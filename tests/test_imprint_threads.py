"""Explicit imprint options, scoped OCC threads, and mesher API parity.

Only False or a mapping with exactly 'threads' and 'glue' is accepted.
'all' requests the logical processor count, even when the caller previously
limited OCC. The previous pool is restored before subsequent meshing.
"""

import functools
import inspect
from collections import UserDict
from types import MappingProxyType
from typing import get_type_hints, is_typeddict
from unittest.mock import Mock

import cadquery as cq
import gmsh
import pytest
from OCP.OSD import OSD_Parallel, OSD_ThreadPool

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import (
    DEFAULT_IMPRINT,
    ImprintOptions,
    imprint_assembly,
    resolve_imprint,
    thread_limit,
)

GLUES = ("partial", "full", None)
MAPPING_FACTORIES = (dict, MappingProxyType, UserDict)
EXPORT_METHODS = (
    "export_dagmc_h5m_file",
    "export_gmsh_mesh_file",
    "export_unstructured_mesh_file",
)
INVALID_NON_MAPPINGS = (True, 0, 1, 4, -1, None, 1.0, "all", [], ())
INVALID_THREADS = (True, False, 0, -1, 1.0, 2.5, None, "1", "ALL", "", [], {})
INVALID_KEYS = (
    {},
    {"threads": 1},
    {"glue": "partial"},
    {"threads": 1, "glue": "partial", "extra": 2},
    {"thread": 1, "glue": "partial"},
    {"threads": 1, "glue": "partial", 2: "unknown", None: "unknown"},
    {"unexpected": True},
)


def _pool_threads():
    return OSD_ThreadPool.DefaultPool_s().NbThreads()


def _two_touching_boxes():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(0, 7, 0)).box(10, 4, 10))
    return assembly


def _model():
    model = CadToDagmc()
    model.add_cadquery_object(_two_touching_boxes(), material_tags=["mat1", "mat2"])
    return model


class TestResolveImprint:
    def test_only_false_disables_imprinting(self):
        assert resolve_imprint(False) == (False, None, "partial")

    @pytest.mark.parametrize("imprint", INVALID_NON_MAPPINGS)
    def test_non_mapping_and_legacy_shorthand_are_rejected(self, imprint):
        with pytest.raises(TypeError) as excinfo:
            resolve_imprint(imprint)
        assert str(excinfo.value) == (
            "imprint must be False or a dictionary with 'threads' and 'glue', "
            f"got {imprint!r}"
        )

    @pytest.mark.parametrize("mapping_factory", MAPPING_FACTORIES)
    @pytest.mark.parametrize("threads", ["all", 1, 4])
    @pytest.mark.parametrize("glue", GLUES)
    def test_valid_mappings_are_resolved_without_mutation(self, mapping_factory, threads, glue):
        options = mapping_factory({"threads": threads, "glue": glue})
        original = dict(options)
        expected_threads = (
            max(1, OSD_Parallel.NbLogicalProcessors_s()) if threads == "all" else threads
        )
        before = _pool_threads()
        assert resolve_imprint(options) == (True, expected_threads, glue)
        assert options == original
        assert _pool_threads() == before

    @pytest.mark.parametrize("processors", [-2, 0, 1, 7])
    def test_all_uses_at_least_one_logical_processor(self, monkeypatch, processors):
        monkeypatch.setattr(OSD_Parallel, "NbLogicalProcessors_s", lambda: processors)
        assert resolve_imprint(DEFAULT_IMPRINT) == (True, max(1, processors), "partial")

    def test_all_does_not_reuse_a_previously_limited_pool(self, monkeypatch):
        monkeypatch.setattr(OSD_Parallel, "NbLogicalProcessors_s", lambda: 4)
        before = _pool_threads()
        with thread_limit(1):
            assert resolve_imprint(DEFAULT_IMPRINT) == (True, 4, "partial")
            assert _pool_threads() == 1, "resolution alone must not change the OCC pool"
        assert _pool_threads() == before

    @pytest.mark.parametrize("mapping_factory", MAPPING_FACTORIES)
    @pytest.mark.parametrize("options", INVALID_KEYS)
    def test_requires_exactly_threads_and_glue(self, mapping_factory, options):
        imprint = mapping_factory(options.copy())
        original = dict(imprint)
        missing = {"threads", "glue"} - imprint.keys()
        unknown = imprint.keys() - {"threads", "glue"}
        with pytest.raises(ValueError) as excinfo:
            resolve_imprint(imprint)
        assert str(excinfo.value) == (
            "imprint requires exactly 'threads' and 'glue'; "
            f"missing keys: {sorted(missing, key=repr)!r}, "
            f"unknown keys: {sorted(unknown, key=repr)!r}"
        )
        assert imprint == original

    @pytest.mark.parametrize("mapping_factory", MAPPING_FACTORIES)
    @pytest.mark.parametrize("threads", INVALID_THREADS)
    def test_invalid_threads_are_rejected_without_mutation(self, mapping_factory, threads):
        imprint = mapping_factory({"threads": threads, "glue": "partial"})
        original = dict(imprint)
        with pytest.raises(ValueError) as excinfo:
            resolve_imprint(imprint)
        assert str(excinfo.value) == (
            f"imprint['threads'] must be 'all' or a positive int, got {threads!r}"
        )
        assert imprint == original

    @pytest.mark.parametrize("glue", ["off", "Partial", "shift", True, False, 1, [], {}])
    def test_invalid_glue_uses_the_mesher_error_text(self, glue):
        imprint = {"threads": 1, "glue": glue}
        original = imprint.copy()
        with pytest.raises(ValueError) as excinfo:
            resolve_imprint(imprint)
        assert str(excinfo.value) == (
            f'imprint[\'glue\'] must be "partial", "full" or None, got {glue!r}'
        )
        assert imprint == original

    def test_validation_order_matches_mesher(self):
        with pytest.raises(ValueError, match="requires exactly"):
            resolve_imprint({"threads": False, "glue": "off", "extra": 1})
        with pytest.raises(ValueError, match=r"imprint\['threads'\]"):
            resolve_imprint({"threads": False, "glue": "off"})


