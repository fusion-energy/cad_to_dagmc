"""The cad-to-dagmc-mesher auto-refine report is kept for inspection.

cad-to-dagmc-mesher refines folding solids automatically and returns a report
of what it did (rounds, convergence, remaining folds, final tolerances). It
used to be dropped, leaving a printed log as the only record. Refinement itself
needs no settings here: the mesher's default gives the same mesh whatever the
free memory, or raises (issue #240), so cad_to_dagmc exposes none.
"""

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc


def _model():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(10, 0, 0)).box(10, 10, 10))
    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags=["mat1", "mat2"])
    return model


def _export(model, tmp_path, **kwargs):
    return model.export_dagmc_h5m_file(filename=str(tmp_path / "dagmc.h5m"), **kwargs)


def test_the_refinement_report_is_kept(tmp_path):
    model = _model()
    assert model.refinement is None
    _export(model, tmp_path, meshing_backend="cad-to-dagmc-mesher", tolerance=1.0)
    assert model.refinement is not None
    assert {"rounds", "converged", "remaining_folds"} <= set(model.refinement)


def test_a_later_export_without_refinement_clears_the_report(tmp_path):
    """A stale report must not outlive the export it describes."""
    model = _model()
    _export(model, tmp_path, meshing_backend="cad-to-dagmc-mesher", tolerance=1.0)
    _export(model, tmp_path, meshing_backend="gmsh")
    assert model.refinement is None


@pytest.mark.parametrize("option", ["auto_refine", "memory_budget_gb", "max_refine_rounds"])
def test_refinement_has_no_user_settings(tmp_path, option):
    with pytest.raises(ValueError, match="Invalid keyword arguments"):
        _export(_model(), tmp_path, meshing_backend="cad-to-dagmc-mesher", **{option: 1})
