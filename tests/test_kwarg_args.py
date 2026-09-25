import warnings

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc, CadToDagmcMesherNotFoundError


class TestKwargsExportDagmcH5mFile:
    """Test the **kwargs functionality for export_dagmc_h5m_file method"""

    def setup_method(self):
        """Setup method to create a simple geometry for testing"""
        self.my_model = CadToDagmc()

        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)
        self.my_model.add_cadquery_object(box, material_tags=["steel"])

    def test_cadquery_backend_with_tolerance_params(self, tmp_path):
        """Test CadQuery backend with tolerance parameters"""
        output_file = tmp_path / "test_cadquery.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cadquery",
            tolerance=0.05,
            angular_tolerance=0.2,
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_gmsh_backend_with_mesh_size_params(self, tmp_path):
        """Test GMSH backend with mesh size parameters"""
        output_file = tmp_path / "test_gmsh.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="gmsh",
            min_mesh_size=0.1,
            max_mesh_size=1.0,
            mesh_algorithm=6,
        )

        assert result == str(output_file)
        assert output_file.exists()

    @pytest.mark.requires_mesher
    def test_cad_to_dagmc_mesher_backend_with_tolerance_params(self, tmp_path):
        """Test cad-to-dagmc-mesher backend with tolerance parameters"""
        output_file = tmp_path / "test_mesher.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cad-to-dagmc-mesher",
            tolerance=0.05,
            angular_tolerance=0.2,
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_cadquery_backend_with_unstructured_volumes_raises_error(self, tmp_path):
        """Test that CadQuery backend with unstructured_volumes raises ValueError"""
        output_file = tmp_path / "test_invalid.h5m"

        with pytest.raises(
            ValueError, match="CadQuery backend cannot be used for volume meshing"
        ):
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                meshing_backend="cadquery",
                unstructured_volumes=[1],
            )

    def test_cadquery_backend_with_tet_volumes_raises_error(self, tmp_path):
        """The CadQuery backend cannot volume mesh, so an explicit cadquery
        backend combined with tet_volumes must fail fast."""
        with pytest.raises(
            ValueError, match="CadQuery backend cannot be used for volume meshing"
        ):
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "test_invalid_tet.h5m"),
                meshing_backend="cadquery",
                tet_volumes=["steel"],
            )

    def test_mesher_backend_auto_selected_from_tet_volumes(self, tmp_path):
        """tet_volumes selects the cad-to-dagmc-mesher backend when no
        meshing_backend is given. The mesher branch then fails fast because
        target_edge_length is missing, which proves the backend was selected
        (the cadquery default would have silently ignored tet_volumes)."""
        with pytest.raises(ValueError, match="requires BOTH tet_volumes"):
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "auto_mesher.h5m"),
                tet_volumes=["steel"],
            )

    def test_mesher_backend_auto_selected_from_target_edge_length(self, tmp_path):
        """target_edge_length selects the cad-to-dagmc-mesher backend when no
        meshing_backend is given."""
        with pytest.raises(ValueError, match="requires BOTH tet_volumes"):
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "auto_mesher.h5m"),
                target_edge_length=1.0,
            )

    def test_mesher_and_gmsh_args_are_ambiguous(self, tmp_path):
        """Mixing mesher-specific and gmsh-specific arguments without an
        explicit meshing_backend raises rather than guessing."""
        with pytest.raises(ValueError, match="Ambiguous backend"):
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "ambiguous.h5m"),
                tet_volumes=["steel"],
                target_edge_length=1.0,
                min_mesh_size=0.5,
            )

    @pytest.mark.requires_mesher
    @pytest.mark.parametrize(
        "shared_kwargs",
        [
            {"tolerance": 0.05},
            {"angular_tolerance": 0.2},
            {"tolerance": 0.05, "angular_tolerance": 0.2},
        ],
    )
    def test_shared_kwargs_select_mesher_and_warn(self, tmp_path, shared_kwargs):
        """tolerance and angular_tolerance are accepted by both the cadquery
        and the cad-to-dagmc-mesher backends, so the mesher is preferred and
        the choice is reported."""
        output_file = tmp_path / "shared_kwargs.h5m"

        with pytest.warns(UserWarning, match="cad-to-dagmc-mesher backend has been"):
            result = self.my_model.export_dagmc_h5m_file(
                filename=str(output_file), **shared_kwargs
            )

        assert result == str(output_file)
        assert output_file.exists()

    @pytest.mark.requires_mesher
    def test_shared_kwargs_warning_names_the_provided_arguments(self, tmp_path):
        """The warning lists the shared arguments that triggered the choice."""
        with pytest.warns(UserWarning) as record:
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "named_args.h5m"), tolerance=0.05
            )

        message = str(record[0].message)
        assert "tolerance" in message
        assert "angular_tolerance" not in message

    def test_explicit_backend_overrides_shared_kwarg_preference(self, tmp_path):
        """An explicit meshing_backend wins over the shared kwarg preference,
        and no ambiguity warning is emitted."""
        output_file = tmp_path / "explicit_cadquery.h5m"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            result = self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                meshing_backend="cadquery",
                tolerance=0.05,
            )

        assert result == str(output_file)
        assert output_file.exists()
        assert not [
            warning
            for warning in w
            if "cad-to-dagmc-mesher backend has been" in str(warning.message)
        ]

    def test_shared_kwargs_with_gmsh_args_still_ambiguous(self, tmp_path):
        """Preferring the mesher for shared kwargs must not swallow the
        existing CadQuery and GMSH ambiguity error."""
        with pytest.raises(ValueError, match="Ambiguous backend"):
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "cq_gmsh_ambiguous.h5m"),
                tolerance=0.05,
                min_mesh_size=0.5,
            )

    def test_ambiguity_message_does_not_call_umesh_filename_gmsh_specific(
        self, tmp_path
    ):
        """umesh_filename is accepted by gmsh and cad-to-dagmc-mesher, so the
        ambiguity error must not describe it as gmsh specific, and it should
        say why the mesher cannot simply be used instead."""
        with pytest.raises(ValueError) as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "umesh_ambiguous.h5m"),
                tolerance=0.05,
                umesh_filename=str(tmp_path / "umesh_ambiguous.vtk"),
            )

        message = str(excinfo.value)
        assert "Accepted by gmsh and cad-to-dagmc-mesher: ['umesh_filename']" in message
        assert "Accepted by gmsh only" not in message
        assert "tet_volumes and target_edge_length" in message
        assert "meshing_backend" in message

    def test_ambiguity_message_separates_gmsh_only_arguments(self, tmp_path):
        """Genuinely gmsh specific arguments are reported as such."""
        with pytest.raises(ValueError) as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "gmsh_ambiguous.h5m"),
                tolerance=0.05,
                min_mesh_size=0.5,
            )

        message = str(excinfo.value)
        assert "Accepted by gmsh only: ['min_mesh_size']" in message
        assert "Accepted by cadquery and cad-to-dagmc-mesher: ['tolerance']" in message

    def test_umesh_filename_alone_still_selects_gmsh(self, tmp_path):
        """umesh_filename on its own remains a gmsh request."""
        output_file = tmp_path / "umesh_only.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            umesh_filename=str(tmp_path / "umesh_only.vtk"),
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_gmsh_only_args_still_select_gmsh(self, tmp_path):
        """gmsh-specific arguments alone still select the gmsh backend."""
        output_file = tmp_path / "auto_gmsh.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file), max_mesh_size=1.0
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_shared_kwargs_without_mesher_installed_raises_helpful_error(
        self, tmp_path, monkeypatch
    ):
        """cad-to-dagmc-mesher is not on conda-forge, so when it would be auto
        selected but is missing the user is told how to proceed."""
        monkeypatch.setattr(
            "cad_to_dagmc.core._cad_to_dagmc_mesher_is_available", lambda: False
        )

        with pytest.raises(CadToDagmcMesherNotFoundError) as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "no_mesher.h5m"), tolerance=0.05
            )

        message = str(excinfo.value)
        assert "pip install cad-to-dagmc-mesher" in message
        assert "meshing_backend='cadquery'" in message
        assert "tolerance" in message

    def test_explicit_cadquery_works_without_mesher_installed(
        self, tmp_path, monkeypatch
    ):
        """The remedy the error suggests actually works."""
        monkeypatch.setattr(
            "cad_to_dagmc.core._cad_to_dagmc_mesher_is_available", lambda: False
        )
        output_file = tmp_path / "explicit_cq_no_mesher.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file), meshing_backend="cadquery", tolerance=0.05
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_no_backend_args_without_mesher_installed_falls_back_to_cadquery(
        self, tmp_path, monkeypatch, capsys
    ):
        """A plain export must not be affected by the mesher being absent.

        cad-to-dagmc-mesher is not on conda-forge, so a call that names no
        backend has to keep working without it rather than raising.
        """
        monkeypatch.setattr(
            "cad_to_dagmc.core._cad_to_dagmc_mesher_is_available", lambda: False
        )
        output_file = tmp_path / "default_no_mesher.h5m"

        with pytest.warns(UserWarning, match="Falling back to the cadquery backend"):
            result = self.my_model.export_dagmc_h5m_file(filename=str(output_file))

        assert result == str(output_file)
        assert output_file.exists()
        assert "Using meshing backend: cadquery" in capsys.readouterr().out

    def test_no_backend_args_default_to_cad_to_dagmc_mesher(self, tmp_path, capsys):
        """With no backend selecting arguments the mesher is chosen."""
        output_file = tmp_path / "auto_default.h5m"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            result = self.my_model.export_dagmc_h5m_file(filename=str(output_file))

        assert result == str(output_file)
        assert output_file.exists()
        assert "Using meshing backend: cad-to-dagmc-mesher" in capsys.readouterr().out
        # Naming no backend expresses no preference, so there is nothing to
        # disambiguate and nothing to warn about.
        assert not [
            warning
            for warning in w
            if "cad-to-dagmc-mesher backend has been" in str(warning.message)
        ]

    def test_invalid_meshing_backend_raises_error(self, tmp_path):
        """Test that invalid meshing backend raises ValueError"""
        output_file = tmp_path / "test_invalid_backend.h5m"

        with pytest.raises(ValueError, match='meshing_backend "invalid" not supported'):
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file), meshing_backend="invalid"
            )

    def test_cadquery_backend_warns_about_gmsh_parameters(self, tmp_path):
        """Test that CadQuery backend warns about unused GMSH parameters"""
        output_file = tmp_path / "test_warnings.h5m"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                meshing_backend="cadquery",
                min_mesh_size=0.1,  # GMSH parameter, should be ignored
                tolerance=0.05,
            )

            # Check that warning was issued
            assert len(w) == 1
            assert (
                "following parameters are ignored when using CadQuery backend"
                in str(w[0].message)
            )
            assert "min_mesh_size" in str(w[0].message)

    def test_gmsh_backend_warns_about_cadquery_parameters(self, tmp_path):
        """Test that GMSH backend warns about unused CadQuery parameters"""
        output_file = tmp_path / "test_warnings_gmsh.h5m"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                meshing_backend="gmsh",
                tolerance=0.05,  # CadQuery parameter, should be ignored
                min_mesh_size=0.1,
            )

            # Check that warning was issued
            assert len(w) == 1
            assert "following parameters are ignored when using GMSH backend" in str(
                w[0].message
            )
            assert "tolerance" in str(w[0].message)

    def test_cadquery_backend_uses_default_tolerances(self, tmp_path):
        """Test that CadQuery backend uses default tolerances when not specified"""
        output_file = tmp_path / "test_defaults.h5m"

        # This should work without specifying tolerance parameters
        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file), meshing_backend="cadquery"
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_gmsh_backend_uses_default_values(self, tmp_path):
        """Test that GMSH backend uses default values when not specified"""
        output_file = tmp_path / "test_gmsh_defaults.h5m"

        # This should work without specifying mesh size parameters
        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file), meshing_backend="gmsh"
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_cadquery_backend_with_all_valid_parameters(self, tmp_path):
        """Test CadQuery backend with all valid parameters"""
        output_file = tmp_path / "test_cadquery_all_params.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cadquery",
            tolerance=0.01,
            angular_tolerance=0.15,
            scale_factor=2.0,
            imprint=False,
            implicit_complement_material_tag="vacuum",
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_gmsh_backend_with_all_valid_parameters(self, tmp_path):
        """Test GMSH backend with all valid parameters"""
        output_file = tmp_path / "test_gmsh_all_params.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="gmsh",
            min_mesh_size=0.05,
            max_mesh_size=2.0,
            mesh_algorithm=1,
            method="file",
            scale_factor=1.5,
            imprint=True,
            implicit_complement_material_tag="air",
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_multiple_backend_switches(self, tmp_path):
        """Test that the same model can be exported with different backends"""
        output_file_cq = tmp_path / "test_switch_cq.h5m"
        output_file_gmsh = tmp_path / "test_switch_gmsh.h5m"

        # Export with CadQuery backend
        result_cq = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file_cq), meshing_backend="cadquery", tolerance=0.1
        )

        # Export with GMSH backend
        result_gmsh = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file_gmsh), meshing_backend="gmsh", max_mesh_size=1.0
        )

        assert result_cq == str(output_file_cq)
        assert result_gmsh == str(output_file_gmsh)
        assert output_file_cq.exists()
        assert output_file_gmsh.exists()


