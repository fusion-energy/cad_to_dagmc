"""Tests that assembly_names and assembly_materials material tag counts
match the number of solids, even when leaf children have 0 or multiple solids."""

import cadquery as cq
from cad_to_dagmc import CadToDagmc


def test_assembly_names_single_solid_per_child():
    """Each child has one solid — tags should equal number of solids."""
    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").box(1, 1, 1), name="box_a")
    assembly.add(cq.Workplane("XY").box(1, 1, 1).translate((5, 0, 0)), name="box_b")

    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_names")

    assert len(model.material_tags) == len(model.parts)
    assert model.material_tags == ["box_a", "box_b"]


def test_assembly_names_child_with_no_solids():
    """A child with no solid geometry should not contribute a material tag."""
    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").box(1, 1, 1), name="has_solid")
    # Add a child that is just a wire (no solid)
    wire = cq.Workplane("XY").rect(2, 2).val()
    assembly.add(wire, name="no_solid")

    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_names")

    assert len(model.material_tags) == len(model.parts)
    assert model.material_tags == ["has_solid"]


def test_assembly_names_child_with_multiple_solids():
    """A child with multiple solids should repeat the tag for each solid."""
    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").box(1, 1, 1), name="single")
    # Create a compound of two separate solids
    solid_a = cq.Workplane("XY").box(1, 1, 1).val()
    solid_b = cq.Workplane("XY").box(1, 1, 1).translate((5, 0, 0)).val()
    compound = cq.Compound.makeCompound([solid_a, solid_b])
    assembly.add(compound, name="multi")

    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_names")

    assert len(model.material_tags) == len(model.parts)
    assert model.material_tags == ["single", "multi", "multi"]


def test_assembly_materials_single_solid_per_child():
    """assembly_materials with one solid per child should match."""
    assembly = cq.Assembly()
    assembly.add(
        cq.Workplane("XY").box(1, 1, 1),
        name="a",
        material=cq.Material("mat_a"),
    )
    assembly.add(
        cq.Workplane("XY").box(1, 1, 1).translate((5, 0, 0)),
        name="b",
        material=cq.Material("mat_b"),
    )

    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_materials")

    assert len(model.material_tags) == len(model.parts)
    assert model.material_tags == ["mat_a", "mat_b"]


def test_assembly_materials_child_with_no_solids():
    """assembly_materials: a child with no solid should not contribute a tag."""
    assembly = cq.Assembly()
    assembly.add(
        cq.Workplane("XY").box(1, 1, 1),
        name="has_solid",
        material=cq.Material("mat_solid"),
    )
    wire = cq.Workplane("XY").rect(2, 2).val()
    assembly.add(wire, name="no_solid", material=cq.Material("mat_wire"))

    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_materials")

    assert len(model.material_tags) == len(model.parts)
    assert model.material_tags == ["mat_solid"]


def test_assembly_materials_child_with_multiple_solids():
    """assembly_materials: a compound child should repeat tag per solid."""
    assembly = cq.Assembly()
    assembly.add(
        cq.Workplane("XY").box(1, 1, 1),
        name="single",
        material=cq.Material("mat_single"),
    )
    solid_a = cq.Workplane("XY").box(1, 1, 1).val()
    solid_b = cq.Workplane("XY").box(1, 1, 1).translate((5, 0, 0)).val()
    compound = cq.Compound.makeCompound([solid_a, solid_b])
    assembly.add(compound, name="multi", material=cq.Material("mat_multi"))

    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_materials")

    assert len(model.material_tags) == len(model.parts)
    assert model.material_tags == ["mat_single", "mat_multi", "mat_multi"]
