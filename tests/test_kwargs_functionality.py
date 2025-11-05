import os
import warnings
from pathlib import Path

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc


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
            angular_tolerance=0.2
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
            mesh_algorithm=6
        )
        
        assert result == str(output_file)
        assert output_file.exists()

    def test_cadquery_backend_with_unstructured_volumes_raises_error(self, tmp_path):
        """Test that CadQuery backend with unstructured_volumes raises ValueError"""
        output_file = tmp_path / "test_invalid.h5m"
        
        with pytest.raises(ValueError, match="CadQuery backend cannot be used for volume meshing"):
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                meshing_backend="cadquery",
                unstructured_volumes=[1]
            )

    def test_invalid_meshing_backend_raises_error(self, tmp_path):
        """Test that invalid meshing backend raises ValueError"""
        output_file = tmp_path / "test_invalid_backend.h5m"
        
        with pytest.raises(ValueError, match='meshing_backend "invalid" not supported'):
            self.my_model.export_dagmc_h5m_file(
                filename=str(output_file),
                meshing_backend="invalid"
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
                tolerance=0.05
            )
            
            # Check that warning was issued
            assert len(w) == 1
            assert "following parameters are ignored when using CadQuery backend" in str(w[0].message)
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
                min_mesh_size=0.1
            )
            
            # Check that warning was issued
            assert len(w) == 1
            assert "following parameters are ignored when using GMSH backend" in str(w[0].message)
            assert "tolerance" in str(w[0].message)

    def test_cadquery_backend_uses_default_tolerances(self, tmp_path):
        """Test that CadQuery backend uses default tolerances when not specified"""
        output_file = tmp_path / "test_defaults.h5m"
        
        # This should work without specifying tolerance parameters
        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="cadquery"
        )
        
        assert result == str(output_file)
        assert output_file.exists()

    def test_gmsh_backend_uses_default_values(self, tmp_path):
        """Test that GMSH backend uses default values when not specified"""
        output_file = tmp_path / "test_gmsh_defaults.h5m"
        
        # This should work without specifying mesh size parameters
        result = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file),
            meshing_backend="gmsh"
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
            implicit_complement_material_tag="vacuum"
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
            implicit_complement_material_tag="air"
        )
        
        assert result == str(output_file)
        assert output_file.exists()

    def test_multiple_backend_switches(self, tmp_path):
        """Test that the same model can be exported with different backends"""
        output_file_cq = tmp_path / "test_switch_cq.h5m"
        output_file_gmsh = tmp_path / "test_switch_gmsh.h5m"
        
        # Export with CadQuery backend
        result_cq = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file_cq),
            meshing_backend="cadquery",
            tolerance=0.1
        )
        
        # Export with GMSH backend
        result_gmsh = self.my_model.export_dagmc_h5m_file(
            filename=str(output_file_gmsh),
            meshing_backend="gmsh",
            max_mesh_size=1.0
        )
        
        assert result_cq == str(output_file_cq)
        assert result_gmsh == str(output_file_gmsh)
        assert output_file_cq.exists()
        assert output_file_gmsh.exists()


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
            set_size={1: 0.5, 2: 0.3}  # Different mesh sizes for different volumes
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
            angular_tolerance=0.12
        )
        
        assert result == str(output_file)
        assert output_file.exists()