class TestImprintDefaults:
    def test_default_is_an_immutable_mapping(self):
        assert isinstance(DEFAULT_IMPRINT, MappingProxyType)
        assert dict(DEFAULT_IMPRINT) == {"threads": "all", "glue": "partial"}
        with pytest.raises(TypeError):
            DEFAULT_IMPRINT["threads"] = 1
        with pytest.raises(TypeError):
            del DEFAULT_IMPRINT["glue"]
        copy = dict(DEFAULT_IMPRINT)
        copy["threads"] = 1
        assert dict(DEFAULT_IMPRINT) == {"threads": "all", "glue": "partial"}

    @pytest.mark.parametrize("method_name", EXPORT_METHODS)
    def test_every_public_export_uses_the_same_immutable_default(self, method_name):
        parameters = inspect.signature(getattr(CadToDagmc, method_name)).parameters
        assert parameters["imprint"].default is DEFAULT_IMPRINT
        assert "imprint_glue" not in parameters
        assert "imprint_threads" not in parameters

    def test_options_typeddict_has_both_required_entries(self):
        assert is_typeddict(ImprintOptions)
        assert ImprintOptions.__required_keys__ == {"threads", "glue"}
        assert ImprintOptions.__optional_keys__ == frozenset()
        assert set(get_type_hints(ImprintOptions)) == {"threads", "glue"}
        options: ImprintOptions = {"threads": 1, "glue": None}
        assert resolve_imprint(options) == (True, 1, None)


def _resolver_outcome(resolver, imprint):
    try:
        return resolver(imprint)
    except (TypeError, ValueError) as error:
        return type(error), str(error)


@pytest.mark.parametrize("imprint", [False, *INVALID_NON_MAPPINGS])
def test_non_mapping_resolver_parity_with_released_mesher(imprint):
    mesher = pytest.importorskip("cad_to_dagmc_mesher.cad._assembly")
    assert _resolver_outcome(resolve_imprint, imprint) == _resolver_outcome(
        mesher._resolve_imprint, imprint
    )


