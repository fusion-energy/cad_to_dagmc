"""mesh_threads is passed to the cad-to-dagmc-mesher backend and validated.

The mesher runs the parallel work of meshing after the imprint on that many
threads; "all" (the default) leaves it as it was. The gmsh backend has its
own threads argument, so it warns that mesh_threads is unused.
"""

import functools
import inspect
import warnings
from unittest.mock import Mock

import cadquery as cq
import gmsh
import pytest

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import resolve_mesh_threads

INVALID_THREADS = (True, False, 0, -1, 1.0, 2.5, None, "1", "ALL", "", [], {})
THREAD_ERROR = "mesh_threads must be 'all' or a positive int, got "
METHODS = (("export_dagmc_h5m_file", "h5m"), ("export_unstructured_mesh_file", "vtk"))


def _model():
    model = CadToDagmc()
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().sphere(5))
    assembly.add(cq.Workplane().sphere(8).cut(cq.Workplane().sphere(5)))
    model.add_cadquery_object(assembly, material_tags=["mat1", "mat2"])
    return model


def _mesher_export(method, tmp_path, **kwargs):
    if method == "export_dagmc_h5m_file":
        return _model().export_dagmc_h5m_file(
            filename=str(tmp_path / "dagmc.h5m"), meshing_backend="cad-to-dagmc-mesher",
            tolerance=1.0, angular_tolerance=0.5, **kwargs,
        )
    return _model().export_unstructured_mesh_file(
        filename=str(tmp_path / "umesh.vtk"), meshing_backend="cad-to-dagmc-mesher",
        target_edge_length=3.0, tolerance=1.0, angular_tolerance=0.5, **kwargs,
    )


@pytest.fixture
def mesher_calls(monkeypatch):
    mesher = pytest.importorskip("cad_to_dagmc_mesher.cad")
    real = mesher.mesh_assembly
    calls = []

    # Keeps the real signature, which the compatibility check reads.
    @functools.wraps(real)
    def spy(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(mesher, "mesh_assembly", spy)
    return calls


@pytest.mark.parametrize("method, _suffix", METHODS)
def test_default_is_all_and_keyword_only(method, _suffix):
    parameters = inspect.signature(getattr(CadToDagmc, method)).parameters
    assert parameters["mesh_threads"].default == "all"
    assert parameters["mesh_threads"].kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.parametrize("threads", INVALID_THREADS)
def test_invalid_threads_are_rejected(threads):
    with pytest.raises(ValueError) as error:
        resolve_mesh_threads(threads)
    assert str(error.value) == f"{THREAD_ERROR}{threads!r}"


@pytest.mark.parametrize("method, suffix", METHODS)
@pytest.mark.parametrize("backend", ["gmsh", "cad-to-dagmc-mesher"])
@pytest.mark.parametrize("threads", [0, True, "4"])
def test_public_methods_validate_before_side_effects(
    tmp_path, monkeypatch, method, suffix, backend, threads,
):
    guard = Mock(side_effect=AssertionError("geometry or meshing ran before validation"))
    for name in ("get_ids_from_assembly", "imprint_assembly", "init_gmsh",
                 "_mesh_with_cad_to_dagmc_mesher"):
        monkeypatch.setattr(f"cad_to_dagmc.core.{name}", guard)
    monkeypatch.setattr(CadToDagmc, "_export_unstructured_mesh_file_with_mesher", guard)
    with pytest.raises(ValueError) as error:
        getattr(_model(), method)(
            filename=str(tmp_path / f"mesh.{suffix}"), meshing_backend=backend,
            mesh_threads=threads,
        )
    assert str(error.value) == f"{THREAD_ERROR}{threads!r}"
    guard.assert_not_called()
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("method, _suffix", METHODS)
def test_mesh_threads_reaches_the_mesher(tmp_path, mesher_calls, method, _suffix):
    _mesher_export(method, tmp_path, mesh_threads=2, imprint_threads=1)
    assert [(c["mesh_threads"], c["imprint_threads"]) for c in mesher_calls] == [(2, 1)]


@pytest.mark.parametrize("method, _suffix", METHODS)
def test_all_is_not_passed_so_older_meshers_still_work(tmp_path, mesher_calls, method, _suffix):
    _mesher_export(method, tmp_path)
    assert len(mesher_calls) == 1 and "mesh_threads" not in mesher_calls[0]


@pytest.mark.parametrize("method, _suffix", METHODS)
def test_a_mesher_without_mesh_threads_refuses_a_limit(tmp_path, monkeypatch, method, _suffix):
    mesher = pytest.importorskip("cad_to_dagmc_mesher.cad")
    real = mesher.mesh_assembly

    def older(assembly, solid_config=None, imprint="partial", *, imprint_threads="all"):
        return real(assembly, solid_config=solid_config, imprint=imprint,
                    imprint_threads=imprint_threads)

    monkeypatch.setattr(mesher, "mesh_assembly", older)
    with pytest.raises(RuntimeError, match="cannot limit its meshing threads"):
        _mesher_export(method, tmp_path, mesh_threads=1)
    # The default needs nothing the older mesher lacks.
    assert _mesher_export(method, tmp_path)


def test_thread_count_does_not_change_the_mesh(tmp_path, monkeypatch):
    mesher = pytest.importorskip("cad_to_dagmc_mesher.cad")
    if "mesh_threads" not in inspect.signature(mesher.mesh_assembly).parameters:
        pytest.skip("installed cad-to-dagmc-mesher has no mesh_threads")
    real = mesher.mesh_assembly
    meshes = {}

    @functools.wraps(real)
    def keep(*args, **kwargs):
        result = real(*args, **kwargs)
        threads = kwargs.get("mesh_threads", "all")
        meshes[threads] = (result["vertices"], result["triangles_by_solid_by_face"])
        return result

    monkeypatch.setattr(mesher, "mesh_assembly", keep)
    for threads in (1, 2, 4, 8, "all"):
        _mesher_export("export_dagmc_h5m_file", tmp_path, mesh_threads=threads)
    assert list(meshes) == [1, 2, 4, 8, "all"]
    assert all(mesh == meshes[1] for mesh in meshes.values())


@pytest.mark.parametrize("method, suffix, options", [
    ("export_dagmc_h5m_file", "h5m", {}),
    ("export_unstructured_mesh_file", "vtk", {"max_mesh_size": 5}),
])
def test_gmsh_backend_warns_that_mesh_threads_is_unused(tmp_path, method, suffix, options):
    with pytest.warns(UserWarning, match="ignored when using GMSH backend: mesh_threads"):
        getattr(_model(), method)(
            filename=str(tmp_path / f"mesh.{suffix}"), meshing_backend="gmsh",
            mesh_threads=2, **options,
        )
    assert not gmsh.isInitialized()


@pytest.mark.parametrize("method, suffix", METHODS)
def test_gmsh_backend_does_not_warn_for_the_default(tmp_path, method, suffix):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        getattr(_model(), method)(
            filename=str(tmp_path / f"mesh.{suffix}"), meshing_backend="gmsh",
        )
    assert not [w for w in caught if "mesh_threads" in str(w.message)]
