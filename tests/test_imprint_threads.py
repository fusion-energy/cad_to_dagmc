"""Scalar imprint modes and OCC limits scoped to imprinting, not meshing."""

import functools
import inspect
from contextlib import nullcontext
from unittest.mock import Mock

import cadquery as cq
import gmsh
import numpy as np
import pytest
from OCP.OSD import OSD_Parallel, OSD_ThreadPool

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import (
    imprint_assembly,
    resolve_imprint,
    thread_limit,
)

GLUES = ("partial", "full", None)
IMPRINT_MODES = (*GLUES, False)
INVALID_MODES = (True, 0, 1, 4, -1, 0.0, 1.0, "all", "off", "Partial", [], (), {},
                 {"threads": 1, "glue": "partial"})
INVALID_THREADS = (True, False, 0, -1, 1.0, 2.5, None, "1", "ALL", "", [], {})
MODE_ERROR = "imprint must be 'partial', 'full', None or False, got "
THREAD_ERROR = "imprint_threads must be 'all' or a positive int, got "
EXPORT_METHODS = (
    "export_dagmc_h5m_file", "export_gmsh_mesh_file", "export_unstructured_mesh_file",
)
# Public method, backend options, and every expected output for each route.
IMPRINT_PATHS = {
    "h5m_gmsh": (EXPORT_METHODS[0], {"meshing_backend": "gmsh"}, ("dagmc.h5m",)),
    "h5m_mesher": (EXPORT_METHODS[0], {"meshing_backend": "cad-to-dagmc-mesher"}, ("dagmc.h5m",)),
    "h5m_umesh_gmsh": (
        EXPORT_METHODS[0], {"meshing_backend": "gmsh", "unstructured_volumes": ["mat1"]},
        ("dagmc.h5m", "umesh.vtk"),
    ),
    "h5m_umesh_mesher": (
        EXPORT_METHODS[0], {"meshing_backend": "cad-to-dagmc-mesher", "tet_volumes": ["mat1"],
                            "target_edge_length": 3.0}, ("dagmc.h5m", "umesh.vtk"),
    ),
    "msh": (EXPORT_METHODS[1], {}, ("mesh.msh",)),
    "umesh_gmsh": (EXPORT_METHODS[2], {"meshing_backend": "gmsh"}, ("umesh.vtk",)),
    "umesh_mesher": (
        EXPORT_METHODS[2], {"meshing_backend": "cad-to-dagmc-mesher", "target_edge_length": 3.0},
        ("umesh.vtk",),
    ),
}


def _pool_threads():
    return OSD_ThreadPool.DefaultPool_s().NbThreads()


def _two_touching_boxes():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(10, 0, 0)).box(10, 10, 10))
    return assembly


def _model(single_solid=False):
    model = CadToDagmc()
    shape = cq.Workplane().box(10, 10, 10) if single_solid else _two_touching_boxes()
    model.add_cadquery_object(shape, material_tags=["mat1"] if single_solid else ["mat1", "mat2"])
    return model


def _export(path, model, tmp_path, imprint="partial", *, imprint_threads="all"):
    method, options, outputs = IMPRINT_PATHS[path]
    if options.get("meshing_backend") == "cad-to-dagmc-mesher":
        pytest.importorskip("cad_to_dagmc_mesher")
    options = dict(options)
    if len(outputs) == 2:
        options["umesh_filename"] = str(tmp_path / outputs[1])
    return getattr(model, method)(
        filename=str(tmp_path / outputs[0]), imprint=imprint,
        imprint_threads=imprint_threads, **options,
    )


def _assert_outputs(path, tmp_path):
    for filename in IMPRINT_PATHS[path][2]:
        assert (tmp_path / filename).stat().st_size > 0
    assert not gmsh.isInitialized()


@pytest.fixture
def imprint_calls(monkeypatch):
    real_imprint = cq.occ_impl.assembly.imprint
    calls = []

    # Signature detection must still see whether CadQuery supports glue.
    @functools.wraps(real_imprint)
    def spy(*args, **kwargs):
        calls.append((_pool_threads(), kwargs.get("glue", "legacy")))
        return real_imprint(*args, **kwargs)

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", spy)
    return calls


@pytest.mark.parametrize("imprint", IMPRINT_MODES)
@pytest.mark.parametrize("threads", ["all", 1, 4])
def test_scalar_modes_and_threads_are_resolved_without_changing_pool(imprint, threads):
    before = _pool_threads()
    expected = max(1, OSD_Parallel.NbLogicalProcessors_s()) if threads == "all" else threads
    assert resolve_imprint(imprint, threads) == expected
    assert _pool_threads() == before


def test_int_like_threads_are_accepted():
    assert resolve_imprint("partial", np.int64(4)) == 4


@pytest.mark.parametrize("processors", [0, 1, 7])
def test_all_uses_logical_processors_not_the_current_pool(monkeypatch, processors):
    monkeypatch.setattr(OSD_Parallel, "NbLogicalProcessors_s", lambda: processors)
    with thread_limit(2):
        assert resolve_imprint() == max(1, processors)
        assert _pool_threads() == 2


@pytest.mark.parametrize("imprint", INVALID_MODES)
def test_invalid_modes_are_rejected_before_threads(imprint):
    with pytest.raises(ValueError) as error:
        resolve_imprint(imprint, imprint_threads=0)
    assert str(error.value) == f"{MODE_ERROR}{imprint!r}"


@pytest.mark.parametrize("imprint", ["partial", False])
@pytest.mark.parametrize("threads", INVALID_THREADS)
def test_invalid_threads_are_rejected_even_when_imprint_is_disabled(imprint, threads):
    with pytest.raises(ValueError) as error:
        resolve_imprint(imprint, imprint_threads=threads)
    assert str(error.value) == f"{THREAD_ERROR}{threads!r}"


