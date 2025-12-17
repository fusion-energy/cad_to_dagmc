from os import name
import tempfile
import cadquery as cq
from cad_to_dagmc import CadToDagmc
from pathlib import Path
import pytest
from test_python_api import get_volumes_and_materials_from_h5m


def test_cadquery_assembly_with_names():

    with tempfile.TemporaryDirectory() as tmpdir:

        result = cq.Workplane().sphere(5)
        result2 = cq.Workplane().moveTo(10, 0).sphere(2)

        assembly = cq.Assembly()
        assembly.add(
            result, name="result", material=cq.Material("diamond")
        )  # note material assigned here
        assembly.add(
            result2, name="result2", material=cq.Material("gold")
        )  # note material assigned here

        my_model = CadToDagmc()
        # note that material tags are not needed here
        my_model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_names")
        test_h5m_filename = my_model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)

        assert Path(test_h5m_filename).is_file()

        assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat:result",
            2: "mat:result2",
        }


def test_cadquery_assembly_with_incomplete_names():

    with tempfile.TemporaryDirectory() as tmpdir:

        result = cq.Workplane().sphere(5)
        result2 = cq.Workplane().moveTo(10, 0).sphere(2)

        assembly = cq.Assembly()
        assembly.add(
            result, name="result", material=cq.Material("diamond")
        )  # note material assigned here
        assembly.add(
            result2, material=cq.Material("gold")
        )  # note material assigned here

        my_model = CadToDagmc()
        # note that material tags are not needed here
        my_model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_names")
        test_h5m_filename = my_model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)

        assert Path(test_h5m_filename).is_file()

        names_dict = get_volumes_and_materials_from_h5m(test_h5m_filename)
        assert names_dict[1] == "mat:result"
        assert names_dict[2].startswith("mat:")
        assert isinstance(names_dict[2], str)
        assert len(names_dict) == 2


def test_cadquery_assembly_with_nested_assembly():

    with tempfile.TemporaryDirectory() as tmpdir:

        result = cq.Workplane().sphere(5)
        result2 = cq.Workplane().moveTo(10, 0).sphere(2)
        result3 = cq.Workplane().moveTo(-10, 0).sphere(2)

        assembly = cq.Assembly()
        assembly.add(result, name="result", material=cq.Material("diamond"))
        assembly.add(result2, name="result2", material=cq.Material("gold"))

        assembly2 = cq.Assembly()
        assembly2.add(assembly, name="assembly1")
        assembly2.add(result3, name="result3", material=cq.Material("silver"))

        my_model = CadToDagmc()
        # note that material tags are not needed here
        my_model.add_cadquery_object(cadquery_object=assembly2, material_tags="assembly_names")
        test_h5m_filename = my_model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)

        assert Path(test_h5m_filename).is_file()

        assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat:result",
            2: "mat:result2",
            3: "mat:result3",
        }