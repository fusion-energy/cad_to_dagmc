from cad_to_dagmc import CadToDagmc
import cadquery as cq


def test_transport_result_h5m_with_2_sep_volumes():
    h5m_filename = "test_two_sep_volumes.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    workplane1 = cq.Workplane("XY").cylinder(height=10, radius=4)
    workplane2 = cq.Workplane("XY").moveTo(0, 15).cylinder(height=10, radius=5)
    # cq.Assembly().add(workplane1).add(workplane2)

    my_model = CadToDagmc()
    my_model.add_cadquery_object(workplane1)
    my_model.add_cadquery_object(workplane2)
    my_model.export_dagmc_h5m_file(
        filename=h5m_filename, material_tags=[material_tags[0], material_tags[1]]
    )


def test_transport_result_h5m_with_1_volumes():
    h5m_filename = "one_cylinder.h5m"
    volumes = 1
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    workplane1 = cq.Workplane("XY").cylinder(height=10, radius=4)

    my_model = CadToDagmc()
    my_model.add_cadquery_object(workplane1)
    my_model.export_dagmc_h5m_file(filename=h5m_filename, material_tags=[material_tags[0]])


def test_transport_result_h5m_with_2_joined_volumes():
    h5m_filename = "two_connected_cylinders.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    workplane1 = cq.Workplane("XY").cylinder(height=10, radius=4)
    workplane2 = cq.Workplane("XY").cylinder(height=10, radius=5).cut(workplane1)

    my_model = CadToDagmc()
    my_model.add_cadquery_object(workplane1)
    my_model.add_cadquery_object(workplane2)
    my_model.export_dagmc_h5m_file(
        filename=h5m_filename, material_tags=[material_tags[0], material_tags[1]]
    )
