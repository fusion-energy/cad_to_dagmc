import cadquery as cq
import pytest

import cad_to_dagmc

try:
    import openmc
    OPENMC_AVAILABLE = True
except ImportError:
    openmc = None
    OPENMC_AVAILABLE = False


@pytest.mark.parametrize(
    "scale_factor, expected_bbox",
    [
        (1.0, (-5.0000001, -5.0000001, -5.0000001, 5.0000001, 5.0000001, 5.0000001)),
        (
            2.0,
            (-10.0000001, -10.0000001, -10.0000001, 10.0000001, 10.0000001, 10.0000001),
        ),
        (
            10.0,
            (-50.0000001, -50.0000001, -50.0000001, 50.0000001, 50.0000001, 50.0000001),
        ),
    ],
)
def test_get_volumes(scale_factor, expected_bbox):

    result = cq.Workplane("XY").box(10, 10, 10)
    assembly = cq.Assembly()
    assembly.add(result)
    imprinted_assembly, _ = cq.occ_impl.assembly.imprint(assembly)

    gmsh = cad_to_dagmc.init_gmsh()

    gmsh, _ = cad_to_dagmc.get_volumes(
        gmsh, imprinted_assembly, method="file", scale_factor=scale_factor
    )

    bbox_after = gmsh.model.getBoundingBox(-1, -1)

    for a, b in zip(bbox_after, expected_bbox):
        assert abs(a - b) <= 0.000001  # tolerance


@pytest.mark.parametrize(
    "scale_factor, expected_bbox_lower_left, expected_bbox_upper_right, meshing_backend",
    [
        (
            1.0,
            (-5.0000001, -5.0000001, -5.0000001),
            (5.0000001, 5.0000001, 5.0000001),
            "cadquery",
        ),
        (
            1.0,
            (-5.0000001, -5.0000001, -5.0000001),
            (5.0000001, 5.0000001, 5.0000001),
            "gmsh",
        ),
        (
            2.0,
            (-10.0000001, -10.0000001, -10.0000001),
            (10.0000001, 10.0000001, 10.0000001),
            "cadquery",
        ),
        (
            2.0,
            (-10.0000001, -10.0000001, -10.0000001),
            (10.0000001, 10.0000001, 10.0000001),
            "gmsh",
        ),
        (
            10.0,
            (-50.0000001, -50.0000001, -50.0000001),
            (50.0000001, 50.0000001, 50.0000001),
            "cadquery",
        ),
        (
            10.0,
            (-50.0000001, -50.0000001, -50.0000001),
            (50.0000001, 50.0000001, 50.0000001),
            "gmsh",
        ),
    ],
)
@pytest.mark.skipif(not OPENMC_AVAILABLE, reason="openmc not installed")
def test_scale_factor_in_openmc(
    scale_factor, expected_bbox_lower_left, expected_bbox_upper_right, meshing_backend
):

    result = cq.Workplane("XY").box(10, 10, 10)
    assembly = cq.Assembly()
    assembly.add(result)

    my_model = cad_to_dagmc.CadToDagmc()
    my_model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1"])
    my_model.export_dagmc_h5m_file(
        filename=f"scale-{scale_factor}.h5m",
        min_mesh_size=0.5,
        max_mesh_size=1.0e6,
        scale_factor=scale_factor,
        meshing_backend=meshing_backend,
    )

    dag_model = openmc.DAGMCUniverse(filename=f"scale-{scale_factor}.h5m")

    for a, b in zip(dag_model.bounding_box.lower_left, expected_bbox_lower_left):
        assert abs(a - b) <= 0.2
    for a, b in zip(dag_model.bounding_box.upper_right, expected_bbox_upper_right):
        assert abs(a - b) <= 0.2
