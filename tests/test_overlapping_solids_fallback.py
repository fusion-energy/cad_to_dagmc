"""Overlapping solids still mesh, even though they cannot be meshed per solid.

The cad-to-dagmc-mesher backend is driven through the mesher's ``solid_config``
API, which addresses solids by assembly child name. Imprinting overlapping solids
fuses them, so those names no longer exist in the imprinted compound and the
mesher raises ``OverlappingSolidsError``.

That must not become a hard failure: the positional ``material_tags`` API does not
depend on names and meshes this geometry, and it is what this backend used before.
The docs quickstart is exactly this case — a sphere inside a box — so a regression
here breaks the first thing a new user runs.
"""
import warnings

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc

pytest.importorskip("cad_to_dagmc_mesher")
di = pytest.importorskip("dagmc_h5m_file_inspector")


def _sphere_in_box():
    """The docs quickstart geometry: a sphere wholly inside a box."""
    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").sphere(10), name="tungsten")
    assembly.add(cq.Workplane("XY").box(30, 30, 30), name="steel")
    return assembly


def test_overlapping_solids_still_export(tmp_path):
    h5m = str(tmp_path / "overlapping.h5m")
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=_sphere_in_box(),
                              material_tags="assembly_names")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.export_dagmc_h5m_file(filename=h5m,
                                    meshing_backend="cad-to-dagmc-mesher")

    # the tags must survive the fallback, not just the export
    assert sorted(di.get_volumes_and_materials(h5m).values()) == ["steel", "tungsten"]


def test_overlapping_solids_say_why_per_solid_meshing_is_unavailable(tmp_path):
    """Silence would hide both the lost refinement and the invalid geometry."""
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=_sphere_in_box(),
                              material_tags="assembly_names")
    with pytest.warns(UserWarning, match="fused overlapping solids"):
        model.export_dagmc_h5m_file(filename=str(tmp_path / "warned.h5m"),
                                    meshing_backend="cad-to-dagmc-mesher")


def test_non_overlapping_solids_do_not_warn(tmp_path):
    """The fallback must not fire on well formed geometry."""
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10), name="steel")
    assembly.add(cq.Workplane().moveTo(10, 0).box(10, 10, 10), name="water")
    model = CadToDagmc()
    model.add_cadquery_object(cadquery_object=assembly,
                              material_tags="assembly_names")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.export_dagmc_h5m_file(filename=str(tmp_path / "clean.h5m"),
                                    meshing_backend="cad-to-dagmc-mesher")
    assert not [w for w in caught if "fused overlapping solids" in str(w.message)]