@pytest.mark.parametrize("mapping_factory", MAPPING_FACTORIES)
@pytest.mark.parametrize(
    "options",
    [
        *({"threads": threads, "glue": glue} for threads in ("all", 1, 4) for glue in GLUES),
        *INVALID_KEYS,
        *({"threads": threads, "glue": "partial"} for threads in INVALID_THREADS),
        *({"threads": 1, "glue": glue} for glue in ("off", "Partial", True, False, 1, [], {})),
    ],
)
def test_mapping_resolver_parity_with_released_mesher(mapping_factory, options):
    mesher = pytest.importorskip("cad_to_dagmc_mesher.cad._assembly")
    imprint = mapping_factory(options.copy())
    original = dict(imprint)
    assert _resolver_outcome(resolve_imprint, imprint) == _resolver_outcome(
        mesher._resolve_imprint, imprint
    )
    assert imprint == original


class TestThreadLimit:
    def test_limit_is_applied_and_restored(self):
        before = _pool_threads()
        with thread_limit(2):
            assert _pool_threads() == 2
        assert _pool_threads() == before

    def test_limit_is_restored_after_an_exception(self):
        before = _pool_threads()
        with pytest.raises(RuntimeError), thread_limit(2):
            raise RuntimeError("meshing failed")
        assert _pool_threads() == before

    def test_none_leaves_the_pool_alone(self):
        before = _pool_threads()
        with thread_limit(None):
            assert _pool_threads() == before
        assert _pool_threads() == before


class TestImprintAssembly:
    def test_threads_are_restored_after_imprinting(self):
        before = _pool_threads()
        imprint_assembly(_two_touching_boxes(), threads=1)
        assert _pool_threads() == before

    def test_thread_count_does_not_change_the_imprint(self):
        """Fewer threads is a RAM and speed trade off, not a different result."""
        all_threads, _ = imprint_assembly(_two_touching_boxes())
        one_thread, _ = imprint_assembly(_two_touching_boxes(), threads=1)

        assert len(one_thread.Solids()) == len(all_threads.Solids())
        assert len(one_thread.Faces()) == len(all_threads.Faces())


@pytest.mark.parametrize(
    "meshing_backend", ["gmsh", "cad-to-dagmc-mesher"]
)
def test_export_dagmc_h5m_file_with_thread_limited_imprint(tmp_path, meshing_backend):
    """Every backend accepts the thread mapping and restores the caller's pool."""
    if meshing_backend == "cad-to-dagmc-mesher":
        pytest.importorskip("cad_to_dagmc_mesher")

    before = _pool_threads()
    h5m_filename = tmp_path / f"{meshing_backend}.h5m"

    _model().export_dagmc_h5m_file(
        filename=str(h5m_filename),
        meshing_backend=meshing_backend,
        imprint={"threads": 1, "glue": "partial"},
    )

    assert h5m_filename.is_file()
    assert _pool_threads() == before


def test_export_gmsh_mesh_file_with_thread_limited_imprint(tmp_path):
    before = _pool_threads()
    msh_filename = tmp_path / "mesh.msh"

    _model().export_gmsh_mesh_file(
        filename=str(msh_filename), imprint={"threads": 2, "glue": "partial"}
    )

    assert msh_filename.is_file()
    assert _pool_threads() == before


def test_export_unstructured_mesh_file_with_thread_limited_imprint(tmp_path):
    before = _pool_threads()
    vtk_filename = tmp_path / "umesh.vtk"

    _model().export_unstructured_mesh_file(
        filename=str(vtk_filename), meshing_backend="gmsh",
        imprint={"threads": 2, "glue": "partial"},
    )

    assert vtk_filename.is_file()
    assert _pool_threads() == before


@pytest.fixture
def imprint_spy(monkeypatch):
    """Record the size of the OCC thread pool each time an imprint runs.

    Restoring the pool afterwards is not enough on its own, the limit also has
    to be in place while the imprint is running. imprint_assembly and
    cad-to-dagmc-mesher both call cq.occ_impl.assembly.imprint, so patching it
    here catches the imprint whichever backend triggers it.
    """
    real_imprint = cq.occ_impl.assembly.imprint
    pool_sizes = []

    # functools.wraps keeps the signature visible to the inspect.signature
    # check in cad-to-dagmc-mesher that looks for the glue argument.
    @functools.wraps(real_imprint)
    def spy(*args, **kwargs):
        pool_sizes.append(_pool_threads())
        return real_imprint(*args, **kwargs)

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", spy)
    return pool_sizes


