import warnings

import pytest
import cadquery as cq

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import resolve_set_size, set_sizes_for_mesh, init_gmsh, get_volumes


# Unit tests for resolve_set_size helper function

def test_resolve_set_size_int_only():
    """Test with only integer volume IDs as keys"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "copper"]

    result = resolve_set_size({1: 0.5, 2: 1.0}, volumes, material_tags)
    assert result == {1: 0.5, 2: 1.0}


def test_resolve_set_size_str_only_single_match():
    """Test with a material tag that matches a single volume"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "copper"]

    result = resolve_set_size({"water": 0.5}, volumes, material_tags)
    assert result == {2: 0.5}


def test_resolve_set_size_str_only_multiple_matches():
    """Test with a material tag that matches multiple volumes"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "steel"]

    result = resolve_set_size({"steel": 0.5}, volumes, material_tags)
    assert result == {1: 0.5, 3: 0.5}


def test_resolve_set_size_mixed_int_and_str():
    """Test with mixed int and str keys"""
    volumes = [(3, 1), (3, 2), (3, 3), (3, 4)]
    material_tags = ["steel", "water", "steel", "copper"]

    result = resolve_set_size({2: 0.5, "copper": 1.0}, volumes, material_tags)
    assert result == {2: 0.5, 4: 1.0}


def test_resolve_set_size_empty_input():
    """Test with empty input"""
    volumes = [(3, 1), (3, 2)]
    material_tags = ["steel", "water"]

    result = resolve_set_size({}, volumes, material_tags)
    assert result == {}


def test_resolve_set_size_invalid_material_tag_raises_error():
    """Test that an invalid material tag raises ValueError"""
    volumes = [(3, 1), (3, 2)]
    material_tags = ["steel", "water"]

    with pytest.raises(ValueError, match="Material tag 'copper' not found"):
        resolve_set_size({"copper": 0.5}, volumes, material_tags)


def test_resolve_set_size_invalid_type_raises_error():
    """Test that an invalid key type raises TypeError"""
    volumes = [(3, 1), (3, 2)]
    material_tags = ["steel", "water"]

    with pytest.raises(TypeError, match="set_size keys must be int .* or str"):
        resolve_set_size({1.5: 0.5}, volumes, material_tags)


def test_resolve_set_size_duplicate_volume_same_size_ok():
    """Test that specifying same volume multiple times with same size is OK"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "steel"]

    # Volume 1 is specified both by ID and by material tag "steel"
    # Both have size 0.5, so this should work
    result = resolve_set_size({1: 0.5, "steel": 0.5}, volumes, material_tags)
    assert result == {1: 0.5, 3: 0.5}


