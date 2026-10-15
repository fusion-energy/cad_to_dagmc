"""Tests for the imprint_glue argument.

imprint_glue is passed through to cadquery's imprint as its glue option.
"partial" is the fast, low RAM default for solids that touch or share faces
without crossing or overlapping, "full" is for solids whose shared faces
coincide exactly, and None turns glue off for a full general-fuse
intersection."""

import functools
import inspect
import warnings
from contextlib import nullcontext

import cadquery as cq
import gmsh
import pytest
from OCP.OSD import OSD_ThreadPool

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import imprint_assembly, resolve_imprint_glue

HAS_GLUE = "glue" in inspect.signature(cq.occ_impl.assembly.imprint).parameters
GLUES = ("partial", "full", None)


def _expected_response(glue):
    if not HAS_GLUE and glue == "full":
        return pytest.raises(RuntimeError, match='cannot honour imprint_glue="full"')
    if not HAS_GLUE and glue == "partial":
        return pytest.warns(UserWarning, match="legacy no-glue imprint")
    return nullcontext()


def _two_touching_boxes():
    """Whole-face contact: full glue is only correct for coincident faces."""
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(10, 0, 0)).box(10, 10, 10))
    return assembly


def _model():
    model = CadToDagmc()
    model.add_cadquery_object(_two_touching_boxes(), material_tags=["mat1", "mat2"])
    return model


@pytest.fixture
def glue_spy(monkeypatch):
    """Record the glue each imprint runs with.

    imprint_assembly and cad-to-dagmc-mesher both call
    cq.occ_impl.assembly.imprint, so patching it here catches the imprint
    whichever backend triggers it.
    """
    real_imprint = cq.occ_impl.assembly.imprint
    glues = []

    # functools.wraps keeps the signature visible to the inspect.signature
    # check in cad-to-dagmc-mesher that looks for the glue argument.
    @functools.wraps(real_imprint)
    def spy(assy, *args, **kwargs):
        glues.append(kwargs.get("glue", "not given"))
        return real_imprint(assy, *args, **kwargs)

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", spy)
    return glues


class TestResolveImprintGlue:
    @pytest.mark.parametrize("glue", ["partial", "full", None])
    def test_cadquery_glue_options_are_accepted(self, glue):
        assert resolve_imprint_glue(glue) == glue

    @pytest.mark.parametrize("glue", ["off", "Partial", "shift", True, False, 1])
    def test_anything_else_is_rejected(self, glue):
        with pytest.raises(ValueError, match="imprint_glue must be"):
            resolve_imprint_glue(glue)


class TestImprintAssembly:
    def test_default_glue_is_partial(self, glue_spy):
        with _expected_response("partial"):
            imprint_assembly(_two_touching_boxes())
        assert glue_spy == ["partial" if HAS_GLUE else "not given"]

    @pytest.mark.parametrize("glue", ["partial", "full", None])
    def test_glue_is_passed_to_cadquery(self, glue_spy, glue):
        with _expected_response(glue):
            shape, _ = imprint_assembly(_two_touching_boxes(), glue=glue)
        if not HAS_GLUE and glue == "full":
            assert glue_spy == []
            return
        assert glue_spy == [glue if HAS_GLUE else "not given"]
        assert len(shape.Solids()) == 2
        assert len(shape.Faces()) == 11
        assert sorted(s.Volume() for s in shape.Solids()) == pytest.approx([1000, 1000])

    @pytest.mark.parametrize("glue", ["full", None])
    def test_touching_boxes_imprint_the_same_with_any_glue(self, glue):
        """For these boxes every glue option gives the same imprinted solids and
        faces, so the choice only changes the cost."""
        with _expected_response("partial"):
            partial, _ = imprint_assembly(_two_touching_boxes(), glue="partial")
        with _expected_response(glue):
            other, _ = imprint_assembly(_two_touching_boxes(), glue=glue)
        if not HAS_GLUE and glue == "full":
            return

        assert len(other.Solids()) == len(partial.Solids()) == 2
        assert len(other.Faces()) == len(partial.Faces())


def _dagmc_h5m(backend, **kwargs):
    def export(model, tmp_path, imprint_glue, imprint=True):
        options = dict(kwargs)
        if "unstructured_volumes" in options or "tet_volumes" in options:
            options["umesh_filename"] = str(tmp_path / "umesh.vtk")
        return model.export_dagmc_h5m_file(
            filename=str(tmp_path / "dagmc.h5m"),
            meshing_backend=backend,
            imprint_glue=imprint_glue,
            imprint=imprint,
            **options,
        )

    return export


def _gmsh_mesh(model, tmp_path, imprint_glue, imprint=True):
    return model.export_gmsh_mesh_file(
        filename=str(tmp_path / "mesh.msh"), imprint_glue=imprint_glue, imprint=imprint
    )


def _unstructured(backend, **kwargs):
    def export(model, tmp_path, imprint_glue, imprint=True):
        return model.export_unstructured_mesh_file(
            filename=str(tmp_path / "umesh.vtk"),
            meshing_backend=backend,
            imprint_glue=imprint_glue,
            imprint=imprint,
            **kwargs,
        )

    return export