def _dagmc_h5m(backend, **kwargs):
    def export(model, tmp_path, imprint=DEFAULT_IMPRINT, **export_kwargs):
        options = kwargs | export_kwargs
        if "unstructured_volumes" in options or "tet_volumes" in options:
            options["umesh_filename"] = str(tmp_path / "umesh.vtk")
        return model.export_dagmc_h5m_file(
            filename=str(tmp_path / "dagmc.h5m"),
            meshing_backend=backend,
            imprint=imprint,
            **options,
        )

    return export


def _gmsh_mesh(model, tmp_path, imprint=DEFAULT_IMPRINT, **export_kwargs):
    return model.export_gmsh_mesh_file(
        filename=str(tmp_path / "mesh.msh"), imprint=imprint, **export_kwargs
    )


def _unstructured(backend, **kwargs):
    def export(model, tmp_path, imprint=DEFAULT_IMPRINT, **export_kwargs):
        return model.export_unstructured_mesh_file(
            filename=str(tmp_path / "umesh.vtk"),
            meshing_backend=backend,
            imprint=imprint,
            **(kwargs | export_kwargs),
        )

    return export


# Every route through the library that ends in an imprint, with the backends
# that need cad-to-dagmc-mesher flagged so they skip when it is not installed.
IMPRINT_PATHS = {
    "h5m_gmsh": (_dagmc_h5m("gmsh"), False),
    "h5m_mesher": (_dagmc_h5m("cad-to-dagmc-mesher"), True),
    "h5m_gmsh_with_umesh": (
        _dagmc_h5m("gmsh", unstructured_volumes=["mat1"]),
        False,
    ),
    "h5m_mesher_with_tets": (
        _dagmc_h5m(
            "cad-to-dagmc-mesher",
            tet_volumes=["mat1"],
            target_edge_length=3.0,
        ),
        True,
    ),
    "gmsh_mesh_file": (_gmsh_mesh, False),
    "unstructured_gmsh": (_unstructured("gmsh"), False),
    "unstructured_mesher": (_unstructured("cad-to-dagmc-mesher", target_edge_length=3.0), True),
}


@pytest.mark.parametrize("path", IMPRINT_PATHS.keys())
@pytest.mark.parametrize("requested", [1, 3])
def test_every_imprint_path_imprints_on_the_requested_threads(
    tmp_path, imprint_spy, path, requested
):
    """imprint['threads'] has to reach the imprint on every export path.

    The three export methods reach an imprint by several routes: some imprint
    directly, others hand the assembly to a backend that imprints inside its
    own meshing call. All of them must run the imprint on the requested number
    of threads and put the previous count back afterwards.
    """
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    before = _pool_threads()
    options = {"threads": requested, "glue": "partial"}
    original = options.copy()
    export(_model(), tmp_path, options)

    assert imprint_spy == [requested], (
        f"{path} imprinted with pool sizes {imprint_spy}, expected one imprint "
        f"on {requested} threads"
    )
    assert options == original
    assert _pool_threads() == before
    assert not gmsh.isInitialized()


@pytest.mark.parametrize("path", IMPRINT_PATHS.keys())
def test_every_imprint_path_all_overrides_and_restores_the_callers_pool(
    tmp_path, imprint_spy, path
):
    """The default actively requests logical processors, not the current pool."""
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    before = _pool_threads()
    with thread_limit(1):
        export(_model(), tmp_path, DEFAULT_IMPRINT)
        assert _pool_threads() == 1
    assert imprint_spy == [max(1, OSD_Parallel.NbLogicalProcessors_s())]
    assert _pool_threads() == before
    assert dict(DEFAULT_IMPRINT) == {"threads": "all", "glue": "partial"}
    assert not gmsh.isInitialized()