def test_resolve_set_size_duplicate_volume_different_size_raises_error():
    """Test that specifying same volume with different sizes raises error"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "steel"]

    # Volume 1 is specified by ID with size 0.5, but also by "steel" with size 1.0
    with pytest.raises(ValueError, match="Volume ID 1 specified multiple times"):
        resolve_set_size({1: 0.5, "steel": 1.0}, volumes, material_tags)


def test_resolve_set_size_error_message_shows_available_tags():
    """Test that error message shows available material tags"""
    volumes = [(3, 1), (3, 2), (3, 3)]
    material_tags = ["steel", "water", "copper"]

    with pytest.raises(ValueError) as exc_info:
        resolve_set_size({"invalid": 0.5}, volumes, material_tags)

    error_msg = str(exc_info.value)
    assert "copper" in error_msg
    assert "steel" in error_msg
    assert "water" in error_msg


# Integration tests for set_size with material tag strings

def test_set_size_with_material_tag_string(tmp_path):
    """Test export_dagmc_h5m_file with material tag string in set_size"""
    sphere1 = cq.Workplane("XY").sphere(5)
    sphere2 = cq.Workplane("XY").center(15, 0).sphere(5)

    assembly = cq.Assembly()
    assembly.add(sphere1, name="sphere1")
    assembly.add(sphere2, name="sphere2")

    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags=["steel", "copper"])

    h5m_file = tmp_path / "dagmc.h5m"

    # Use material tag string in set_size
    filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        min_mesh_size=0.5,
        max_mesh_size=2.0,
        set_size={"steel": 0.8, "copper": 1.5},
        meshing_backend="gmsh",
    )

    assert h5m_file.is_file()


def test_set_size_with_mixed_int_and_string(tmp_path):
    """Test export_dagmc_h5m_file with mixed int and string in set_size"""
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

    # Use mixed int and string in set_size
    filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        min_mesh_size=0.5,
        max_mesh_size=2.0,
        set_size={1: 0.8, "copper": 1.5},  # Volume 1 and copper (volume 3)
        meshing_backend="gmsh",
    )

    assert h5m_file.is_file()


def test_set_size_with_assembly_names(tmp_path):
    """Test set_size with assembly_names derived material tags"""
    cube1 = cq.Workplane("XY").box(10, 10, 10)
    cube2 = cq.Workplane("XY").center(20, 0).box(10, 10, 10)

    assembly = cq.Assembly()
    assembly.add(cube1, name="coarse_mesh_part")
    assembly.add(cube2, name="fine_mesh_part")

    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags="assembly_names")

    h5m_file = tmp_path / "dagmc.h5m"

    # Use assembly names in set_size
    filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        min_mesh_size=0.1,
        max_mesh_size=2.0,
        set_size={"coarse_mesh_part": 1.5, "fine_mesh_part": 0.3},
        meshing_backend="gmsh",
    )

    assert h5m_file.is_file()


def test_set_size_invalid_material_tag_raises_error(tmp_path):
    """Test that invalid material tag string in set_size raises ValueError"""
    sphere = cq.Workplane("XY").sphere(5)

    model = CadToDagmc()
    model.add_cadquery_object(sphere, material_tags=["steel"])

    h5m_file = tmp_path / "dagmc.h5m"

    with pytest.raises(ValueError, match="Material tag 'nonexistent' not found"):
        model.export_dagmc_h5m_file(
            filename=str(h5m_file),
            min_mesh_size=0.5,
            max_mesh_size=2.0,
            set_size={"nonexistent": 0.5},
            meshing_backend="gmsh",
        )


def test_set_size_material_tag_multiple_volumes(tmp_path):
    """Test that a material tag matching multiple volumes sets size for all"""
    sphere1 = cq.Workplane("XY").sphere(5)
    sphere2 = cq.Workplane("XY").center(15, 0).sphere(5)
    sphere3 = cq.Workplane("XY").center(30, 0).sphere(5)

    assembly = cq.Assembly()
    assembly.add(sphere1, name="sphere1")
    assembly.add(sphere2, name="sphere2")
    assembly.add(sphere3, name="sphere3")

    model = CadToDagmc()
    # Two volumes have "steel" tag
    model.add_cadquery_object(assembly, material_tags=["steel", "water", "steel"])

    h5m_file = tmp_path / "dagmc.h5m"

    # "steel" should set size for volumes 1 and 3
    filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        min_mesh_size=0.5,
        max_mesh_size=2.0,
        set_size={"steel": 0.8},
        meshing_backend="gmsh",
    )

    assert h5m_file.is_file()


def _make_gmsh_with_two_volumes():
    """Helper to create a gmsh model with two volumes for warning tests."""
    sphere1 = cq.Workplane("XY").sphere(5)
    sphere2 = cq.Workplane("XY").center(15, 0).sphere(5)
    assembly = cq.Assembly()
    assembly.add(sphere1, name="sphere1")
    assembly.add(sphere2, name="sphere2")
    gmsh_obj = init_gmsh()
    gmsh_obj, volumes = get_volumes(gmsh_obj, assembly)
    return gmsh_obj, volumes


def test_set_size_above_max_warns():
    """Test that set_size above max_mesh_size produces a warning"""
    gmsh_obj, volumes = _make_gmsh_with_two_volumes()
    vol_id = volumes[0][1]
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            set_sizes_for_mesh(
                gmsh=gmsh_obj,
                min_mesh_size=1.0,
                max_mesh_size=5.0,
                set_size={vol_id: 10.0},
            )
            assert len(w) == 1
            assert "above max_mesh_size" in str(w[0].message)
            assert "clamped to 5.0" in str(w[0].message)
            assert "Try enlarging max_mesh_size" in str(w[0].message)
    finally:
        gmsh_obj.finalize()


def test_set_size_below_min_warns():
    """Test that set_size below min_mesh_size produces a warning"""
    gmsh_obj, volumes = _make_gmsh_with_two_volumes()
    vol_id = volumes[0][1]
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            set_sizes_for_mesh(
                gmsh=gmsh_obj,
                min_mesh_size=5.0,
                max_mesh_size=10.0,
                set_size={vol_id: 1.0},
            )
            assert len(w) == 1
            assert "below min_mesh_size" in str(w[0].message)
            assert "clamped to 5.0" in str(w[0].message)
            assert "Try reducing min_mesh_size" in str(w[0].message)
    finally:
        gmsh_obj.finalize()


def test_set_size_within_range_no_warning():
    """Test that set_size within min/max range produces no warning"""
    gmsh_obj, volumes = _make_gmsh_with_two_volumes()
    vol_id = volumes[0][1]
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            set_sizes_for_mesh(
                gmsh=gmsh_obj,
                min_mesh_size=1.0,
                max_mesh_size=10.0,
                set_size={vol_id: 5.0},
            )
            assert len(w) == 0
    finally:
        gmsh_obj.finalize()


def test_set_size_warning_uses_original_material_tag_key():
    """Test that warning uses original material tag string when provided"""
    gmsh_obj, volumes = _make_gmsh_with_two_volumes()
    vol_id = volumes[0][1]
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            set_sizes_for_mesh(
                gmsh=gmsh_obj,
                min_mesh_size=1.0,
                max_mesh_size=5.0,
                set_size={vol_id: 10.0},
                original_set_size={"steel": 10.0},
            )
            assert len(w) == 1
            assert "steel" in str(w[0].message)
            assert "above max_mesh_size" in str(w[0].message)
    finally:
        gmsh_obj.finalize()
