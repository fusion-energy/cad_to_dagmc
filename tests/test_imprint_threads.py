"""Tests for passing a thread count to the imprint argument.

Imprinting runs in parallel and its peak RAM scales with the thread count, so
the imprint argument accepts a positive int as well as a bool. The int limits
the OpenCASCADE thread pool for the duration of the imprint and the previous
limit is put back afterwards so other cadquery operations are unaffected.
"""

import cadquery as cq
import pytest
from OCP.OSD import OSD_ThreadPool

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import imprint_assembly, resolve_imprint, thread_limit


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
