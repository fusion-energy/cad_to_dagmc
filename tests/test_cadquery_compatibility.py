"""Default imprinting works with released CadQuery and current master."""

import cadquery as cq
import pytest
from OCP.OSD import OSD_ThreadPool

from cad_to_dagmc.core import (
    _mesh_with_cad_to_dagmc_mesher,
    imprint_assembly,
    thread_limit,
)


@pytest.mark.parametrize("modern", [False, True])
def test_default_imprint_supports_both_cadquery_signatures(monkeypatch, modern):
    calls = []
    result = object()

    def legacy(assembly):
        calls.append("legacy")
        return result

    def current(assembly, *, glue="full"):
        calls.append(glue)
        return result

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", current if modern else legacy)
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(1, 1, 1))
    assembly.add(cq.Workplane().transformed(offset=(1, 0, 0)).box(1, 1, 1))
    assert imprint_assembly(assembly) is result
    assert calls == (["partial"] if modern else ["legacy"])


def test_single_solid_skips_imprint(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("a single solid must not be imprinted")

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", unexpected)
    assembly = cq.Assembly().add(cq.Workplane().box(1, 1, 1), name="box")
    shape, origins = imprint_assembly(assembly)
    assert len(shape.Solids()) == 1
    assert [names[0].rsplit("/", 1)[-1] for names in origins.values()] == ["box"]


@pytest.mark.parametrize("enabled, threads", [(False, None), (True, None), (True, 1)])
def test_mesher_release_adapter_preserves_existing_imprint_api(monkeypatch, enabled, threads):
    cad = pytest.importorskip("cad_to_dagmc_mesher.cad")
    calls = []

    def mesh_assembly(assembly, *, solid_config, imprint):
        calls.append(imprint)
        assert OSD_ThreadPool.DefaultPool_s().NbThreads() == 2
        return {
            "vertices": [],
            "triangles_by_solid_by_face": {},
            "material_tags": [config.name for config in solid_config],
        }

    monkeypatch.setattr(cad, "mesh_assembly", mesh_assembly)
    with thread_limit(2):
        _mesh_with_cad_to_dagmc_mesher(
            cq.Assembly(), ["steel"], 0.1, 0.2,
            tet_volumes=None, target_edge_length=None,
            imprint=enabled, imprint_threads=threads,
        )
    expected = {"threads": threads or 2, "glue": "partial"} if enabled else False
    assert calls == [expected]


def test_touching_solids_default_imprint_shares_a_face():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(1, 1, 1))
    assembly.add(cq.Workplane().transformed(offset=(1, 0, 0)).box(1, 1, 1))
    shape, origins = imprint_assembly(assembly)
    assert len(shape.Solids()) == len(origins) == 2
    assert len(shape.Faces()) == 11
    assert all(isinstance(names, tuple) for names in origins.values())