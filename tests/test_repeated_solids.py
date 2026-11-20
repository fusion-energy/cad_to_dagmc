"""A solid that appears twice in the input is an overlap, and is rejected on add.

Two parts holding the same solid both claim its region. Assembly.imprint leaves
overlapping parts like that, with the region they share in each of them, and
exporting with imprint=False then skips the overlap checks that come with the
export's own imprint. CadQuery's Solids() drops the repeat, so before this check
the user got a mismatch between the numbers of volumes and material tags.
"""

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc

HAS_ASSEMBLY_IMPRINT = hasattr(cq.Assembly, "imprint")
needs_assembly_imprint = pytest.mark.skipif(
    not HAS_ASSEMBLY_IMPRINT, reason="CadQuery has no Assembly.imprint"
)


def _box(x=0.0, size=10.0):
    return cq.Workplane().transformed(offset=(x, 0, 0)).box(size, size, size)


@pytest.mark.parametrize("material_tags", ["assembly_names", ["a", "b"]])
def test_the_same_solid_in_two_parts_is_rejected(material_tags):
    solid = _box().val()
    assembly = cq.Assembly().add(solid, name="a").add(solid, name="b")
    with pytest.raises(ValueError, match="Overlapping solids in the CAD") as error:
        CadToDagmc().add_cadquery_object(assembly, material_tags=material_tags)
    assert "Parts 'a' and 'b' hold the same solid" in str(error.value)


def test_nested_parts_are_named_by_their_own_name():
    solid = _box().val()
    inner = cq.Assembly(name="group").add(solid, name="b").add(_box(20), name="c")
    assembly = cq.Assembly(name="top").add(solid, name="a").add(inner)
    with pytest.raises(ValueError, match="Parts 'a' and 'b' hold the same solid"):
        CadToDagmc().add_cadquery_object(assembly, material_tags="assembly_names")


def test_the_same_solid_twice_in_one_part_is_rejected():
    solid = _box().val()
    assembly = cq.Assembly().add(cq.Compound.makeCompound([solid, solid]), name="a")
    assembly.add(_box(20), name="b")
    with pytest.raises(ValueError, match="Part 'a' holds the same solid more than once"):
        CadToDagmc().add_cadquery_object(assembly, material_tags="assembly_names")


def test_the_same_solid_twice_in_a_compound_is_rejected():
    solid = _box().val()
    with pytest.raises(ValueError, match="CadQuery object holds the same solid more than once"):
        CadToDagmc().add_cadquery_object(
            cq.Compound.makeCompound([solid, solid]), material_tags=["a"]
        )


def test_a_shape_reused_at_different_locations_is_fine():
    """Placing one shape several times makes different solids, not repeats."""
    solid = _box().val()
    assembly = cq.Assembly()
    assembly.add(solid, name="a", loc=cq.Location((0, 0, 0)))
    assembly.add(solid, name="b", loc=cq.Location((10, 0, 0)))
    model = CadToDagmc()
    assert model.add_cadquery_object(assembly, material_tags="assembly_names") == 2
    assert model.material_tags == ["a", "b"]


def test_a_part_of_several_separate_solids_is_fine():
    two_boxes = cq.Compound.makeCompound([_box().val(), _box(20).val()])
    assembly = cq.Assembly().add(two_boxes, name="a").add(_box(40), name="b")
    model = CadToDagmc()
    assert model.add_cadquery_object(assembly, material_tags="assembly_names") == 3
    assert model.material_tags == ["a", "a", "b"]


@needs_assembly_imprint
def test_overlapping_parts_imprinted_by_the_user_are_rejected():
    assembly = cq.Assembly().add(_box(), name="a").add(_box(5), name="b")
    assembly.imprint()
    with pytest.raises(ValueError, match="Parts 'a' and 'b' hold the same solid"):
        CadToDagmc().add_cadquery_object(assembly, material_tags="assembly_names")


@needs_assembly_imprint
def test_touching_parts_imprinted_by_the_user_export_without_imprinting(tmp_path):
    assembly = cq.Assembly()
    for name, x in [("middle", 10), ("left", 0), ("right", 20)]:
        assembly.add(_box(x), name=name)
    assembly.imprint()
    model = CadToDagmc()
    assert model.add_cadquery_object(assembly, material_tags="assembly_names") == 3
    assert model.material_tags == ["middle", "left", "right"]
    assert [round(part.Center().x, 6) for part in model.parts] == [10, 0, 20]
    model.export_dagmc_h5m_file(
        filename=str(tmp_path / "imprinted.h5m"),
        meshing_backend="gmsh",
        imprint=False,
        max_mesh_size=5,
    )
