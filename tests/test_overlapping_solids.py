"""Overlapping solids are rejected rather than meshed.

Overlapping CAD cannot be written as valid DAGMC: a region inside two volumes has
no single material, and a DAGMC surface separates at most two volumes. The failure
mode if it is meshed anyway is the bad kind — the h5m is watertight, transport
runs, and the material in the shared region is whichever volume DAGMC resolves
first. Nothing looks wrong.

That is not hypothetical. The docs quickstart put a sphere inside a box for a long
time and passed CI throughout, so anyone following it built a model with an
ambiguous region and no way to notice.

Exporting runs the overlap checks that cost nothing: the imprint records what it
split where faces coincide, and fusing overlapping solids means the per-solid
names no longer exist in the imprinted compound. Neither sees every overlap (two
intersecting spheres pass both), and the exact check that does,
``CadToDagmc.check_overlaps``, can take hours on a large model, so it is the
user's to run rather than part of every export.
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


def test_check_overlaps_says_how_much_and_where():
    """Each overlapping pair is named by material tag and position, with the
    volume they share and its place. A whole sphere sunk in a box is a bulk
    overlap: all of the sphere."""
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=_sphere_in_box(),
                              material_tags="assembly_names")
    report = model.check_overlaps(progress=False)
    assert not report.clean
    assert [str(overlap) for overlap in report.overlaps] == [(
        "'tungsten (solid 0)' and 'steel (solid 1)' overlap by 4,189 cm³ "
        "(100.0% of 'tungsten (solid 0)', 15.5% of 'steel (solid 1)'), "
        "spanning 20 x 20 x 20 cm around (0, 0, 0)"
    )]


def _intersecting_spheres():
    model = CadToDagmc()
    model.add_cadquery_object(cq.Workplane().sphere(5), material_tags=["steel"])
    model.add_cadquery_object(
        cq.Workplane().transformed(offset=(5, 0, 0)).sphere(5), material_tags=["water"]
    )
    return model


def test_check_overlaps_finds_what_exporting_does_not(tmp_path):
    """Two intersecting spheres: no coincident faces for the imprint to split,
    and no solid swallowed, so the free checks exporting runs let them through
    (with the mesher's warning). The exact check names them."""
    model = _intersecting_spheres()
    model.export_dagmc_h5m_file(filename=str(tmp_path / "spheres.h5m"),
                                meshing_backend="cad-to-dagmc-mesher")
    report = model.check_overlaps(progress=False)
    assert [(o.name_a, o.name_b) for o in report.overlaps] == [
        ("steel (solid 0)", "water (solid 1)")
    ]
    # Two spheres of radius r with centres r apart share 5*pi*r^3/12.
    assert report.overlaps[0].shared == pytest.approx(5 * 3.14159265 * 5**3 / 12, rel=1e-3)


def test_check_overlaps_reports_at_the_export_scale():
    """Volumes and lengths are those of the exported geometry."""
    report = _intersecting_spheres().check_overlaps(scale_factor=10, progress=False)
    assert report.overlaps[0].shared == pytest.approx(1000 * 5 * 3.14159265 * 5**3 / 12, rel=1e-3)


def test_check_overlaps_can_look_at_some_material_tags_only():
    model = _intersecting_spheres()
    model.add_cadquery_object(
        cq.Workplane().transformed(offset=(50, 0, 0)).box(1, 1, 1), material_tags=["air"]
    )
    assert model.check_overlaps(material_tags=["air"], progress=False).clean
    assert len(model.check_overlaps(material_tags=["water"], progress=False).overlaps) == 1
    with pytest.raises(ValueError, match=r"No solid has the material tag\(s\) \['nope'\]"):
        model.check_overlaps(material_tags=["nope"], progress=False)


def test_check_overlaps_passes_touching_solids():
    model = CadToDagmc()
    model.add_cadquery_object(cq.Workplane().box(10, 10, 10), material_tags=["steel"])
    model.add_cadquery_object(cq.Workplane().moveTo(10, 0).box(10, 10, 10), material_tags=["water"])
    report = model.check_overlaps(progress=False)
    assert report.clean and report.pairs == 1


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
    # The error points to the method that checks every pair.
    assert "model.check_overlaps()" in message


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
