"""Tests for passing a thread count to the imprint argument.

Imprinting runs in parallel and its peak RAM scales with the thread count, so
the imprint argument accepts a positive int as well as a bool. The int limits
the OpenCASCADE thread pool while the imprint runs and the previous limit is
put back afterwards so other cadquery operations are unaffected. The limit is
on the imprint alone: the meshing that follows it keeps all its threads, which
takes some care for the cadquery and cad-to-dagmc-mesher backends because they
imprint part way through their own meshing call.
"""

import functools

import cadquery as cq
import pytest
from OCP.OSD import OSD_ThreadPool

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import (
    imprint_assembly,
    imprint_thread_limit,
    resolve_imprint,
    thread_limit,
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
    def test_bools_leave_the_thread_count_alone(self):
        assert resolve_imprint(True) == (True, None)
        assert resolve_imprint(False) == (False, None)

    def test_positive_int_imprints_with_that_many_threads(self):
        assert resolve_imprint(1) == (True, 1)
        assert resolve_imprint(4) == (True, 4)

    @pytest.mark.parametrize("threads", [0, -1])
    def test_int_below_one_is_rejected(self, threads):
        """0 cannot mean off because bool is a subclass of int, so False and 0
        would be the same argument."""
        with pytest.raises(ValueError, match="not a valid number of threads"):
            resolve_imprint(threads)

    @pytest.mark.parametrize("imprint", ["2", 2.0, None])
    def test_non_int_is_rejected(self, imprint):
        with pytest.raises(TypeError, match="must be a bool or an int"):
            resolve_imprint(imprint)


class TestThreadLimit:
    def test_limit_is_applied_and_restored(self):
        before = _pool_threads()
        with thread_limit(2):
            assert _pool_threads() == 2
        assert _pool_threads() == before

    def test_limit_is_restored_after_an_exception(self):
        before = _pool_threads()
        with pytest.raises(RuntimeError):
            with thread_limit(2):
                raise RuntimeError("meshing failed")
        assert _pool_threads() == before

    def test_none_leaves_the_pool_alone(self):
        before = _pool_threads()
        with thread_limit(None):
            assert _pool_threads() == before
        assert _pool_threads() == before


class TestImprintThreadLimit:
    """The limit has to land on the imprint and on nothing either side of it."""

    def test_only_the_imprint_call_is_limited(self):
        before = _pool_threads()
        inside_the_imprint = []

        real_imprint = cq.occ_impl.assembly.imprint

        @functools.wraps(real_imprint)
        def spy(*args, **kwargs):
            inside_the_imprint.append(_pool_threads())
            return real_imprint(*args, **kwargs)

        cq.occ_impl.assembly.imprint = spy
        try:
            with imprint_thread_limit(2):
                # Stands in for the meshing a backend does before it imprints.
                assert _pool_threads() == before
                cq.occ_impl.assembly.imprint(_two_touching_boxes())
                # ...and for the meshing it does afterwards.
                assert _pool_threads() == before
        finally:
            cq.occ_impl.assembly.imprint = real_imprint

        assert inside_the_imprint == [2]
        assert _pool_threads() == before

    def test_the_original_imprint_is_put_back(self):
        real_imprint = cq.occ_impl.assembly.imprint
        with imprint_thread_limit(2):
            assert cq.occ_impl.assembly.imprint is not real_imprint
        assert cq.occ_impl.assembly.imprint is real_imprint

    def test_the_original_imprint_is_put_back_after_an_exception(self):
        real_imprint = cq.occ_impl.assembly.imprint
        before = _pool_threads()
        with pytest.raises(RuntimeError):
            with imprint_thread_limit(2):
                raise RuntimeError("meshing failed")
        assert cq.occ_impl.assembly.imprint is real_imprint
        assert _pool_threads() == before

    def test_the_glue_argument_stays_visible(self):
        """imprint_assembly and cad-to-dagmc-mesher both inspect the signature
        to decide whether to pass glue="partial", so the wrapper must not hide
        it."""
        import inspect

        real_params = inspect.signature(cq.occ_impl.assembly.imprint).parameters
        with imprint_thread_limit(2):
            wrapped_params = inspect.signature(cq.occ_impl.assembly.imprint).parameters
        assert list(wrapped_params) == list(real_params)

    def test_none_leaves_the_imprint_alone(self):
        real_imprint = cq.occ_impl.assembly.imprint
        with imprint_thread_limit(None):
            assert cq.occ_impl.assembly.imprint is real_imprint


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
    "meshing_backend", ["gmsh", "cadquery", "cad-to-dagmc-mesher"]
)
def test_export_dagmc_h5m_file_with_thread_limited_imprint(tmp_path, meshing_backend):
    """Every backend accepts imprint=1 and leaves the thread pool as it found it."""
    if meshing_backend == "cad-to-dagmc-mesher":
        pytest.importorskip("cad_to_dagmc_mesher")

    before = _pool_threads()
    h5m_filename = tmp_path / f"{meshing_backend}.h5m"

    _model().export_dagmc_h5m_file(
        filename=str(h5m_filename),
        meshing_backend=meshing_backend,
        imprint=1,
    )

    assert h5m_filename.is_file()
    assert _pool_threads() == before