def test_mesher_backend_meshes_on_all_threads(tmp_path, monkeypatch, imprint_spy):
    """cad-to-dagmc-mesher imprints part way through its own meshing call, so
    only the imprint should be limited. Probing just after its imprint returns shows
    whether the pool is back up for the meshing that follows."""
    mesher_assembly = pytest.importorskip("cad_to_dagmc_mesher.cad._assembly")

    before = _pool_threads()
    pool_after_the_imprint = []
    real_imprint_assembly = mesher_assembly._imprint_assembly

    def spy(*args, **kwargs):
        result = real_imprint_assembly(*args, **kwargs)
        pool_after_the_imprint.append(_pool_threads())
        return result

    monkeypatch.setattr(mesher_assembly, "_imprint_assembly", spy)

    _model().export_dagmc_h5m_file(
        filename=str(tmp_path / "dagmc.h5m"),
        meshing_backend="cad-to-dagmc-mesher",
        imprint={"threads": 1, "glue": "partial"},
    )

    assert imprint_spy == [1], "the imprint should have been limited"
    assert pool_after_the_imprint == [before], (
        "the pool was still limited once the imprint had finished, the limit "
        "is leaking into the meshing"
    )


@pytest.fixture
def no_export_side_effects(monkeypatch):
    """Validation must precede assembly inspection, OCC, and both mesh backends."""
    guard = Mock(side_effect=AssertionError("geometry or meshing ran before validation"))
    for name in (
        "get_ids_from_assembly", "imprint_assembly", "init_gmsh",
        "_mesh_with_cad_to_dagmc_mesher",
    ):
        monkeypatch.setattr(f"cad_to_dagmc.core.{name}", guard)
    monkeypatch.setattr(CadToDagmc, "_export_unstructured_mesh_file_with_mesher", guard)
    return guard


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize(
    "imprint",
    [
        *INVALID_NON_MAPPINGS,
        *INVALID_KEYS,
        *({"threads": threads, "glue": "partial"} for threads in INVALID_THREADS),
    ],
)
def test_invalid_imprint_is_rejected_by_every_route_before_side_effects(
    tmp_path, path, imprint, no_export_side_effects
):
    export, _ = IMPRINT_PATHS[path]
    before = _pool_threads()
    error = TypeError if not isinstance(imprint, (dict, MappingProxyType, UserDict)) else ValueError
    original = imprint.copy() if isinstance(imprint, dict) else imprint
    with pytest.raises(error, match="imprint"):
        export(_model(), tmp_path, imprint)
    no_export_side_effects.assert_not_called()
    assert imprint == original
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("glue", GLUES)
@pytest.mark.parametrize("imprint", [False, DEFAULT_IMPRINT])
def test_removed_glue_keyword_is_rejected_by_every_route_before_side_effects(
    tmp_path, path, glue, imprint, no_export_side_effects
):
    export, _ = IMPRINT_PATHS[path]
    before = _pool_threads()
    error = ValueError if path.startswith("h5m_") else TypeError
    with pytest.raises(error, match="imprint_glue") as excinfo:
        export(_model(), tmp_path, imprint, imprint_glue=glue)
    if error is ValueError:
        assert "Invalid keyword arguments: ['imprint_glue']" in str(excinfo.value)
    else:
        assert "unexpected keyword argument 'imprint_glue'" in str(excinfo.value)
    no_export_side_effects.assert_not_called()
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("path", IMPRINT_PATHS)
def test_imprint_failure_restores_pool_and_backend_state(tmp_path, monkeypatch, path):
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")
    real_imprint = cq.occ_impl.assembly.imprint
    before = _pool_threads()

    @functools.wraps(real_imprint)
    def failing_imprint(*args, **kwargs):
        assert _pool_threads() == 1
        raise RuntimeError("imprint failed")

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", failing_imprint)
    options = {"threads": 1, "glue": "partial"}
    with pytest.raises(RuntimeError, match="imprint failed"):
        export(_model(), tmp_path, options)
    assert options == {"threads": 1, "glue": "partial"}
    assert cq.occ_impl.assembly.imprint is failing_imprint
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())
