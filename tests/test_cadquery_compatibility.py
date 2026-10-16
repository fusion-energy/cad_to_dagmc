"""Default imprinting works with released CadQuery and current master."""

import cadquery as cq
import pytest

from cad_to_dagmc.core import imprint_assembly


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


def test_touching_solids_default_imprint_shares_a_face():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(1, 1, 1))
    assembly.add(cq.Workplane().transformed(offset=(1, 0, 0)).box(1, 1, 1))
    shape, origins = imprint_assembly(assembly)
    assert len(shape.Solids()) == len(origins) == 2
    assert len(shape.Faces()) == 11
    assert all(isinstance(names, tuple) for names in origins.values())