def test_export_gmsh_mesh_file_with_thread_limited_imprint(tmp_path):
    before = _pool_threads()
    msh_filename = tmp_path / "mesh.msh"

    _model().export_gmsh_mesh_file(filename=str(msh_filename), imprint=2)

    assert msh_filename.is_file()
    assert _pool_threads() == before


def test_export_unstructured_mesh_file_with_thread_limited_imprint(tmp_path):
    before = _pool_threads()
    vtk_filename = tmp_path / "umesh.vtk"

    _model().export_unstructured_mesh_file(
        filename=str(vtk_filename), meshing_backend="gmsh", imprint=2
    )

    assert vtk_filename.is_file()
    assert _pool_threads() == before


@pytest.fixture
def imprint_spy(monkeypatch):
    """Record the size of the OCC thread pool each time an imprint runs.

    Restoring the pool afterwards is not enough on its own, the limit also has
    to be in place while the imprint is running. The cadquery plugin and
    cad-to-dagmc-mesher call cq.occ_impl.assembly.imprint themselves, so
    patching it here catches the imprint whichever backend triggers it.
    """
    real_imprint = cq.occ_impl.assembly.imprint
    pool_sizes = []

    # functools.wraps keeps the signature visible to the inspect.signature
    # check in imprint_assembly that looks for the glue argument.
    @functools.wraps(real_imprint)
    def spy(*args, **kwargs):
        pool_sizes.append(_pool_threads())
        return real_imprint(*args, **kwargs)

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", spy)
    return pool_sizes


def _dagmc_h5m(backend, **kwargs):
    def export(model, tmp_path, imprint):
        model.export_dagmc_h5m_file(
            filename=str(tmp_path / "dagmc.h5m"),
            meshing_backend=backend,
            imprint=imprint,
            **kwargs,
        )

    return export


def _gmsh_mesh(model, tmp_path, imprint):
    model.export_gmsh_mesh_file(filename=str(tmp_path / "mesh.msh"), imprint=imprint)


def _unstructured(backend, **kwargs):
    def export(model, tmp_path, imprint):
        model.export_unstructured_mesh_file(
            filename=str(tmp_path / "umesh.vtk"),
            meshing_backend=backend,
            imprint=imprint,
            **kwargs,
        )

    return export


