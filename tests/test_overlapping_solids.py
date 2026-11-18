"""Overlapping solids are rejected rather than meshed.

Overlapping CAD cannot be written as valid DAGMC: a region inside two volumes has
no single material, and a DAGMC surface separates at most two volumes. The failure
mode if it is meshed anyway is the bad kind — the h5m is watertight, transport
runs, and the material in the shared region is whichever volume DAGMC resolves
first. Nothing looks wrong.

That is not hypothetical. The docs quickstart put a sphere inside a box for a long
time and passed CI throughout, so anyone following it built a model with an
ambiguous region and no way to notice.

The imprint is what detects this: fusing overlapping solids means the per-solid
names no longer exist in the imprinted compound.
"""
import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc

pytest.importorskip("cad_to_dagmc_mesher")
di = pytest.importorskip("dagmc_h5m_file_inspector")


def _sphere_in_box():
    """What the docs quickstart used to do: a sphere wholly inside a box."""
    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").sphere(10), name="tungsten")
    assembly.add(cq.Workplane("XY").box(30, 30, 30), name="steel")
    return assembly


def _sphere_cut_from_box():
    """The same geometry made valid: the box has a spherical cavity."""
    sphere = cq.Workplane("XY").sphere(10)
    assembly = cq.Assembly()
    assembly.add(sphere, name="tungsten")
    assembly.add(cq.Workplane("XY").box(30, 30, 30).cut(sphere), name="steel")
    return assembly


def test_overlapping_solids_are_rejected(tmp_path):
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=_sphere_in_box(),
                              material_tags="assembly_names")
    with pytest.raises(ValueError, match="Overlapping solids in the CAD"):
        model.export_dagmc_h5m_file(filename=str(tmp_path / "overlapping.h5m"),
                                    meshing_backend="cad-to-dagmc-mesher")


def test_the_error_names_the_material_tags_not_internal_names(tmp_path):
    """The mesher reports synthetic per-solid names; users need their own tags."""
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=_sphere_in_box(),
                              material_tags="assembly_names")
    with pytest.raises(ValueError) as excinfo:
        model.export_dagmc_h5m_file(filename=str(tmp_path / "overlapping.h5m"),
                                    meshing_backend="cad-to-dagmc-mesher")
    message = str(excinfo.value)
    assert "tungsten" in message and "steel" in message
    # the synthetic names are an implementation detail and must not leak
    assert "#0" not in message and "#1" not in message


def test_the_error_says_how_to_fix_it(tmp_path):
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=_sphere_in_box(),
                              material_tags="assembly_names")
    with pytest.raises(ValueError, match="cut"):
        model.export_dagmc_h5m_file(filename=str(tmp_path / "overlapping.h5m"),
                                    meshing_backend="cad-to-dagmc-mesher")


def test_cutting_the_overlap_out_makes_it_valid(tmp_path):
    """The fix the error recommends has to actually work."""
    h5m = str(tmp_path / "cut.h5m")
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=_sphere_cut_from_box(),
                              material_tags="assembly_names")
    model.export_dagmc_h5m_file(filename=h5m,
                                meshing_backend="cad-to-dagmc-mesher")
    assert sorted(di.get_volumes_and_materials(h5m).values()) == ["steel", "tungsten"]


def test_touching_solids_are_still_fine(tmp_path):
    """Sharing a surface is normal and must not be mistaken for overlapping."""
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10), name="steel")
    assembly.add(cq.Workplane().moveTo(10, 0).box(10, 10, 10), name="water")
    h5m = str(tmp_path / "touching.h5m")
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=assembly,
                              material_tags="assembly_names")
    model.export_dagmc_h5m_file(filename=h5m,
                                meshing_backend="cad-to-dagmc-mesher")
    assert sorted(di.get_volumes_and_materials(h5m).values()) == ["steel", "water"]


def test_the_error_says_how_much_and_where(tmp_path):
    """Each overlapping pair is named, with the volume they share and its place.

    A whole sphere sunk in a box is a bulk overlap: all of the sphere.
    """
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=_sphere_in_box(),
                              material_tags="assembly_names")
    with pytest.raises(ValueError) as excinfo:
        model.export_dagmc_h5m_file(filename=str(tmp_path / "overlapping.h5m"),
                                    meshing_backend="cad-to-dagmc-mesher")
    message = str(excinfo.value)
    assert (
        "'tungsten' (solid 0) and 'steel' (solid 1) overlap by 4,189 cm³ "
        "(100.0% of 'tungsten', 15.5% of 'steel'), spanning 20 x 20 x 20 cm "
        "around (0, 0, 0)"
    ) in message, message
    assert "contact surface" not in message


def test_a_face_pressed_into_its_neighbour_is_described_as_such(tmp_path):
    """Two solids meant to touch, one face modelled 0.01 cm into the other.

    That is the common way real CAD overlaps: a layer far thinner than either
    solid, spread over the face they share, a tiny fraction of either volume.
    The message has to say that rather than leave a reader to infer it.
    """
    block = cq.Workplane().box(100, 100, 50).translate((0, 0, -25))
    slab = cq.Workplane().box(100, 100, 10).translate((0, 0, 5 - 0.01))
    model = CadToDagmc()
    model.add_cadquery_object(block, material_tags=["steel"])
    model.add_cadquery_object(slab, material_tags=["water"])
    with pytest.raises(ValueError) as excinfo:
        model.export_dagmc_h5m_file(filename=str(tmp_path / "overlapping.h5m"),
                                    meshing_backend="cad-to-dagmc-mesher")
    message = str(excinfo.value)
    assert (
        "'steel' (solid 0) and 'water' (solid 1) overlap by 100 cm³ along a "
        "contact surface (0.020% of 'steel', 0.1% of 'water'): a layer about "
        "0.01 cm thick, spanning 100 x 100 x 0.01 cm around (0, 0, -0.005)"
    ) in message, message


def test_the_mesher_message_is_passed_on_in_the_callers_names(monkeypatch, tmp_path):
    """Whatever the mesher says about the overlap reaches the user whole, with
    its per-solid names turned back into material tags and input positions."""
    import cad_to_dagmc_mesher.cad as mesher_cad

    def overlapping(*args, **kwargs):
        raise mesher_cad.OverlappingSolidsError(
            "Overlapping solids in the input CAD:\n"
            "  'steel#0' and 'water#1' overlap by 2.42 cm³ along a contact "
            "surface (0.000089% of 'steel#0', 0.00012% of 'water#1')\n"
            "Boolean-subtract the overlap in CAD (e.g. b = b.cut(a))."
        )

    monkeypatch.setattr(mesher_cad, "mesh_assembly", overlapping)
    model = CadToDagmc()
    model.add_cadquery_object(cq.Workplane().box(10, 10, 10), material_tags=["steel"])
    model.add_cadquery_object(
        cq.Workplane().moveTo(10, 0).box(10, 10, 10), material_tags=["water"]
    )
    with pytest.raises(ValueError) as excinfo:
        model.export_dagmc_h5m_file(filename=str(tmp_path / "overlapping.h5m"),
                                    meshing_backend="cad-to-dagmc-mesher")
    assert str(excinfo.value) == (
        "Overlapping solids in the CAD:\n"
        "  'steel' (solid 0) and 'water' (solid 1) overlap by 2.42 cm³ along a "
        "contact surface (0.000089% of 'steel', 0.00012% of 'water')\n"
        "Boolean-subtract the overlap in CAD (e.g. b = b.cut(a))."
    )
