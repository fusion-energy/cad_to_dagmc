"""Tests for the component_tags feature of add_cadquery_object, which writes
independent "component:<tag>" identity groups alongside the "mat:<tag>" material
groups so that components sharing a material can still be distinguished
downstream (e.g. an OpenMC CellFilter)."""

import cadquery as cq
import pytest
from cad_to_dagmc import CadToDagmc
from test_python_api import get_volumes_and_materials_from_h5m


def _two_cube_assembly():
    """Two disconnected cubes that will become two separate volumes."""
    first_wall = cq.Workplane().box(10, 10, 10)
    divertor = cq.Workplane().moveTo(20, 0).box(5, 5, 5)
    assembly = cq.Assembly()
    assembly.add(first_wall, name="first_wall")
    assembly.add(divertor, name="divertor")
    return assembly


@pytest.mark.parametrize("meshing_backend", ["cadquery", "gmsh"])
def test_component_tags_explicit_list_shared_material(meshing_backend, tmp_path):
    """An explicit component_tags list distinguishes two volumes that share a
    material, while the material groups stay deduplicated."""
    model = CadToDagmc()
    model.add_cadquery_object(
        cadquery_object=_two_cube_assembly(),
        material_tags=["steel", "steel"],
        component_tags=["first_wall", "divertor"],
    )

    h5m = str(tmp_path / "dagmc.h5m")
    model.export_dagmc_h5m_file(filename=h5m, meshing_backend=meshing_backend)

    # the material is shared across both volumes (deduplicated)
    assert get_volumes_and_materials_from_h5m(h5m) == {
        1: "mat:steel",
        2: "mat:steel",
    }
    # the component identity groups distinguish the two volumes
    assert get_volumes_and_materials_from_h5m(h5m, prefix="component:") == {
        1: "component:first_wall",
        2: "component:divertor",
    }


@pytest.mark.parametrize("meshing_backend", ["cadquery", "gmsh"])
def test_component_tags_assembly_names(meshing_backend, tmp_path):
    """component_tags="assembly_names" derives the identity groups from the
    CadQuery assembly part names."""
    model = CadToDagmc()
    model.add_cadquery_object(
        cadquery_object=_two_cube_assembly(),
        material_tags=["steel", "steel"],
        component_tags="assembly_names",
    )

    h5m = str(tmp_path / "dagmc.h5m")
    model.export_dagmc_h5m_file(filename=h5m, meshing_backend=meshing_backend)

    assert get_volumes_and_materials_from_h5m(h5m) == {
        1: "mat:steel",
        2: "mat:steel",
    }
    assert get_volumes_and_materials_from_h5m(h5m, prefix="component:") == {
        1: "component:first_wall",
        2: "component:divertor",
    }


def test_no_component_tags_writes_no_component_groups(tmp_path):
    """When component_tags is omitted no component groups are written, and the
    material groups are unchanged."""
    model = CadToDagmc()
    model.add_cadquery_object(
        cq.Workplane().box(10, 10, 10), material_tags=["steel"]
    )

    h5m = str(tmp_path / "dagmc.h5m")
    model.export_dagmc_h5m_file(filename=h5m)

    assert get_volumes_and_materials_from_h5m(h5m) == {1: "mat:steel"}
    assert get_volumes_and_materials_from_h5m(h5m, prefix="component:") == {}


def test_component_tags_wrong_length_raises():
    """An explicit component_tags list must match the number of volumes."""
    model = CadToDagmc()
    with pytest.raises(ValueError, match="component_tags"):
        model.add_cadquery_object(
            cadquery_object=_two_cube_assembly(),
            material_tags=["steel", "steel"],
            component_tags=["only_one"],
        )


def test_component_tags_assembly_names_on_non_assembly_raises():
    """component_tags="assembly_names" only makes sense for an assembly."""
    model = CadToDagmc()
    with pytest.raises(ValueError, match="assembly_names"):
        model.add_cadquery_object(
            cadquery_object=cq.Workplane().box(10, 10, 10),
            material_tags=["steel"],
            component_tags="assembly_names",
        )
