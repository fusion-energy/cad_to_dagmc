import warnings
from collections import UserDict
from types import MappingProxyType
from unittest.mock import Mock

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

    def test_removed_cadquery_backend_raises_error(self, tmp_path):
        """The cadquery direct-mesh plugin backend has been removed, so asking
        for it explains what to use instead rather than reporting an unknown
        backend."""
        with pytest.raises(ValueError, match='"cadquery" has been removed') as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "test_cadquery.h5m"),
                meshing_backend="cadquery",
                tolerance=0.05,
            )

        assert "cad-to-dagmc-mesher" in str(excinfo.value)

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

    def test_mesher_backend_auto_selected_from_tet_volumes(self, tmp_path):
        """tet_volumes selects the cad-to-dagmc-mesher backend when no
        meshing_backend is given. The mesher branch then fails fast because
        target_edge_length is missing, which proves the backend was selected."""
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
        "mesher_kwargs",
        [
            {"tolerance": 0.05},
            {"angular_tolerance": 0.2},
            {"tolerance": 0.05, "angular_tolerance": 0.2},
        ],
    )
    def test_tolerance_kwargs_select_mesher(self, tmp_path, capsys, mesher_kwargs):
        """tolerance and angular_tolerance are only accepted by the
        cad-to-dagmc-mesher backend, so they select it without any warning."""
        output_file = tmp_path / "mesher_kwargs.h5m"

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = self.my_model.export_dagmc_h5m_file(
                filename=str(output_file), **mesher_kwargs
            )

        assert result == str(output_file)
        assert output_file.exists()
        assert "Using meshing backend: cad-to-dagmc-mesher" in capsys.readouterr().out

    def test_tolerance_with_gmsh_args_is_ambiguous(self, tmp_path):
        """tolerance selects the mesher and min_mesh_size selects gmsh, so
        together they raise rather than guessing."""
        with pytest.raises(ValueError, match="Ambiguous backend"):
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "mesher_gmsh_ambiguous.h5m"),
                tolerance=0.05,
                min_mesh_size=0.5,
            )

    def test_tolerance_with_umesh_filename_needs_the_tet_arguments(self, tmp_path):
        """umesh_filename is accepted by gmsh and cad-to-dagmc-mesher, so with
        tolerance it is not ambiguous: the mesher is selected, and it says it
        needs tet_volumes and target_edge_length to write the volume mesh."""
        with pytest.raises(ValueError, match="requires BOTH tet_volumes"):
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "umesh_mesher.h5m"),
                tolerance=0.05,
                umesh_filename=str(tmp_path / "umesh_mesher.vtk"),
            )

    def test_ambiguity_message_names_the_provided_arguments(self, tmp_path):
        """The ambiguity error says which argument came from which backend."""
        with pytest.raises(ValueError) as excinfo:
            self.my_model.export_dagmc_h5m_file(
                filename=str(tmp_path / "gmsh_ambiguous.h5m"),
                tolerance=0.05,
                min_mesh_size=0.5,
            )

        message = str(excinfo.value)
        assert "Provided GMSH arguments: ['min_mesh_size']" in message
        assert "Provided cad-to-dagmc-mesher arguments: ['tolerance']" in message

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

    @pytest.mark.parametrize(
        "imprint",
        [
            False,
            {"threads": "all", "glue": "partial"},
            MappingProxyType({"threads": 1, "glue": None}),
            UserDict({"threads": 1, "glue": "full"}),
        ],
    )
    @pytest.mark.parametrize(
        "backend_kwargs, expected_backend",
        [
            ({}, "cad-to-dagmc-mesher"),
            ({"max_mesh_size": 1.0}, "gmsh"),
            ({"tolerance": 0.05}, "cad-to-dagmc-mesher"),
        ],
    )
    def test_shared_imprint_options_do_not_select_a_backend(
        self, tmp_path, monkeypatch, capsys, imprint, backend_kwargs, expected_backend
    ):
        """Neither mapping entries nor False are backend-selecting arguments."""
        monkeypatch.setattr(
            "cad_to_dagmc.core._cad_to_dagmc_mesher_is_available", lambda: True
        )
        stop_after_selection = Mock(side_effect=RuntimeError("arguments handled"))
        monkeypatch.setattr(
            "cad_to_dagmc.core.get_ids_from_assembly", stop_after_selection
        )
        original = dict(imprint) if imprint is not False else False
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with pytest.raises(RuntimeError, match="arguments handled"):
                self.my_model.export_dagmc_h5m_file(
                    filename=str(tmp_path / "shared_imprint.h5m"),
                    imprint=imprint,
                    **backend_kwargs,
                )
        stop_after_selection.assert_called_once()
        assert f"Using meshing backend: {expected_backend}" in capsys.readouterr().out
        assert imprint == original
        assert not list(tmp_path.iterdir())

    def test_mesher_kwargs_without_mesher_installed_raises_helpful_error(
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
        assert "meshing_backend='gmsh'" in message
        assert "tolerance" in message

    def test_explicit_gmsh_works_without_mesher_installed(
        self, tmp_path, monkeypatch
    ):
        """The remedy the error suggests actually works."""
        monkeypatch.setattr(
            "cad_to_dagmc.core._cad_to_dagmc_mesher_is_available", lambda: False
        )
        output_file = tmp_path / "explicit_gmsh_no_mesher.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file), meshing_backend="gmsh", max_mesh_size=1.0
        )

        assert result == str(output_file)
        assert output_file.exists()

    def test_no_backend_args_without_mesher_installed_falls_back_to_gmsh(
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

        with pytest.warns(UserWarning, match="Falling back to the gmsh backend"):
            result = self.my_model.export_dagmc_h5m_file(filename=str(output_file))

        assert result == str(output_file)
        assert output_file.exists()
        assert "Using meshing backend: gmsh" in capsys.readouterr().out

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
            warning for warning in w if "meshing backend" in str(warning.message)
        ]

    def test_invalid_meshing_backend_raises_error(self, tmp_path):
        """Test that invalid meshing backend raises ValueError"""
        output_file = tmp_path / "test_invalid_backend.h5m"

        with pytest.raises(ValueError, match='meshing_backend "invalid" not supported'):
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file), meshing_backend="invalid"
            )

    def test_gmsh_backend_warns_about_mesher_parameters(self, tmp_path):
        """Test that GMSH backend warns about unused cad-to-dagmc-mesher parameters"""
        output_file = tmp_path / "test_warnings_gmsh.h5m"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                meshing_backend="gmsh",
                tolerance=0.05,  # cad-to-dagmc-mesher parameter, should be ignored
                min_mesh_size=0.1,
            )

            # Check that warning was issued
            assert len(w) == 1
            assert "following parameters are ignored when using GMSH backend" in str(
                w[0].message
            )
            assert "tolerance" in str(w[0].message)

    def test_gmsh_backend_uses_default_values(self, tmp_path):
        """Test that GMSH backend uses default values when not specified"""
        output_file = tmp_path / "test_gmsh_defaults.h5m"

        # This should work without specifying mesh size parameters
        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file), meshing_backend="gmsh"
        )

        assert result == str(output_file)
        assert output_file.exists()

    @pytest.mark.requires_mesher
    def test_mesher_backend_with_all_valid_parameters(self, tmp_path):
        """Test cad-to-dagmc-mesher backend with all valid parameters"""
        output_file = tmp_path / "test_mesher_all_params.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cad-to-dagmc-mesher",
            tolerance=0.01,
            angular_tolerance=0.15,
            scale_factor=2.0,
            imprint={"threads": 1, "glue": None},
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
            imprint={"threads": "all", "glue": "partial"},
            implicit_complement_material_tag="air",
        )

        assert result == str(output_file)
        assert output_file.exists()

    @pytest.mark.requires_mesher
    def test_multiple_backend_switches(self, tmp_path):
        """Test that the same model can be exported with different backends"""
        output_file_cq = tmp_path / "test_switch_mesher.h5m"
        output_file_gmsh = tmp_path / "test_switch_gmsh.h5m"

        # Export with cad-to-dagmc-mesher backend
        result_cq = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file_cq),
            meshing_backend="cad-to-dagmc-mesher",
            tolerance=0.1,
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

    @pytest.mark.requires_mesher
    def test_all_valid_mesher_kwargs_accepted(self, tmp_path):
        """Test that all valid cad-to-dagmc-mesher surface kwargs are accepted"""
        output_file = tmp_path / "test_valid_mesher_kwargs.h5m"

        # Should not raise any error
        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cad-to-dagmc-mesher",
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
                MESHING_BACKEND="gmsh",  # wrong case
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

    @pytest.mark.requires_mesher
    def test_mesher_backend_with_multiple_volumes(self, tmp_path):
        """Test cad-to-dagmc-mesher backend works with multiple volumes"""
        output_file = tmp_path / "test_multi_volume_mesher.h5m"

        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cad-to-dagmc-mesher",
            tolerance=0.08,
            angular_tolerance=0.12,
        )

        assert result == str(output_file)
        assert output_file.exists()
