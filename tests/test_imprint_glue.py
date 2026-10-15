"""Tests for the glue entry in the explicit imprint mapping.

imprint['glue'] is passed through to cadquery's imprint as its glue option.
"partial" is the fast, low RAM default for solids that touch or share faces
without crossing or overlapping, "full" is for solids whose shared faces
coincide exactly, and None turns glue off for a full general-fuse
intersection."""

import functools
import inspect
import warnings
from collections import UserDict
from contextlib import nullcontext
from types import MappingProxyType
from unittest.mock import Mock

import cadquery as cq
import gmsh
import pytest
from OCP.BOPAlgo import BOPAlgo_GlueEnum
from OCP.OSD import OSD_ThreadPool

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import (
    DEFAULT_IMPRINT,
    _mesh_with_cad_to_dagmc_mesher,
    _resolve_glue,
    imprint_assembly,
)

HAS_GLUE = "glue" in inspect.signature(cq.occ_impl.assembly.imprint).parameters
GLUES = ("partial", "full", None)


def _expected_response(glue):
    if not HAS_GLUE and glue != "partial":
        return pytest.raises(RuntimeError, match="legacy imprint always uses partial glue")
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


class TestResolveGlue:
    @pytest.mark.parametrize("glue", ["partial", "full", None])
    def test_cadquery_glue_options_are_accepted(self, glue):
        assert _resolve_glue(glue) == glue

    @pytest.mark.parametrize("glue", ["off", "Partial", "shift", True, False, 1, [], {}])
    def test_anything_else_is_rejected(self, glue):
        with pytest.raises(ValueError, match=r"imprint\['glue'\] must be") as excinfo:
            _resolve_glue(glue)
        assert str(excinfo.value) == (
            f'imprint[\'glue\'] must be "partial", "full" or None, got {glue!r}'
        )


class TestImprintAssembly:
    def test_default_glue_is_partial(self, glue_spy):
        with _expected_response("partial"):
            imprint_assembly(_two_touching_boxes())
        assert glue_spy == ["partial" if HAS_GLUE else "not given"]

    @pytest.mark.parametrize("glue", ["partial", "full", None])
    def test_glue_is_passed_to_cadquery(self, glue_spy, glue):
        with _expected_response(glue):
            shape, _ = imprint_assembly(_two_touching_boxes(), glue=glue)
        if not HAS_GLUE and glue != "partial":
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
        if not HAS_GLUE and glue != "partial":
            return

        assert len(other.Solids()) == len(partial.Solids()) == 2
        assert len(other.Faces()) == len(partial.Faces())


def _dagmc_h5m(backend, **kwargs):
    def export(model, tmp_path, imprint=DEFAULT_IMPRINT, **export_kwargs):
        options = dict(kwargs)
        options.update(export_kwargs)
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
@pytest.mark.parametrize("threads", ["all", 1])
def test_every_export_passes_the_glue_to_cadquery(tmp_path, glue_spy, path, glue, threads):
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")

    imprint = {"threads": threads, "glue": glue}
    original = imprint.copy()
    before = OSD_ThreadPool.DefaultPool_s().NbThreads()
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        with _expected_response(glue):
            export(_model(), tmp_path, imprint=imprint)

    assert imprint == original
    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before
    assert not gmsh.isInitialized()
    if not HAS_GLUE and glue != "partial":
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
@pytest.mark.parametrize("glue", ["off", "Partial", True, False, 1, [], {}])
@pytest.mark.parametrize("single_solid", [False, True])
def test_invalid_glue_is_rejected_by_every_export(
    tmp_path, monkeypatch, glue_spy, path, glue, single_solid
):
    export, _ = IMPRINT_PATHS[path]
    model = _model()
    if single_solid:
        model = CadToDagmc()
        model.add_cadquery_object(cq.Workplane().box(10, 10, 10), material_tags=["mat1"])
        if path == "h5m_umesh_gmsh":
            export = _dagmc_h5m("gmsh", unstructured_volumes=[1])
    side_effects = Mock(side_effect=AssertionError("geometry or meshing ran before validation"))
    for name in ("get_ids_from_assembly", "imprint_assembly", "init_gmsh", "_mesh_with_cad_to_dagmc_mesher"):
        monkeypatch.setattr(f"cad_to_dagmc.core.{name}", side_effects)
    monkeypatch.setattr(model, "_export_unstructured_mesh_file_with_mesher", side_effects)
    imprint = {"threads": 1, "glue": glue}
    original = imprint.copy()
    before = OSD_ThreadPool.DefaultPool_s().NbThreads()

    with pytest.raises(ValueError, match=r"imprint\['glue'\] must be"):
        export(model, tmp_path, imprint=imprint)

    side_effects.assert_not_called()
    assert imprint == original
    assert glue_spy == [], "the imprint ran before the glue was checked"
    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("glue", GLUES)
