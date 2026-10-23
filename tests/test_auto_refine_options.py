"""cad-to-dagmc-mesher's refinement can be controlled, and reports back.

export_dagmc_h5m_file used to call mesh_assembly with the mesher's refinement
defaults and no way to change them, and the only sign that refinement was cut
short by memory was a printed line. Issue 240: the same inputs gave different
meshes depending on how much memory was free, and the caller could neither pin
the behaviour nor see that it had happened.
"""

import cadquery as cq
import pytest

import cad_to_dagmc_mesher.cad as mesher_cad
from cad_to_dagmc import CadToDagmc

REFINE_KEYS = ("auto_refine", "memory_budget_gb", "max_refine_rounds")


def _two_touching_boxes():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(10, 0, 0)).box(10, 10, 10))
    return assembly


def _model():
    model = CadToDagmc()
    model.add_cadquery_object(_two_touching_boxes(), material_tags=["mat1", "mat2"])
    return model


@pytest.fixture
def captured(monkeypatch):
    """Record what mesh_assembly is called with, and let tests edit its result."""
    calls = []
    real = mesher_cad.mesh_assembly

    def spy(*args, **kwargs):
        result = real(*args, **kwargs)
        calls.append({"kwargs": kwargs, "result": result})
        for edit in spy.edits:
            edit(result)
        return result

    spy.edits = []
    monkeypatch.setattr(mesher_cad, "mesh_assembly", spy)
    return calls, spy


def _export(model, tmp_path, **kwargs):
    return model.export_dagmc_h5m_file(
        filename=str(tmp_path / "dagmc.h5m"),
        meshing_backend="cad-to-dagmc-mesher",
        tolerance=1.0,
        **kwargs,
    )


def test_refinement_options_are_accepted_and_forwarded(captured, tmp_path):
    calls, _ = captured
    _export(_model(), tmp_path, auto_refine=True, memory_budget_gb=8.0,
            max_refine_rounds=2)
    forwarded = calls[-1]["kwargs"]
    assert forwarded["auto_refine"] is True
    assert forwarded["memory_budget_gb"] == 8.0
    assert forwarded["max_refine_rounds"] == 2


def test_unset_options_leave_the_mesher_defaults_alone(captured, tmp_path):
    calls, _ = captured
    _export(_model(), tmp_path)
    assert not set(REFINE_KEYS) & set(calls[-1]["kwargs"])


def test_the_refinement_report_is_kept(captured, tmp_path):
    model = _model()
    assert model.refinement is None
    _export(model, tmp_path)
    assert model.refinement is not None
    assert {"rounds", "converged", "memory_limited"} <= set(model.refinement)


def test_no_refinement_leaves_no_report(captured, tmp_path):
    model = _model()
    _export(model, tmp_path)
    _export(model, tmp_path, auto_refine=False)
    assert model.refinement is None, "a stale report must not outlive its export"


def test_refinement_cut_short_by_memory_warns(captured, tmp_path):
    """A printed line is invisible to scripts and tests; a warning is not."""
    _, spy = captured

    def memory_limited(result):
        result["refinement"]["memory_limited"] = True
        result["refinement"]["remaining_folds"] = 7

    spy.edits.append(memory_limited)
    with pytest.warns(UserWarning, match="memory_budget_gb with 7 fold edge"):
        _export(_model(), tmp_path, memory_budget_gb=1.0)


def test_misspelt_refinement_options_are_still_rejected(tmp_path):
    with pytest.raises(ValueError, match="Invalid keyword arguments"):
        _export(_model(), tmp_path, auto_refines=False)
