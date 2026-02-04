from pathlib import Path

import cadquery as cq

from cad_to_dagmc import CadToDagmc


def test_get_material_tags_empty():
    """Test get_material_tags returns empty list for new model"""
    model = CadToDagmc()
    assert model.get_material_tags() == []


def test_get_material_tags_single_volume():
    """Test get_material_tags with single volume"""
    model = CadToDagmc()
    box = cq.Workplane("XY").box(10, 10, 10)
    model.add_cadquery_object(box, material_tags=["steel"])

    assert model.get_material_tags() == ["steel"]


def test_get_material_tags_multiple_volumes():
    """Test get_material_tags with multiple volumes"""
    model = CadToDagmc()

    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").box(10, 10, 10), name="box1")
    assembly.add(cq.Workplane("XY").center(20, 0).box(10, 10, 10), name="box2")
    assembly.add(cq.Workplane("XY").center(40, 0).sphere(5), name="sphere")

    model.add_cadquery_object(assembly, material_tags=["steel", "water", "copper"])

    assert model.get_material_tags() == ["steel", "water", "copper"]


def test_get_material_tags_with_assembly_names():
    """Test get_material_tags when using assembly_names.

    This is particularly useful when loading geometry where the user
    wants to discover what names are available in the assembly.
    """
    model = CadToDagmc()

    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").box(10, 10, 10), name="steel_block")
    assembly.add(cq.Workplane("XY").center(20, 0).box(10, 10, 10), name="copper_block")

    model.add_cadquery_object(assembly, material_tags="assembly_names")

    # User can now discover what tags were extracted from the assembly
    tags = model.get_material_tags()
    assert tags == ["steel_block", "copper_block"]


def test_get_material_tags_from_stp_file():
    """Test get_material_tags with a STEP file."""
    model = CadToDagmc()

    stp_file = Path(__file__).parent / "two_disconnected_cubes.stp"
    model.add_stp_file(stp_file, material_tags=["mat1", "mat2"])

    assert model.get_material_tags() == ["mat1", "mat2"]


def test_get_material_tags_multiple_add_calls():
    """Test get_material_tags accumulates tags from multiple add calls"""
    model = CadToDagmc()

    box1 = cq.Workplane("XY").box(10, 10, 10)
    model.add_cadquery_object(box1, material_tags=["steel"])

    box2 = cq.Workplane("XY").center(20, 0).box(10, 10, 10)
    model.add_cadquery_object(box2, material_tags=["copper"])

    assert model.get_material_tags() == ["steel", "copper"]


def test_get_material_tags_useful_for_downstream_processing():
    """Test that get_material_tags can be used for downstream processing.

    This demonstrates using get_material_tags to find specific volumes
    for further processing, such as selecting volumes for unstructured meshing.
    """
    model = CadToDagmc()

    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").box(10, 10, 10), name="fuel_rod_1")
    assembly.add(cq.Workplane("XY").center(20, 0).box(10, 10, 10), name="coolant")
    assembly.add(cq.Workplane("XY").center(40, 0).box(10, 10, 10), name="fuel_rod_2")

    model.add_cadquery_object(assembly, material_tags="assembly_names")

    tags = model.get_material_tags()

    # User can check what tags are available
    assert len(tags) == 3
    assert "coolant" in tags
    assert "fuel_rod_1" in tags
    assert "fuel_rod_2" in tags
    assert "moderator" not in tags