@pytest.mark.parametrize("threads", ["all", 1])
@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("single_solid", [False, True])
def test_glue_is_ignored_when_not_imprinting(tmp_path, glue_spy, path, glue, threads, single_solid):
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
    options = {"threads": threads, "glue": glue}
    original = options.copy()
    before = OSD_ThreadPool.DefaultPool_s().NbThreads()
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        export(model, tmp_path, imprint=options if single_solid else False)
    assert options == original
    assert glue_spy == []
    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before
    assert not gmsh.isInitialized()
    output = tmp_path / ("mesh.msh" if path == "gmsh_mesh_file" else
                         "umesh.vtk" if path.startswith("umesh_") else "dagmc.h5m")
    assert output.stat().st_size > 0
    if path.startswith("h5m_umesh_"):
        assert (tmp_path / "umesh.vtk").stat().st_size > 0


@pytest.mark.parametrize("glue", ["partial", None])
def test_partial_face_contact_is_split(glue):
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(0, 0, 7)).box(4, 4, 4))
    with _expected_response(glue):
        shape, _ = imprint_assembly(assembly, glue=glue)
    if not HAS_GLUE and glue != "partial":
        return
    assert len(shape.Solids()) == 2
    # A split ring is added to the big face, and the contact patch is shared.
    assert len(shape.Faces()) == 12
    left, right = shape.Solids()
    assert sum(face.isSame(other) for face in left.Faces() for other in right.Faces()) == 1


def test_glue_and_thread_count_combine(tmp_path, glue_spy):
    """Both entries of imprint reach the same operation."""
    with _expected_response(None):
        _model().export_dagmc_h5m_file(
            filename=str(tmp_path / "dagmc.h5m"),
            meshing_backend="gmsh",
            imprint={"threads": 1, "glue": None},
        )
    assert glue_spy == ([None] if HAS_GLUE else [])


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
    if not supports_glue and glue != "partial":
        with pytest.raises(RuntimeError, match="legacy imprint always uses partial glue") as excinfo:
            imprint_assembly(_two_touching_boxes(), glue=glue)
        message = str(excinfo.value)
        assert "imprint['glue']" in message
        assert '"threads": "all", "glue": "partial"' in message
        assert "upgrade CadQuery" in message
        assert "imprint_glue" not in message
        assert calls == []
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
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
        imprint_assembly(_two_touching_boxes(), threads=1, glue="partial")
    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before


@pytest.mark.skipif(not HAS_GLUE, reason="legacy imprint has no selectable glue API")
@pytest.mark.parametrize(
    "glue, mode",
    [
        ("partial", BOPAlgo_GlueEnum.BOPAlgo_GlueShift),
        ("full", BOPAlgo_GlueEnum.BOPAlgo_GlueFull),
        (None, BOPAlgo_GlueEnum.BOPAlgo_GlueOff),
    ],
)
def test_modern_imprint_uses_the_requested_occ_glue_mode(monkeypatch, glue, mode):
    """Explicit None must reach GlueOff, not CadQuery's default partial glue."""
    real_builder = cq.occ_impl.assembly.BOPAlgo_Builder
    builders = []

    def recording_builder():
        builder = real_builder()
        builders.append(builder)
        return builder

    monkeypatch.setattr(cq.occ_impl.assembly, "BOPAlgo_Builder", recording_builder)
    imprint_assembly(_two_touching_boxes(), glue=glue)
    assert len(builders) == 1
    assert builders[0].Glue() == mode


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("glue", ["full", None])
def test_legacy_signature_rejects_unsupported_glue_without_outputs(
    tmp_path, monkeypatch, path, glue
):
    """Exercise legacy rejection even when the installed CadQuery is modern."""
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")
    calls = []

    def legacy(assembly):
        calls.append(assembly)
        raise AssertionError("unsupported glue reached legacy imprint")

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", legacy)
    imprint = {"threads": "all", "glue": glue}
    original = imprint.copy()
    before = OSD_ThreadPool.DefaultPool_s().NbThreads()
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        with pytest.raises(RuntimeError, match="legacy imprint always uses partial glue"):
            export(_model(), tmp_path, imprint)
    assert calls == []
    assert imprint == original
    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before
    assert cq.occ_impl.assembly.imprint is legacy
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("mapping_factory", [dict, MappingProxyType, UserDict])
@pytest.mark.parametrize("threads", ["all", 1])
@pytest.mark.parametrize("glue", GLUES)
def test_exporter_forwards_the_same_imprint_mapping_to_mesher(monkeypatch, mapping_factory, threads, glue):
    options = mapping_factory({"threads": threads, "glue": glue})
    _assert_mesher_forwarding(monkeypatch, options)


