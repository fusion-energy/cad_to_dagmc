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