# Every route through the library that ends in an imprint, with the backends
# that need cad-to-dagmc-mesher flagged so they skip when it is not installed.
IMPRINT_PATHS = {
    "h5m_gmsh": (_dagmc_h5m("gmsh"), False),
    "h5m_cadquery": (_dagmc_h5m("cadquery"), False),
    "h5m_mesher": (_dagmc_h5m("cad-to-dagmc-mesher"), True),
    "h5m_gmsh_with_umesh": (
        _dagmc_h5m("gmsh", unstructured_volumes=["mat1"], umesh_filename="umesh.vtk"),
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
def test_every_imprint_path_imprints_on_the_requested_threads(
    tmp_path, monkeypatch, imprint_spy, path
):
    """imprint=<int> has to reach the imprint on every export path.

    The three export methods reach an imprint by several routes: some imprint
    directly, others hand the assembly to a backend that imprints inside its
    own meshing call. All of them must run the imprint on the requested number
    of threads and put the previous count back afterwards.
    """
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    requested = 3
    before = _pool_threads()
    # umesh_filename is relative in one of the cases above, so write from
    # tmp_path rather than littering the repo.
    monkeypatch.chdir(tmp_path)

    export(_model(), tmp_path, requested)

    assert imprint_spy == [requested], (
        f"{path} imprinted with pool sizes {imprint_spy}, expected one imprint "
        f"on {requested} threads"
    )
    assert _pool_threads() == before


@pytest.mark.parametrize("path", IMPRINT_PATHS.keys())
def test_every_imprint_path_leaves_the_pool_alone_for_bools(
    tmp_path, monkeypatch, imprint_spy, path
):
    """imprint=True must not touch the pool, it imprints on whatever is set."""
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    before = _pool_threads()
    monkeypatch.chdir(tmp_path)

    export(_model(), tmp_path, True)

    assert imprint_spy == [before]
    assert _pool_threads() == before


def test_cadquery_backend_tessellates_on_all_threads(tmp_path, monkeypatch, imprint_spy):
    """The plugin imprints inside toMesh, but only the imprint is limited.

    BRepMesh_IncrementalMesh is the tessellation and it runs on the same OCC
    pool as the imprint, so it is what would be slowed down if the limit
    covered the whole toMesh call instead of just the imprint.
    """
    plugin = pytest.importorskip("cadquery_direct_mesh_plugin.plugin")

    before = _pool_threads()
    tessellation_pool_sizes = []
    real_tessellate = plugin.BRepMesh_IncrementalMesh

    def spy(*args, **kwargs):
        tessellation_pool_sizes.append(_pool_threads())
        return real_tessellate(*args, **kwargs)

    monkeypatch.setattr(plugin, "BRepMesh_IncrementalMesh", spy)

    _model().export_dagmc_h5m_file(
        filename=str(tmp_path / "dagmc.h5m"),
        meshing_backend="cadquery",
        imprint=1,
    )

    assert imprint_spy == [1], "the imprint should have been limited"
    assert tessellation_pool_sizes, "the plugin did not tessellate anything"
    assert set(tessellation_pool_sizes) == {before}, (
        "tessellation ran on a limited pool, the imprint limit is leaking into "
        "the meshing"
    )


def test_mesher_backend_meshes_on_all_threads(tmp_path, monkeypatch, imprint_spy):
    """Same again for cad-to-dagmc-mesher, which also imprints part way
    through its own meshing call. Probing just after its imprint returns shows
    whether the pool is back up for the meshing that follows."""
    mesher_assembly = pytest.importorskip("cad_to_dagmc_mesher.cad._assembly")
    if not hasattr(mesher_assembly, "_imprint_assembly"):
        pytest.skip("cad-to-dagmc-mesher no longer has _imprint_assembly to probe")

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
        imprint=1,
    )

    assert imprint_spy == [1], "the imprint should have been limited"
    assert pool_after_the_imprint == [before], (
        "the pool was still limited once the imprint had finished, the limit "
        "is leaking into the meshing"
    )


@pytest.mark.parametrize(
    "export",
    ["export_dagmc_h5m_file", "export_gmsh_mesh_file", "export_unstructured_mesh_file"],
)
def test_invalid_imprint_is_rejected_by_every_export(tmp_path, export):
    """The argument is checked before any meshing so the failure is quick."""
    filenames = {
        "export_dagmc_h5m_file": "dagmc.h5m",
        "export_gmsh_mesh_file": "mesh.msh",
        "export_unstructured_mesh_file": "umesh.vtk",
    }
    method = getattr(_model(), export)

    with pytest.raises(ValueError, match="not a valid number of threads"):
        method(filename=str(tmp_path / filenames[export]), imprint=0)