# Every route through the library that ends in an imprint, with the backends
# that need cad-to-dagmc-mesher flagged so they skip when it is not installed.
IMPRINT_PATHS = {
    "h5m_gmsh": (_dagmc_h5m("gmsh"), False),
    "h5m_mesher": (_dagmc_h5m("cad-to-dagmc-mesher"), True),
    "h5m_umesh_gmsh": (_dagmc_h5m("gmsh", unstructured_volumes=[1, 2]), False),
    "h5m_umesh_mesher": (
        _dagmc_h5m("cad-to-dagmc-mesher", target_edge_length=3.0, tet_volumes=["mat1"]),
        True,
    ),
    "gmsh_mesh_file": (_gmsh_mesh, False),
    "umesh_gmsh": (_unstructured("gmsh"), False),
    "umesh_mesher": (
        _unstructured("cad-to-dagmc-mesher", target_edge_length=3.0),
        True,
    ),
}


@pytest.mark.parametrize("glue", ["partial", "full", None])
@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("imprint", [True, 1])
def test_every_export_passes_the_glue_to_cadquery(tmp_path, glue_spy, path, glue, imprint):
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    before = OSD_ThreadPool.DefaultPool_s().NbThreads()
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        with _expected_response(glue):
            export(_model(), tmp_path, glue, imprint=imprint)

    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before
    assert not gmsh.isInitialized()
    if not HAS_GLUE and glue == "full":
        assert glue_spy == []
        assert not list(tmp_path.iterdir()), "unsupported glue must not create output files"
        return
    assert glue_spy == [glue if HAS_GLUE else "not given"], path
    output = tmp_path / ("mesh.msh" if path == "gmsh_mesh_file" else
                         "umesh.vtk" if path.startswith("umesh_") else "dagmc.h5m")
    assert output.stat().st_size > 0
    if path.startswith("h5m_umesh_"):
        assert (tmp_path / "umesh.vtk").stat().st_size > 0


@pytest.mark.parametrize("path", IMPRINT_PATHS)
def test_invalid_glue_is_rejected_by_every_export(tmp_path, glue_spy, path):
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    with pytest.raises(ValueError, match="imprint_glue must be"):
        export(_model(), tmp_path, "off")

    assert glue_spy == [], "the imprint ran before the glue was checked"


@pytest.mark.parametrize("glue", GLUES)
@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("single_solid", [False, True])
def test_glue_is_ignored_when_not_imprinting(tmp_path, glue_spy, path, glue, single_solid):
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")
    model = _model()
    if single_solid:
        model = CadToDagmc()
        model.add_cadquery_object(cq.Workplane().box(10, 10, 10), material_tags=["mat1"])
    # Select only the existing volume for the single-solid H5M+Gmsh route.
    if single_solid and path == "h5m_umesh_gmsh":
        export = _dagmc_h5m("gmsh", unstructured_volumes=[1])
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        export(model, tmp_path, glue, imprint=single_solid)
    assert glue_spy == []
    assert not gmsh.isInitialized()


@pytest.mark.parametrize("glue", ["partial", None])
def test_partial_face_contact_is_split(glue):
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(0, 0, 7)).box(4, 4, 4))
    with _expected_response(glue):
        shape, _ = imprint_assembly(assembly, glue=glue)
    assert len(shape.Solids()) == 2
    # A split ring is added to the big face, and the contact patch is shared.
    assert len(shape.Faces()) == 12
    left, right = shape.Solids()
    assert sum(face.isSame(other) for face in left.Faces() for other in right.Faces()) == 1


def test_glue_and_thread_count_combine(tmp_path, glue_spy):
    """imprint sets the threads and imprint_glue the glue, independently."""
    _model().export_dagmc_h5m_file(
        filename=str(tmp_path / "dagmc.h5m"),
        meshing_backend="gmsh",
        imprint=1,
        imprint_glue=None,
    )
    assert glue_spy == [None if HAS_GLUE else "not given"]


@pytest.mark.parametrize("supports_glue", [False, True])
@pytest.mark.parametrize("glue", GLUES)
def test_both_api_signatures(monkeypatch, supports_glue, glue):
    calls = []
    sentinel = object()

    def modern(assembly, *, glue="partial"):
        calls.append(glue)
        return sentinel

    def legacy(assembly):
        calls.append("legacy")
        return sentinel

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", modern if supports_glue else legacy)
    if not supports_glue and glue == "full":
        with pytest.raises(RuntimeError, match="Use imprint_glue=None.*upgrade CadQuery"):
            imprint_assembly(_two_touching_boxes(), glue=glue)
        assert calls == []
    else:
        response = (
            pytest.warns(UserWarning, match="legacy no-glue imprint")
            if not supports_glue and glue == "partial" else nullcontext()
        )
        with response:
            assert imprint_assembly(_two_touching_boxes(), glue=glue) is sentinel
        assert calls == [glue if supports_glue else "legacy"]


@pytest.mark.parametrize("supports_glue", [False, True])
def test_imprint_error_restores_thread_pool(monkeypatch, supports_glue):
    before = OSD_ThreadPool.DefaultPool_s().NbThreads()

    def modern(assembly, *, glue=None):
        assert OSD_ThreadPool.DefaultPool_s().NbThreads() == 1
        raise RuntimeError("imprint failed")

    def legacy(assembly):
        return modern(assembly)

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", modern if supports_glue else legacy)
    with pytest.raises(RuntimeError, match="imprint failed"):
        imprint_assembly(_two_touching_boxes(), threads=1, glue=None)
    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before
