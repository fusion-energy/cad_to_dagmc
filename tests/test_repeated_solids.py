"""A solid that appears twice in the input is an overlap, and is rejected on add.

Two parts holding the same solid both claim its region. Assembly.imprint leaves
overlapping parts like that, with the region they share in each of them, and
exporting with imprint=False then skips the overlap checks that come with the
export's own imprint. CadQuery's Solids() drops the repeat, so before this check
the user got a mismatch between the numbers of volumes and material tags.
"""

import cadquery as cq
import pytest
from test_python_api import get_volumes_and_materials_from_h5m

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


def test_assembly_materials_are_checked_too():
    solid = _box().val()
    assembly = cq.Assembly()
    assembly.add(solid, name="a", material=cq.Material("steel"))
    assembly.add(solid, name="b", material=cq.Material("water"))
    with pytest.raises(ValueError, match="Parts 'a' and 'b' hold the same solid"):
        CadToDagmc().add_cadquery_object(assembly, material_tags="assembly_materials")


def test_three_parts_holding_one_solid_are_all_named():
    solid = _box().val()
    assembly = cq.Assembly()
    for name in "abc":
        assembly.add(solid, name=name)
    with pytest.raises(ValueError, match="Parts 'a', 'b' and 'c' hold the same solid"):
        CadToDagmc().add_cadquery_object(assembly, material_tags="assembly_names")


def test_every_repeated_solid_is_reported():
    first, second = _box().val(), _box(20).val()
    assembly = cq.Assembly()
    for name, solid in [("a", first), ("b", first), ("c", second), ("d", second)]:
        assembly.add(solid, name=name)
    with pytest.raises(ValueError) as error:
        CadToDagmc().add_cadquery_object(assembly, material_tags="assembly_names")
    assert "Parts 'a' and 'b' hold the same solid; Parts 'c' and 'd' hold the same solid" in str(error.value)


def test_a_rejected_object_leaves_the_model_unchanged():
    model = CadToDagmc()
    model.add_cadquery_object(_box(50), material_tags=["kept"])
    solid = _box().val()
    with pytest.raises(ValueError, match="Overlapping solids"):
        model.add_cadquery_object(
            cq.Assembly().add(solid, name="a").add(solid, name="b"),
            material_tags="assembly_names",
        )
    assert model.material_tags == ["kept"]
    assert len(model.parts) == 1


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
    h5m = str(tmp_path / "imprinted.h5m")
    model.export_dagmc_h5m_file(
        filename=h5m, meshing_backend="gmsh", imprint=False, max_mesh_size=5
    )
    assert get_volumes_and_materials_from_h5m(h5m) == {
        1: "mat:middle", 2: "mat:left", 3: "mat:right"
    }


@pytest.mark.parametrize("scale_factor", [1.0, 10.0])
def test_a_solid_added_by_an_earlier_call_is_rejected(scale_factor):
    """Scaling makes new solids, so the check compares what was given."""
    solid = _box().val()
    model = CadToDagmc()
    model.add_cadquery_object(solid, material_tags=["first"], scale_factor=scale_factor)
    with pytest.raises(ValueError, match="already added to the model by an earlier"):
        model.add_cadquery_object(solid, material_tags=["second"], scale_factor=scale_factor)
    assert model.material_tags == ["first"]
    assert len(model.parts) == 1


def test_a_part_repeating_an_earlier_solid_is_named():
    solid = _box().val()
    model = CadToDagmc()
    model.add_cadquery_object(solid, material_tags=["first"])
    assembly = cq.Assembly().add(_box(20), name="new").add(solid, name="again")
    with pytest.raises(ValueError, match="Part 'again' holds a solid already added"):
        model.add_cadquery_object(assembly, material_tags="assembly_names")


def test_a_rejected_call_does_not_stop_later_checks():
    first, second = _box().val(), _box(20).val()
    model = CadToDagmc()
    model.add_cadquery_object(first, material_tags=["first"])
    with pytest.raises(ValueError, match="Overlapping solids"):
        model.add_cadquery_object(
            cq.Assembly().add(second, name="a").add(second, name="b"),
            material_tags="assembly_names",
        )
    model.add_cadquery_object(second, material_tags=["second"])
    with pytest.raises(ValueError, match="already added"):
        model.add_cadquery_object(second, material_tags=["third"])
    assert model.material_tags == ["first", "second"]


def test_the_same_shape_moved_in_a_later_call_is_fine():
    solid = _box().val()
    model = CadToDagmc()
    model.add_cadquery_object(solid, material_tags=["first"])
    model.add_cadquery_object(solid.moved(cq.Location((20, 0, 0))), material_tags=["second"])
    assert model.material_tags == ["first", "second"]