@pytest.mark.parametrize("imprint", [False, DEFAULT_IMPRINT])
def test_exporter_forwards_false_and_immutable_default_to_mesher(monkeypatch, imprint):
    _assert_mesher_forwarding(monkeypatch, imprint)


def _assert_mesher_forwarding(monkeypatch, imprint):
    cad = pytest.importorskip("cad_to_dagmc_mesher.cad")
    calls = []
    original = dict(imprint) if imprint is not False else False
    real_imprint = cq.occ_impl.assembly.imprint
    before = OSD_ThreadPool.DefaultPool_s().NbThreads()

    def mesh_assembly(assembly, *, solid_config, imprint):
        assert cq.occ_impl.assembly.imprint is real_imprint
        assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before
        calls.append(imprint)
        return {
            "vertices": [],
            "triangles_by_solid_by_face": {},
            "material_tags": [config.name for config in solid_config],
        }

    monkeypatch.setattr(cad, "mesh_assembly", mesh_assembly)
    _mesh_with_cad_to_dagmc_mesher(
        _two_touching_boxes(), ["left", "right"], 1.0, 0.3,
        tet_volumes=None, target_edge_length=None, imprint=imprint,
    )
    assert len(calls) == 1
    assert calls[0] is imprint, "do not copy, resolve, or translate the caller's mapping"
    assert imprint == original
    assert cq.occ_impl.assembly.imprint is real_imprint
    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before


def test_mesher_adapter_has_no_separate_imprint_arguments():
    parameters = inspect.signature(_mesh_with_cad_to_dagmc_mesher).parameters
    assert "imprint" in parameters
    assert "imprint_threads" not in parameters
    assert "imprint_glue" not in parameters


@pytest.mark.parametrize("removed_keyword", ["imprint_threads", "imprint_glue"])
def test_mesher_adapter_rejects_removed_keywords(removed_keyword):
    with pytest.raises(TypeError, match=f"unexpected keyword argument '{removed_keyword}'"):
        _mesh_with_cad_to_dagmc_mesher(
            _two_touching_boxes(), ["left", "right"], 1.0, 0.3,
            tet_volumes=None, target_edge_length=None, imprint=False,
            **{removed_keyword: None},
        )


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("mapping_factory", [MappingProxyType, UserDict])
def test_every_export_accepts_other_mapping_types_unchanged(
    tmp_path, path, mapping_factory
):
    export, needs_mesher = IMPRINT_PATHS[path]
    if needs_mesher:
        pytest.importorskip("cad_to_dagmc_mesher")
    imprint = mapping_factory({"threads": 1, "glue": "partial"})
    original = dict(imprint)
    before = OSD_ThreadPool.DefaultPool_s().NbThreads()
    export(_model(), tmp_path, imprint)
    assert imprint == original
    assert OSD_ThreadPool.DefaultPool_s().NbThreads() == before
    assert not gmsh.isInitialized()
    output = tmp_path / ("mesh.msh" if path == "gmsh_mesh_file" else
                         "umesh.vtk" if path.startswith("umesh_") else "dagmc.h5m")
    assert output.stat().st_size > 0
    if path.startswith("h5m_umesh_"):
        assert (tmp_path / "umesh.vtk").stat().st_size > 0
