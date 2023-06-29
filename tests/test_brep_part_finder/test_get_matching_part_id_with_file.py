
from cad_to_dagmc.brep_part_finder import (
    get_part_properties_from_file,
    get_matching_part_id,
    get_part_properties_from_shapes,
)
import cadquery
import pytest

brep_part_properties = get_part_properties_from_file("tests/test_brep_part_finder/ball_reactor.brep")

def test_finding_part_id_with_volume():
    """"""

    part_id = get_matching_part_id(
        brep_part_properties=brep_part_properties,
        volume=95467959.26023674,
        volume_atol=1e-6,
    )

    assert part_id == [6]

def test_finding_part_id_with_center():
    """"""

    part_id = get_matching_part_id(
        brep_part_properties=brep_part_properties,
        center_x=-0.006133773543690803,
        center_y=7.867805031206607e-10,
        center_z=7.70315160988196e-12,
        center_atol=1e-6,
    )

    assert part_id == [6]

def test_finding_part_id_with_bounding_box():
    """"""

    part_id = get_matching_part_id(
        brep_part_properties=brep_part_properties,
        bounding_box_xmin=-570.5554844464615,
        bounding_box_ymin=-570.5554844464615,
        bounding_box_zmin=-453.27123145033755,
        bounding_box_xmax=570.5554844464615,
        bounding_box_ymax=570.5554844464615,
        bounding_box_zmax=453.27123145033755,
        bounding_box_atol=1e-6,
    )

    assert part_id == [6]

def test_cq_workplane():
    result = cadquery.Workplane("front").box(2.0, 2.0, 0.5)
    details = get_part_properties_from_shapes(result)
    assert list(details.keys()) == [1]
    assert pytest.approx(details[1]["center_x"]) == 0
    assert pytest.approx(details[1]["center_y"]) == 0
    assert pytest.approx(details[1]["center_z"]) == 0
    assert pytest.approx(details[1]["volume"]) == 2
    assert details[1]["bounding_box_xmin"] == -1.0
    assert details[1]["bounding_box_ymin"] == -1.0
    assert details[1]["bounding_box_zmin"] == -0.25
    assert details[1]["bounding_box_xmax"] == 1.0
    assert details[1]["bounding_box_ymax"] == 1.0
    assert details[1]["bounding_box_zmax"] == 0.25
