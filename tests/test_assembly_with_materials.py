import tempfile
import cadquery as cq
from cad_to_dagmc import CadToDagmc
from pathlib import Path
import pytest
from test_python_api import get_volumes_and_materials_from_h5m


def test_cadquery_assembly_with_materials():

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
        my_model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_materials")
        test_h5m_filename = my_model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)

        assert Path(test_h5m_filename).is_file()

        assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat:diamond",
            2: "mat:gold",
        }


def test_assembly_missing_material_tag_raises():
    # Create two parts, only one with a material
    result = cq.Workplane().sphere(5)
    result2 = cq.Workplane().moveTo(10, 0).sphere(2)

    assembly = cq.Assembly()
    assembly.add(result, name="result", material=cq.Material("diamond"))
    assembly.add(result2, name="result2")  # No material assigned

    my_model = CadToDagmc()
    # Should raise ValueError when adding the assembly
    with pytest.raises(ValueError) as excinfo:
        my_model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_materials")
    # Check error message is informative
    assert "Not all parts in the assembly have materials assigned" in str(excinfo.value)