class TestKwargsValidation:
    """Test kwargs validation for export_dagmc_h5m_file method"""

    def setup_method(self):
        """Setup method to create a simple geometry for testing"""
        self.my_model = CadToDagmc()

        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)
        self.my_model.add_cadquery_object(box, material_tags=["steel"])

    def test_invalid_kwargs_raises_error(self, tmp_path):
        """Test that invalid kwargs raise ValueError with helpful message"""
        output_file = tmp_path / "test_invalid_kwargs.h5m"

        with pytest.raises(ValueError) as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                invalid_param=123,
                another_invalid=True,
            )

        error_message = str(excinfo.value)
        assert "Invalid keyword arguments:" in error_message
        assert "another_invalid" in error_message
        assert "invalid_param" in error_message
        assert "Acceptable arguments are:" in error_message

    def test_mixed_valid_invalid_kwargs_raises_error(self, tmp_path):
        """Test that mix of valid and invalid kwargs raises error"""
        output_file = tmp_path / "test_mixed_kwargs.h5m"

        with pytest.raises(ValueError) as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                tolerance=0.1,  # valid
                bad_param=456,  # invalid
                min_mesh_size=0.5,  # valid
            )

        error_message = str(excinfo.value)
        assert "Invalid keyword arguments:" in error_message
        assert "bad_param" in error_message
        assert "tolerance" in error_message  # valid param should be in error
        assert "min_mesh_size" in error_message  # valid param should be in error

    def test_all_valid_cadquery_kwargs_accepted(self, tmp_path):
        """Test that all valid CadQuery kwargs are accepted"""
        output_file = tmp_path / "test_valid_cq_kwargs.h5m"

        # Should not raise any error
        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cadquery",
            tolerance=0.1,
            angular_tolerance=0.2,
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_all_valid_gmsh_kwargs_accepted(self, tmp_path):
        """Test that all valid GMSH kwargs are accepted"""
        output_file = tmp_path / "test_valid_gmsh_kwargs.h5m"

        # Should not raise any error
        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="gmsh",
            min_mesh_size=0.1,
            max_mesh_size=1.0,
            mesh_algorithm=1,
            set_size={1: 0.5},
            umesh_filename="test.vtk",
            method="file",
            # unstructured_volumes would be tested separately
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_typo_in_kwarg_name_raises_helpful_error(self, tmp_path):
        """Test that typos in parameter names give helpful error messages"""
        output_file = tmp_path / "test_typo.h5m"

        # Common typo: "tolerance" -> "tollerance"
        with pytest.raises(ValueError) as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                tollerance=0.1,  # typo
            )

        error_message = str(excinfo.value)
        assert "Invalid keyword arguments:" in error_message
        assert "tollerance" in error_message
        assert "tolerance" in error_message  # should show the correct options

    def test_case_sensitivity_in_kwargs(self, tmp_path):
        """Test that kwargs are case sensitive"""
        output_file = tmp_path / "test_case_sensitive.h5m"

        # Wrong case should raise error
        with pytest.raises(ValueError) as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                Tolerance=0.1,  # wrong case
                MESHING_BACKEND="cadquery",  # wrong case
            )

        error_message = str(excinfo.value)
        assert "Invalid keyword arguments:" in error_message
        assert "Tolerance" in error_message
        assert "MESHING_BACKEND" in error_message


class TestKwargsWithMultipleVolumes:
    """Test kwargs functionality with multiple volumes"""

    def setup_method(self):
        """Setup method to create geometry with multiple volumes"""
        self.my_model = CadToDagmc()

        # Create two separate boxes
        box1 = cq.Workplane("XY").box(5, 5, 5).translate((0, 0, 0))
        box2 = cq.Workplane("XY").box(3, 3, 3).translate((10, 0, 0))

        self.my_model.add_cadquery_object(box1, material_tags=["steel"])
        self.my_model.add_cadquery_object(box2, material_tags=["aluminum"])

    def test_gmsh_backend_with_set_size_parameter(self, tmp_path):
        """Test GMSH backend with set_size parameter for different volumes"""
        output_file = tmp_path / "test_set_size.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="gmsh",
            set_size={1: 0.5, 2: 0.3},  # Different mesh sizes for different volumes
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_cadquery_backend_with_multiple_volumes(self, tmp_path):
        """Test CadQuery backend works with multiple volumes"""
        output_file = tmp_path / "test_multi_volume_cq.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cadquery",
            tolerance=0.08,
            angular_tolerance=0.12,
        )

        assert result == str(output_file)
        assert output_file.exists()
