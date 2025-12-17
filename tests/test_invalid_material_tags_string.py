import pytest
import cadquery as cq
from cad_to_dagmc.core import CadToDagmc

def test_add_cadquery_object_invalid_material_tags_string():
    # Create a simple CadQuery solid
    box = cq.Workplane("XY").box(1, 1, 1)
    c2d = CadToDagmc()
    # Use an invalid string for material_tags
    with pytest.raises(ValueError) as excinfo:
        c2d.add_cadquery_object(box, material_tags="not_a_valid_option")
    assert "If material_tags is a string it must be 'assembly_materials' or 'assembly_names'" in str(excinfo.value)
