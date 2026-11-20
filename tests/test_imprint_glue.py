"""Glue propagation, topology, and compatibility at the CadQuery imprint boundary."""

import inspect
from contextlib import nullcontext

import cadquery as cq
import gmsh
import pytest
from OCP.BOPAlgo import BOPAlgo_GlueEnum
from test_imprint_threads import (
    GLUES,
    HAS_ASSEMBLY_IMPRINT,
    HAS_GLUE,
    IMPRINT_MODES,
    IMPRINT_PATHS,
    _assert_outputs,
    _export,
    _model,
    _pool_threads,
    _two_touching_boxes,
)
from test_imprint_threads import (
    imprint_calls as imprint_calls,  # noqa: PLC0414 - shared pytest fixture
)

from cad_to_dagmc.core import (
    _mesh_with_cad_to_dagmc_mesher,
    imprint_assembly,
)

pytestmark = pytest.mark.filterwarnings("error::UserWarning")


# TODO remove _expected_response, without_assembly_imprint and the tests that
# use them once CadQuery/cadquery#2128 is merged and released, and
# pyproject.toml requires that CadQuery release.
def _expected_response(imprint):
    if not HAS_GLUE and imprint is not False and imprint != "partial":
        return pytest.raises(RuntimeError, match="legacy imprint always uses partial glue")
    return nullcontext()


@pytest.fixture
def without_assembly_imprint(monkeypatch):
    """Imprints as on a CadQuery without Assembly.imprint, such as 2.8.0."""
    monkeypatch.delattr(cq.Assembly, "imprint", raising=False)


def _origins(assembly):
    """The functional imprint's origins, for solids the imprint did not change."""
    return {
        solid: (name,)
        for obj, name, loc, _ in assembly
        for solid in obj.moved(loc).Solids()
    }


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("imprint", IMPRINT_MODES)
def test_every_export_passes_scalar_mode_and_thread_limit(tmp_path, imprint_calls, path, imprint):
    before = _pool_threads()
    with _expected_response(imprint):
        _export(path, _model(), tmp_path, imprint, imprint_threads=1)
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    if not HAS_GLUE and imprint is not False and imprint != "partial":
        assert imprint_calls == []
        assert not list(tmp_path.iterdir()), "unsupported glue must not create outputs"
    else:
        # Explicit None still imprints (GlueOff); only literal False disables it.
        expected = [] if imprint is False else [(1, imprint if HAS_GLUE else "legacy")]
        assert imprint_calls == expected
        _assert_outputs(path, tmp_path)


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("imprint", ["full", None])
def test_legacy_signature_rejects_unsupported_modes_without_outputs(
    tmp_path, monkeypatch, without_assembly_imprint, path, imprint
):
    calls = []

    def legacy(assembly):
        calls.append(assembly)
        raise AssertionError("unsupported glue reached legacy imprint")

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", legacy)
    before = _pool_threads()
    with pytest.raises(RuntimeError, match="legacy imprint always uses partial glue") as error:
        _export(path, _model(), tmp_path, imprint)
    assert f"imprint={imprint!r}" in str(error.value)
    assert "imprint='partial'" in str(error.value)
    assert calls == []
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("supports_glue", [False, True])
@pytest.mark.parametrize("glue", GLUES)
def test_functional_imprint_signatures_without_assembly_imprint(
    monkeypatch, without_assembly_imprint, supports_glue, glue
):
    calls = []

    def modern(assembly, *, glue="partial"):
        calls.append(glue)
        assert _pool_threads() == 1
        return None, _origins(assembly)

    def legacy(assembly):
        return modern(assembly, glue="legacy")

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", modern if supports_glue else legacy)
    before = _pool_threads()
    if not supports_glue and glue != "partial":
        with pytest.raises(RuntimeError, match="legacy imprint always uses partial glue"):
            imprint_assembly(_two_touching_boxes(), threads=1, glue=glue)
        assert calls == []
    else:
        shape = imprint_assembly(_two_touching_boxes(), threads=1, glue=glue)
        assert len(shape.Solids()) == 2
        assert calls == [glue if supports_glue else "legacy"]
    assert _pool_threads() == before


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("imprint", IMPRINT_MODES)
def test_single_solid_exports_skip_imprint_for_all_modes(tmp_path, imprint_calls, path, imprint):
    before = _pool_threads()
    _export(path, _model(single_solid=True), tmp_path, imprint, imprint_threads=1)
    assert imprint_calls == []
    assert _pool_threads() == before
    _assert_outputs(path, tmp_path)


@pytest.mark.skipif(not HAS_ASSEMBLY_IMPRINT, reason="CadQuery has no Assembly.imprint")
@pytest.mark.parametrize("glue", GLUES)
def test_glue_and_thread_limit_reach_assembly_imprint(monkeypatch, glue):
    calls = []

    def imprint(self, *, glue="partial"):
        calls.append(glue)
        assert _pool_threads() == 1
        return self

    monkeypatch.setattr(cq.Assembly, "imprint", imprint)
    before = _pool_threads()
    imprint_assembly(_two_touching_boxes(), threads=1, glue=glue)
    assert calls == [glue]
    assert _pool_threads() == before


