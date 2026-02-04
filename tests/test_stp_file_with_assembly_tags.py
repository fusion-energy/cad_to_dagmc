"""Tests for loading STEP files with assembly_names and assembly_materials."""

import tempfile
from pathlib import Path

import cadquery as cq
import pytest
from packaging.version import Version

from cad_to_dagmc import CadToDagmc
from test_python_api import get_volumes_and_materials_from_h5m

# cq.Material requires CadQuery > 2.6.1
CADQUERY_VERSION = Version(cq.__version__)
CQ_MATERIAL_AVAILABLE = CADQUERY_VERSION > Version("2.6.1")


def test_stp_file_with_assembly_names():
    """Test that STEP files can use assembly_names to get material tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stp_file = Path(tmpdir) / "test_assembly.stp"
        h5m_file = Path(tmpdir) / "dagmc.h5m"

        # Create an assembly with named parts and save to STEP
        sphere = cq.Workplane().sphere(5)
        box = cq.Workplane().moveTo(15, 0).box(5, 5, 5)

        assembly = cq.Assembly()
        assembly.add(sphere, name="tungsten")
        assembly.add(box, name="steel")
        assembly.save(str(stp_file), exportType="STEP")

        # Load the STEP file using assembly_names
        model = CadToDagmc()
        model.add_stp_file(
            filename=str(stp_file),
            material_tags="assembly_names",
        )
        model.export_dagmc_h5m_file(filename=str(h5m_file))

        assert h5m_file.is_file()

        # Verify the material tags were extracted from assembly names
        vol_mats = get_volumes_and_materials_from_h5m(str(h5m_file))
        assert len(vol_mats) == 2
        # Check that the material tags contain the assembly names
        mat_values = set(vol_mats.values())
        assert "mat:tungsten" in mat_values
        assert "mat:steel" in mat_values


@pytest.mark.skipif(
    not CQ_MATERIAL_AVAILABLE,
    reason="cq.Material requires CadQuery > 2.6.1",
)
def test_stp_file_with_assembly_materials():
    """Test that STEP files can use assembly_materials to get material tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stp_file = Path(tmpdir) / "test_assembly.stp"
        h5m_file = Path(tmpdir) / "dagmc.h5m"

        # Create an assembly with materials and save to STEP
        sphere = cq.Workplane().sphere(5)
        box = cq.Workplane().moveTo(15, 0).box(5, 5, 5)

        assembly = cq.Assembly()
        assembly.add(sphere, name="sphere_part", material=cq.Material("gold"))
        assembly.add(box, name="box_part", material=cq.Material("silver"))
        assembly.save(str(stp_file), exportType="STEP")

        # Load the STEP file using assembly_materials
        model = CadToDagmc()
        model.add_stp_file(
            filename=str(stp_file),
            material_tags="assembly_materials",
        )
        model.export_dagmc_h5m_file(filename=str(h5m_file))

        assert h5m_file.is_file()

        # Verify the material tags were extracted from assembly materials
        vol_mats = get_volumes_and_materials_from_h5m(str(h5m_file))
        assert len(vol_mats) == 2
        mat_values = set(vol_mats.values())
        assert "mat:gold" in mat_values
        assert "mat:silver" in mat_values


def test_stp_file_with_assembly_names_and_scale_factor():
    """Test that STEP files with assembly_names work with scale_factor."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stp_file = Path(tmpdir) / "test_assembly.stp"
        h5m_file = Path(tmpdir) / "dagmc.h5m"

        # Create an assembly with named parts and save to STEP
        sphere = cq.Workplane().sphere(5)
        box = cq.Workplane().moveTo(15, 0).box(5, 5, 5)

        assembly = cq.Assembly()
        assembly.add(sphere, name="tungsten")
        assembly.add(box, name="steel")
        assembly.save(str(stp_file), exportType="STEP")

        # Load the STEP file using assembly_names with scale factor
        model = CadToDagmc()
        model.add_stp_file(
            filename=str(stp_file),
            material_tags="assembly_names",
            scale_factor=0.1,  # Scale down
        )
        model.export_dagmc_h5m_file(filename=str(h5m_file))

        assert h5m_file.is_file()

        # Verify the material tags were extracted
        vol_mats = get_volumes_and_materials_from_h5m(str(h5m_file))
        assert len(vol_mats) == 2
        mat_values = set(vol_mats.values())
        assert "mat:tungsten" in mat_values
        assert "mat:steel" in mat_values


def test_stp_file_with_manual_tags_still_works():
    """Test that STEP files with manual material_tags still work."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stp_file = Path(tmpdir) / "test_assembly.stp"
        h5m_file = Path(tmpdir) / "dagmc.h5m"

        # Create an assembly and save to STEP
        sphere = cq.Workplane().sphere(5)
        box = cq.Workplane().moveTo(15, 0).box(5, 5, 5)

        assembly = cq.Assembly()
        assembly.add(sphere, name="part1")
        assembly.add(box, name="part2")
        assembly.save(str(stp_file), exportType="STEP")

        # Load the STEP file using manual tags (original behavior)
        model = CadToDagmc()
        model.add_stp_file(
            filename=str(stp_file),
            material_tags=["custom_mat1", "custom_mat2"],
        )
        model.export_dagmc_h5m_file(filename=str(h5m_file))

        assert h5m_file.is_file()

        # Verify the manual material tags were used
        vol_mats = get_volumes_and_materials_from_h5m(str(h5m_file))
        assert len(vol_mats) == 2
        mat_values = set(vol_mats.values())
        assert "mat:custom_mat1" in mat_values
        assert "mat:custom_mat2" in mat_values