@pytest.mark.parametrize("method", EXPORT_METHODS)
def test_public_signatures_have_scalar_defaults_and_keyword_only_threads(method):
    parameters = inspect.signature(getattr(CadToDagmc, method)).parameters
    assert parameters["imprint"].default == "partial"
    assert parameters["imprint_threads"].default == "all"
    assert parameters["imprint_threads"].kind is inspect.Parameter.KEYWORD_ONLY
    assert not {"glue", "imprint_glue"} & parameters.keys()


@pytest.mark.parametrize("threads", [None, 1, 3])
@pytest.mark.parametrize("fail", [False, True])
def test_thread_limit_restores_the_pool(threads, fail):
    before = _pool_threads()
    expected_response = pytest.raises(RuntimeError) if fail else nullcontext()
    with expected_response, thread_limit(threads):
        assert _pool_threads() == (before if threads is None else threads)
        if fail:
            raise RuntimeError("imprint failed")
    assert _pool_threads() == before


def test_thread_count_does_not_change_topology():
    all_threads, _ = imprint_assembly(_two_touching_boxes())
    one_thread, _ = imprint_assembly(_two_touching_boxes(), threads=1)
    assert len(one_thread.Solids()) == len(all_threads.Solids()) == 2
    assert len(one_thread.Faces()) == len(all_threads.Faces()) == 11


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("requested", [1, 3])
def test_every_path_limits_imprint_but_not_meshing(tmp_path, monkeypatch, imprint_calls, path, requested):
    if IMPRINT_PATHS[path][1].get("meshing_backend") == "cad-to-dagmc-mesher":
        boundary = pytest.importorskip("cad_to_dagmc_mesher.cad._assembly")
        name = "_imprint_assembly"
    else:
        from cad_to_dagmc import core as boundary
        name = "init_gmsh"
    original = getattr(boundary, name)
    meshing_threads = []

    def probe(*args, **kwargs):
        result = original(*args, **kwargs)
        meshing_threads.append(_pool_threads())
        return result

    monkeypatch.setattr(boundary, name, probe)
    before = _pool_threads()
    with thread_limit(2):
        _export(path, _model(), tmp_path, imprint_threads=requested)
        assert _pool_threads() == 2
    assert [threads for threads, _ in imprint_calls] == [requested]
    assert meshing_threads == [2], "the imprint limit must not leak into meshing"
    assert _pool_threads() == before
    _assert_outputs(path, tmp_path)


@pytest.mark.parametrize("path", IMPRINT_PATHS)
def test_all_overrides_and_restores_a_previously_limited_pool(tmp_path, imprint_calls, path):
    before = _pool_threads()
    with thread_limit(1):
        _export(path, _model(), tmp_path)
        assert _pool_threads() == 1
    assert [threads for threads, _ in imprint_calls] == [max(1, OSD_Parallel.NbLogicalProcessors_s())]
    assert _pool_threads() == before
    _assert_outputs(path, tmp_path)


@pytest.mark.parametrize("path", IMPRINT_PATHS)
def test_imprint_failure_restores_pool_and_backend_state(tmp_path, monkeypatch, path):
    real_imprint = cq.occ_impl.assembly.imprint
    before = _pool_threads()

    @functools.wraps(real_imprint)
    def failing_imprint(*args, **kwargs):
        assert _pool_threads() == 1
        raise RuntimeError("imprint failed")

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", failing_imprint)
    with pytest.raises(RuntimeError, match="imprint failed"):
        _export(path, _model(), tmp_path, imprint_threads=1)
    assert cq.occ_impl.assembly.imprint is failing_imprint
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.fixture
def no_export_side_effects(monkeypatch):
    guard = Mock(side_effect=AssertionError("geometry or meshing ran before validation"))
    for name in ("get_ids_from_assembly", "imprint_assembly", "init_gmsh", "_mesh_with_cad_to_dagmc_mesher"):
        monkeypatch.setattr(f"cad_to_dagmc.core.{name}", guard)
    monkeypatch.setattr(CadToDagmc, "_export_unstructured_mesh_file_with_mesher", guard)
    return guard


@pytest.mark.parametrize("method, suffix", tuple(zip(EXPORT_METHODS, ("h5m", "msh", "vtk"))))
@pytest.mark.parametrize("imprint, threads, message", [
    *((mode, 0, f"{MODE_ERROR}{mode!r}") for mode in INVALID_MODES),
    *((mode, threads, f"{THREAD_ERROR}{threads!r}")
      for mode in ("partial", False) for threads in INVALID_THREADS),
])
def test_public_methods_validate_before_side_effects(
    tmp_path, no_export_side_effects, method, suffix, imprint, threads, message,
):
    before = _pool_threads()
    with pytest.raises(ValueError) as error:
        getattr(_model(), method)(
            filename=str(tmp_path / f"mesh.{suffix}"),
            imprint=imprint, imprint_threads=threads,
        )
    assert str(error.value) == message
    no_export_side_effects.assert_not_called()
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("method, suffix", tuple(zip(EXPORT_METHODS, ("h5m", "msh", "vtk"))))
@pytest.mark.parametrize("keyword", ["glue", "imprint_glue"])
def test_public_methods_reject_removed_glue_keywords(tmp_path, no_export_side_effects, method, suffix, keyword):
    error = ValueError if method == EXPORT_METHODS[0] else TypeError
    with pytest.raises(error, match=keyword):
        getattr(_model(), method)(filename=str(tmp_path / f"mesh.{suffix}"), **{keyword: None})
    no_export_side_effects.assert_not_called()
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())