@pytest.mark.parametrize("glue", ["off", "Partial", True, False, 0, 1, [], {}])
def test_low_level_imprint_rejects_invalid_glue(glue):
    with pytest.raises(ValueError, match="imprint"):
        imprint_assembly(_two_touching_boxes(), glue=glue)


@pytest.mark.parametrize("has_assembly_imprint", [True, False])
def test_imprint_error_restores_thread_pool(monkeypatch, has_assembly_imprint):
    def failing(*args, glue=None):
        assert _pool_threads() == 1
        raise RuntimeError("imprint failed")

    if has_assembly_imprint:
        monkeypatch.setattr(cq.Assembly, "imprint", failing, raising=False)
    else:
        monkeypatch.delattr(cq.Assembly, "imprint", raising=False)
        monkeypatch.setattr(cq.occ_impl.assembly, "imprint", failing)
    before = _pool_threads()
    with pytest.raises(RuntimeError, match="imprint failed"):
        imprint_assembly(_two_touching_boxes(), threads=1, glue="partial")
    assert _pool_threads() == before


@pytest.mark.skipif(not HAS_ASSEMBLY_IMPRINT, reason="CadQuery has no Assembly.imprint")
@pytest.mark.parametrize("options, mode", [
    ({}, BOPAlgo_GlueEnum.BOPAlgo_GlueShift),
    ({"glue": "partial"}, BOPAlgo_GlueEnum.BOPAlgo_GlueShift),
    ({"glue": "full"}, BOPAlgo_GlueEnum.BOPAlgo_GlueFull),
    ({"glue": None}, BOPAlgo_GlueEnum.BOPAlgo_GlueOff),
], ids=["omitted-default", "partial", "full", "explicit-none"])
def test_modern_imprint_uses_actual_occ_glue_enum(monkeypatch, options, mode):
    real_set_glue, builders = cq.occ_impl.shapes._set_glue, []

    def recording_set_glue(builder, glue):
        builders.append(builder)
        real_set_glue(builder, glue)

    monkeypatch.setattr(cq.occ_impl.shapes, "_set_glue", recording_set_glue)
    imprint_assembly(_two_touching_boxes(), **options)
    assert len(builders) == 1
    assert builders[0].Glue() == mode


def test_default_glue_is_partial(imprint_calls):
    imprint_assembly(_two_touching_boxes())
    assert [glue for _, glue in imprint_calls] == ["partial" if HAS_GLUE else "legacy"]


@pytest.mark.parametrize("partial_contact, glue, faces, volumes, shared", [
    (False, "partial", 11, [1000, 1000], 1), (False, "full", 11, [1000, 1000], 1),
    (False, None, 11, [1000, 1000], 1), (True, "partial", 12, [64, 1000], 1),
    (True, None, 12, [64, 1000], 1),
    # full glue only merges exactly coincident faces, so a partly coincident
    # contact is left unsplit and nothing is shared
    (True, "full", 12, [64, 1000], 0),
])
def test_full_and_partial_face_contact_topology(
    partial_contact, glue, faces, volumes, shared
):
    assembly = _two_touching_boxes()
    if partial_contact:
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().box(10, 10, 10))
        assembly.add(cq.Workplane().transformed(offset=(0, 0, 7)).box(4, 4, 4))
    with _expected_response(glue):
        shape = imprint_assembly(assembly, glue=glue)
    if not HAS_GLUE and glue != "partial":
        return
    assert len(shape.Solids()) == 2
    assert len(shape.Faces()) == faces
    assert sorted(solid.Volume() for solid in shape.Solids()) == pytest.approx(volumes)
    left, right = shape.Solids()
    assert sum(
        face.isSame(other) for face in left.Faces() for other in right.Faces()
    ) == shared


@pytest.mark.parametrize("imprint, imprint_threads", [
    ("partial", "all"), ("full", 3), (None, 1), (False, "all"), (False, 2),
])
def test_mesher_adapter_forwards_raw_scalar_arguments(monkeypatch, imprint, imprint_threads):
    cad = pytest.importorskip("cad_to_dagmc_mesher.cad")
    calls = []
    real_imprint, before = cq.occ_impl.assembly.imprint, _pool_threads()

    def mesh_assembly(assembly, *, solid_config, imprint, imprint_threads):
        assert cq.occ_impl.assembly.imprint is real_imprint
        assert _pool_threads() == before
        calls.append((imprint, imprint_threads))
        return {"vertices": [], "triangles_by_solid_by_face": {},
                "material_tags": [config.name for config in solid_config]}

    monkeypatch.setattr(cad, "mesh_assembly", mesh_assembly)
    _mesh_with_cad_to_dagmc_mesher(
        _two_touching_boxes(), ["left", "right"], 1.0, 0.3,
        tet_volumes=None, target_edge_length=None, imprint=imprint,
        imprint_threads=imprint_threads,
    )
    assert calls == [(imprint, imprint_threads)]
    assert cq.occ_impl.assembly.imprint is real_imprint
    assert _pool_threads() == before


def test_mesher_adapter_has_separate_threads_but_no_glue_keyword():
    parameters = inspect.signature(_mesh_with_cad_to_dagmc_mesher).parameters
    assert "imprint" in parameters
    assert parameters["imprint_threads"].default == "all"
    assert not {"glue", "imprint_glue"} & parameters.keys()
