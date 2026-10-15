"""Tests for the imprint_glue argument.

imprint_glue is passed through to cadquery's imprint as its glue option.
"partial" is the fast, low RAM default for solids that touch or share faces
without crossing or overlapping, "full" is for solids whose shared faces
coincide exactly, and None turns glue off for a full general-fuse
intersection."""

import functools

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import imprint_assembly, resolve_imprint_glue


def _two_touching_boxes():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(0, 7, 0)).box(10, 4, 10))
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
        imprint_assembly(_two_touching_boxes())
        assert glue_spy == ["partial"]

    @pytest.mark.parametrize("glue", ["partial", "full", None])
    def test_glue_is_passed_to_cadquery(self, glue_spy, glue):
        imprint_assembly(_two_touching_boxes(), glue=glue)
        assert glue_spy == [glue]

    @pytest.mark.parametrize("glue", ["full", None])
    def test_touching_boxes_imprint_the_same_with_any_glue(self, glue):
        """For these boxes every glue option gives the same imprinted solids and
        faces, so the choice only changes the cost."""
        partial, _ = imprint_assembly(_two_touching_boxes(), glue="partial")
        other, _ = imprint_assembly(_two_touching_boxes(), glue=glue)

        assert len(other.Solids()) == len(partial.Solids()) == 2
        assert len(other.Faces()) == len(partial.Faces())


def _dagmc_h5m(backend, **kwargs):
    def export(model, tmp_path, imprint_glue):
        model.export_dagmc_h5m_file(
            filename=str(tmp_path / "dagmc.h5m"),
            meshing_backend=backend,
            imprint_glue=imprint_glue,
            **kwargs,
        )

    return export


def _gmsh_mesh(model, tmp_path, imprint_glue):
    model.export_gmsh_mesh_file(
        filename=str(tmp_path / "mesh.msh"), imprint_glue=imprint_glue
    )


def _unstructured(backend, **kwargs):
    def export(model, tmp_path, imprint_glue):
        model.export_unstructured_mesh_file(
            filename=str(tmp_path / "umesh.vtk"),
            meshing_backend=backend,
            imprint_glue=imprint_glue,
            **kwargs,
        )

    return export


# Every route through the library that ends in an imprint, with the backends
# that need cad-to-dagmc-mesher flagged so they skip when it is not installed.
IMPRINT_PATHS = {
    "h5m_gmsh": (_dagmc_h5m("gmsh"), False),
    "h5m_mesher": (_dagmc_h5m("cad-to-dagmc-mesher"), True),
    "gmsh_mesh_file": (_gmsh_mesh, False),
    "umesh_gmsh": (_unstructured("gmsh"), False),
    "umesh_mesher": (
        _unstructured("cad-to-dagmc-mesher", target_edge_length=3.0),
        True,
    ),
}


@pytest.mark.parametrize("glue", ["partial", "full", None])
@pytest.mark.parametrize("path", IMPRINT_PATHS)
def test_every_export_passes_the_glue_to_cadquery(tmp_path, glue_spy, path, glue):
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    export(_model(), tmp_path, glue)

    assert glue_spy == [glue], f"{path} imprinted with glue {glue_spy}"


@pytest.mark.parametrize("path", IMPRINT_PATHS)
def test_invalid_glue_is_rejected_by_every_export(tmp_path, glue_spy, path):
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    with pytest.raises(ValueError, match="imprint_glue must be"):
        export(_model(), tmp_path, "off")

    assert glue_spy == [], "the imprint ran before the glue was checked"


def test_glue_is_ignored_when_not_imprinting(tmp_path, glue_spy):
    _model().export_dagmc_h5m_file(
        filename=str(tmp_path / "dagmc.h5m"),
        meshing_backend="gmsh",
        imprint=False,
        imprint_glue=None,
    )
    assert glue_spy == []


def test_glue_and_thread_count_combine(tmp_path, glue_spy):
    """imprint sets the threads and imprint_glue the glue, independently."""
    _model().export_dagmc_h5m_file(
        filename=str(tmp_path / "dagmc.h5m"),
        meshing_backend="gmsh",
        imprint=1,
        imprint_glue=None,
    )
    assert glue_spy == [None]
