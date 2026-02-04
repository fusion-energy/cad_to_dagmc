import pytest
import cadquery as cq

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import resolve_unstructured_volumes


# Unit tests for resolve_unstructured_volumes helper function

def test_resolve_unstructured_volumes_int_only():
    """Test with only integer volume IDs"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "steel"]

    result = resolve_unstructured_volumes([1, 2], volumes, material_tags)
    assert result == [1, 2]


def test_resolve_unstructured_volumes_str_only_single_match():
    """Test with a material tag that matches a single volume"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "copper"]

    result = resolve_unstructured_volumes(["water"], volumes, material_tags)
    assert result == [2]


def test_resolve_unstructured_volumes_str_only_multiple_matches():
    """Test with a material tag that matches multiple volumes"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "steel"]

    result = resolve_unstructured_volumes(["steel"], volumes, material_tags)
    assert result == [1, 3]


def test_resolve_unstructured_volumes_mixed_int_and_str():
    """Test with mixed int and str values"""
    volumes = [(3, 1), (3, 2), (3, 3), (3, 4)]
    material_tags = ["steel", "water", "steel", "copper"]

    result = resolve_unstructured_volumes([2, "copper"], volumes, material_tags)
    assert result == [2, 4]


def test_resolve_unstructured_volumes_mixed_str_and_int():
    """Test with str first, then int"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "copper"]

    result = resolve_unstructured_volumes(["steel", 3], volumes, material_tags)
    assert result == [1, 3]


def test_resolve_unstructured_volumes_duplicate_removal():
    """Test that duplicates are removed while preserving order"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "steel"]

    # Request volume 1 explicitly and also "steel" which includes volume 1
    result = resolve_unstructured_volumes([1, "steel"], volumes, material_tags)
    assert result == [1, 3]  # 1 appears only once


def test_resolve_unstructured_volumes_duplicate_from_multiple_tags():
    """Test duplicate removal when same volume from multiple str lookups"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "steel"]

    result = resolve_unstructured_volumes(["steel", "steel"], volumes, material_tags)
    assert result == [1, 3]  # No duplicates


def test_resolve_unstructured_volumes_empty_input():
    """Test with empty input"""
    volumes = [(3, 1), (3, 2)]
    material_tags = ["steel", "water"]

    result = resolve_unstructured_volumes([], volumes, material_tags)
    assert result == []


def test_resolve_unstructured_volumes_invalid_material_tag_raises_error():
    """Test that an invalid material tag raises ValueError"""
    volumes = [(3, 1), (3, 2)]
    material_tags = ["steel", "water"]

    with pytest.raises(ValueError, match="Material tag 'copper' not found"):
        resolve_unstructured_volumes(["copper"], volumes, material_tags)


def test_resolve_unstructured_volumes_invalid_type_raises_error():
    """Test that an invalid type raises TypeError"""
    volumes = [(3, 1), (3, 2)]
    material_tags = ["steel", "water"]

    with pytest.raises(TypeError, match="must contain int .* or str"):
        resolve_unstructured_volumes([1.5], volumes, material_tags)


def test_resolve_unstructured_volumes_error_message_shows_available_tags():
    """Test that error message shows available material tags"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "copper"]

    with pytest.raises(ValueError) as exc_info:
        resolve_unstructured_volumes(["invalid"], volumes, material_tags)

    # Check that available tags are listed
    error_msg = str(exc_info.value)
    assert "copper" in error_msg
    assert "steel" in error_msg
    assert "water" in error_msg


# Integration tests for unstructured_volumes with material tag strings

def test_unstructured_volumes_with_material_tag_string(tmp_path):
    """Test export_dagmc_h5m_file with material tag string in unstructured_volumes"""
    sphere1 = cq.Workplane("XY").sphere(5)
    sphere2 = cq.Workplane("XY").center(15, 0).sphere(5)
    sphere3 = cq.Workplane("XY").center(30, 0).sphere(5)

    assembly = cq.Assembly()
    assembly.add(sphere1, name="sphere1")
    assembly.add(sphere2, name="sphere2")
    assembly.add(sphere3, name="sphere3")

    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags=["steel", "water", "steel"])

    h5m_file = tmp_path / "dagmc.h5m"
    vtk_file = tmp_path / "umesh.vtk"

    # Use material tag string to select volumes
    dag_filename, umesh_filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        min_mesh_size=0.5,
        max_mesh_size=2.0,
        unstructured_volumes=["steel"],  # Should resolve to volumes 1 and 3
        umesh_filename=str(vtk_file),
        meshing_backend="gmsh",
    )

    assert h5m_file.is_file()
    assert vtk_file.is_file()


def test_unstructured_volumes_with_mixed_int_and_string(tmp_path):
    """Test export_dagmc_h5m_file with mixed int and string in unstructured_volumes"""
    sphere1 = cq.Workplane("XY").sphere(5)
    sphere2 = cq.Workplane("XY").center(15, 0).sphere(5)
    sphere3 = cq.Workplane("XY").center(30, 0).sphere(5)

    assembly = cq.Assembly()
    assembly.add(sphere1, name="sphere1")
    assembly.add(sphere2, name="sphere2")
    assembly.add(sphere3, name="sphere3")

    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags=["steel", "water", "copper"])

    h5m_file = tmp_path / "dagmc.h5m"
    vtk_file = tmp_path / "umesh.vtk"

    # Use mixed int and string
    dag_filename, umesh_filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        min_mesh_size=0.5,
        max_mesh_size=2.0,
        unstructured_volumes=[1, "copper"],  # Volume 1 and volume 3 (copper)
        umesh_filename=str(vtk_file),
        meshing_backend="gmsh",
    )

    assert h5m_file.is_file()
    assert vtk_file.is_file()


def test_unstructured_volumes_invalid_material_tag_raises_error(tmp_path):
    """Test that invalid material tag string raises ValueError"""
    sphere = cq.Workplane("XY").sphere(5)

    model = CadToDagmc()
    model.add_cadquery_object(sphere, material_tags=["steel"])

    h5m_file = tmp_path / "dagmc.h5m"
    vtk_file = tmp_path / "umesh.vtk"

    with pytest.raises(ValueError, match="Material tag 'nonexistent' not found"):
        model.export_dagmc_h5m_file(
            filename=str(h5m_file),
            min_mesh_size=0.5,
            max_mesh_size=2.0,
            unstructured_volumes=["nonexistent"],
            umesh_filename=str(vtk_file),
            meshing_backend="gmsh",
        )


def test_unstructured_volumes_with_assembly_names(tmp_path):
    """Test using assembly names as material tags and selecting by name in unstructured_volumes.

    Creates two cubes, adds them to an assembly with names, uses assembly_names
    to derive material tags, then uses one of the names to specify unstructured_volumes.
    """
    cube1 = cq.Workplane("XY").box(10, 10, 10)
    cube2 = cq.Workplane("XY").center(20, 0).box(10, 10, 10)

    assembly = cq.Assembly()
    assembly.add(cube1, name="steel_block")
    assembly.add(cube2, name="copper_block")

    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags="assembly_names")

    h5m_file = tmp_path / "dagmc.h5m"
    vtk_file = tmp_path / "umesh.vtk"

    dag_filename, umesh_filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        min_mesh_size=0.5,
        max_mesh_size=2.0,
        unstructured_volumes=["steel_block"],  # Use the assembly name
        umesh_filename=str(vtk_file),
        meshing_backend="gmsh",
    )

    assert h5m_file.is_file()
    assert vtk_file.is_file()
