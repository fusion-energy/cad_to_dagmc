import warnings
from pathlib import Path

import cadquery as cq
import gmsh
import h5py
import numpy as np
import pytest

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import check_material_tags

# Check if pymoab is available
try:
    import pymoab as mb
    from pymoab import core, types
    PYMOAB_AVAILABLE = True
except ImportError:
    PYMOAB_AVAILABLE = False


def get_volumes_and_materials_from_h5m(filename: str) -> dict:
    """Reads in a DAGMC h5m file and finds the volume ids with their associated
    material tags.

    Uses h5py to read the file directly, which works whether or not pymoab is installed.

    Arguments:
        filename: the filename of the DAGMC h5m file

    Returns:
        A dictionary of volume ids and material tags
    """

    def _read_sparse_tag(tag_group):
        """Read a sparse tag (id_list + values) and return as dict."""
        if "id_list" not in tag_group or "values" not in tag_group:
            return {}
        ids = tag_group["id_list"][:]
        values = tag_group["values"][:]
        result = {}
        # Check if values are string/opaque type or numeric
        dtype_kind = values.dtype.kind
        is_string_type = dtype_kind in ("S", "V", "O")  # bytes, void (opaque), object
        for i, h in enumerate(ids):
            val = values[i]
            if is_string_type:
                # Handle string/opaque types
                if hasattr(val, "tobytes"):
                    val = val.tobytes().rstrip(b"\x00").decode("ascii", "replace")
                elif isinstance(val, bytes):
                    val = val.rstrip(b"\x00").decode("ascii", "replace")
            else:
                # Numeric type - convert to Python int
                val = int(val)
            result[int(h)] = val
        return result

    def _slices_from_end_indices(ends):
        """Convert end indices to slices. End index -1 means empty."""
        prev_end = -1
        slices = []
        for end in ends:
            end = int(end)
            start = prev_end + 1
            if end >= start:
                slices.append(slice(start, end + 1))
            else:
                slices.append(None)
            prev_end = end
        return slices

    with h5py.File(filename, "r") as f:
        tstt = f["tstt"]
        sets = tstt["sets"]
        tags = tstt["tags"]

        # Get set list, contents, and start_id
        set_list = sets["list"][:]
        set_contents = sets["contents"][:]
        sets_start_id = int(sets["list"].attrs.get("start_id", 0))
        num_sets = len(set_list)

        # Build slices for set contents (column 0 is contents end index)
        contents_slices = _slices_from_end_indices(set_list[:, 0])

        # Read sparse tags
        cat_lookup = _read_sparse_tag(tags["CATEGORY"])
        name_lookup = _read_sparse_tag(tags["NAME"])

        # GLOBAL_ID may be sparse (pymoab) or dense (h5py backend)
        global_id_lookup = {}
        if "GLOBAL_ID" in tags and "id_list" in tags["GLOBAL_ID"] and "values" in tags["GLOBAL_ID"]:
            # Sparse storage (pymoab style)
            global_id_lookup = _read_sparse_tag(tags["GLOBAL_ID"])
        elif "tags" in sets and "GLOBAL_ID" in sets["tags"]:
            # Dense storage (h5py backend style) - one value per set
            dense_ids = sets["tags"]["GLOBAL_ID"][:]
            for i, gid in enumerate(dense_ids):
                handle = sets_start_id + i
                global_id_lookup[handle] = int(gid)

        # Find all Groups (material groups start with "mat:") and all Volumes
        vol_mat = {}
        groups = {}  # handle -> name
        volumes = {}  # handle -> global_id

        for handle, category in cat_lookup.items():
            if category == "Group":
                name = name_lookup.get(handle, "")
                if name.startswith("mat:"):
                    groups[handle] = name
            elif category == "Volume":
                global_id = global_id_lookup.get(handle, 0)
                volumes[handle] = global_id

        if not groups:
            return vol_mat

        # For each group, find its child sets (volumes)
        for group_handle, mat_name in groups.items():
            # Get the index into set_list for this group
            set_idx = group_handle - sets_start_id
            if set_idx < 0 or set_idx >= num_sets:
                continue

            # Get the contents slice for this set
            contents_slice = contents_slices[set_idx]
            if contents_slice is None:
                continue

            # The contents are child entity handles
            child_handles = set_contents[contents_slice]

            for child_handle in child_handles:
                child_handle = int(child_handle)
                # Check if this child is a Volume
                if child_handle in volumes:
                    vol_id = volumes[child_handle]
                    vol_mat[vol_id] = mat_name

        return vol_mat


# TODO: Add min/max mesh size feature to CadQuery direct mesher and enable it for this test
@pytest.mark.parametrize("meshing_backend", ["gmsh"])
def test_max_mesh_size_impacts_file_size(meshing_backend, tmp_path):
    """Checks the reducing max_mesh_size value increases the file size"""

    sphere = cq.Workplane().sphere(100)

    c2d = CadToDagmc()
    c2d.add_cadquery_object(sphere, material_tags=["m1"])

    file1 = tmp_path / "test_10_30.h5m"
    file2 = tmp_path / "test_20_30.h5m"
    file3 = tmp_path / "test_20_25.h5m"

    c2d.export_dagmc_h5m_file(
        min_mesh_size=10,
        max_mesh_size=20,
        mesh_algorithm=1,
        filename=str(file1),
        meshing_backend=meshing_backend,
    )
    c2d.export_dagmc_h5m_file(
        min_mesh_size=20,
        max_mesh_size=30,
        mesh_algorithm=1,
        filename=str(file2),
        meshing_backend=meshing_backend,
    )
    c2d.export_dagmc_h5m_file(
        min_mesh_size=20,
        max_mesh_size=25,
        mesh_algorithm=1,
        filename=str(file3),
        meshing_backend=meshing_backend,
    )

    assert file1.is_file()
    assert file2.is_file()
    assert file3.is_file()

    large_file = file1.stat().st_size
    small_file = file2.stat().st_size
    medium_file = file3.stat().st_size
    assert small_file < large_file
    assert small_file < medium_file


@pytest.mark.parametrize("meshing_backend", ["cadquery", "gmsh"])
@pytest.mark.parametrize("h5m_backend", ["pymoab", "h5py"])
def test_h5m_file_tags(meshing_backend, h5m_backend, tmp_path):
    """Checks that a h5m file is created with the correct tags"""

    sphere1 = cq.Workplane().sphere(20)
    sphere2 = cq.Workplane().moveTo(100, 100).sphere(20)
    sphere3 = cq.Workplane().moveTo(-100, -100).sphere(20)

    c2d = CadToDagmc()
    c2d.add_cadquery_object(sphere1, material_tags=["mat1"])
    c2d.add_cadquery_object(sphere2, material_tags=["mat2"])
    c2d.add_cadquery_object(sphere3, material_tags=["mat3"])

    test_h5m_filename = tmp_path / "test_dagmc.h5m"

    returned_filename = c2d.export_dagmc_h5m_file(
        filename=str(test_h5m_filename),
        meshing_backend=meshing_backend,
        h5m_backend=h5m_backend,
    )

    assert test_h5m_filename.is_file()
    assert Path(returned_filename).is_file()
    assert str(test_h5m_filename) == returned_filename

    assert get_volumes_and_materials_from_h5m(str(test_h5m_filename)) == {
        1: "mat:mat1",
        2: "mat:mat2",
        3: "mat:mat3",
    }


def test_add_cadquery_object_returned_volumes():
    """Checks that a add_cadquery_object method returns the correct number of volumes"""

    sphere1 = cq.Workplane().sphere(20)
    sphere2 = cq.Workplane().moveTo(100, 100).sphere(20)
    sphere3 = cq.Workplane().moveTo(-100, -100).sphere(20)

    c2d = CadToDagmc()
    vols = c2d.add_cadquery_object(sphere1, material_tags=["mat1"])
    assert vols == 1

    assembly = cq.Assembly()
    assembly.add(sphere1)
    assembly.add(sphere2)
    assembly.add(sphere3)
    c2d = CadToDagmc()
    vols = c2d.add_cadquery_object(assembly, material_tags=["mat1", "mat2", "mat3"])
    assert vols == 3


def test_add_stp_file_returned_volumes():
    """Checks that a add_stp_file method returns the correct number of volumes"""

    c2d = CadToDagmc()
    vols = c2d.add_stp_file("tests/curved_extrude.stp")
    assert vols == 1

    c2d = CadToDagmc()
    vols = c2d.add_stp_file("tests/two_disconnected_cubes.stp")
    assert vols == 2


@pytest.mark.parametrize("meshing_backend", ["cadquery", "gmsh"])
def test_export_dagmc_h5m_file_handles_paths_folders_strings(meshing_backend, tmp_path):
    """Checks that a h5m file is created with various path formats"""

    box = cq.Workplane().box(1, 1, 1)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, material_tags=["mat1"])

    # Test string filename
    file1 = tmp_path / "test_dagmc1.h5m"
    c2d.export_dagmc_h5m_file(filename=str(file1), meshing_backend=meshing_backend)
    assert file1.is_file()

    # Test nested folder with string
    file2 = tmp_path / "out_folder1" / "test_dagmc2.h5m"
    c2d.export_dagmc_h5m_file(filename=str(file2), meshing_backend=meshing_backend)
    assert file2.is_file()

    # Test Path object
    file3 = tmp_path / "test_dagmc3.h5m"
    c2d.export_dagmc_h5m_file(filename=file3, meshing_backend=meshing_backend)
    assert file3.is_file()

    # Test nested folder with Path
    file4 = tmp_path / "out_folder2" / "test_dagmc4.h5m"
    c2d.export_dagmc_h5m_file(filename=file4, meshing_backend=meshing_backend)
    assert file4.is_file()


def test_export_unstructured_mesh_file_handles_paths_folders_strings(tmp_path):
    """Checks that a vtk file is created with various path formats"""

    box = cq.Workplane().box(1, 1, 1)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, material_tags=["mat1"])

    # Test string filename
    file1 = tmp_path / "test_dagmc1.vtk"
    c2d.export_unstructured_mesh_file(filename=str(file1))
    assert file1.is_file()

    # Test nested folder with string
    file2 = tmp_path / "out_folder3" / "test_dagmc2.vtk"
    c2d.export_unstructured_mesh_file(filename=str(file2))
    assert file2.is_file()

    # Test Path object
    file3 = tmp_path / "test_dagmc3.vtk"
    c2d.export_unstructured_mesh_file(filename=file3)
    assert file3.is_file()

    # Test nested folder with Path
    file4 = tmp_path / "out_folder4" / "test_dagmc4.vtk"
    c2d.export_unstructured_mesh_file(filename=file4)
    assert file4.is_file()


def test_export_gmsh_mesh_file_handles_paths_folders_strings(tmp_path):
    """Checks that a msh file is created with various path formats"""

    box = cq.Workplane().box(1, 1, 1)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, material_tags=["mat1"])

    # Test string filename
    file1 = tmp_path / "test_dagmc1.msh"
    c2d.export_gmsh_mesh_file(filename=str(file1))
    assert file1.is_file()

    # Test nested folder with string
    file2 = tmp_path / "out_folder5" / "test_dagmc2.msh"
    c2d.export_gmsh_mesh_file(filename=str(file2))
    assert file2.is_file()

    # Test Path object
    file3 = tmp_path / "test_dagmc3.msh"
    c2d.export_gmsh_mesh_file(filename=file3)
    assert file3.is_file()

    # Test nested folder with Path
    file4 = tmp_path / "out_folder6" / "test_dagmc4.msh"
    c2d.export_gmsh_mesh_file(filename=file4)
    assert file4.is_file()


def test_check_material_tags_too_long():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        check_material_tags(["a" * 29], [1])
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "Material tag" in str(w[-1].message)
        assert "a" * 29 in str(w[-1].message)


@pytest.mark.parametrize(
    "scale_factor, expected_width",
    [
        (1, 10.0),
        (2, 20.0),
        (10, 100.0),
    ],
)
def test_scaling_factor_when_adding_stp(scale_factor, expected_width, tmp_path):

    c2d = CadToDagmc()
    c2d.add_stp_file("tests/single_cube.stp", scale_factor=scale_factor)
    mesh_file = tmp_path / f"st_test_scaling_factor_{scale_factor}.msh"
    c2d.export_gmsh_mesh_file(str(mesh_file))

    gmsh.initialize()
    gmsh.open(str(mesh_file))
    _, node_coords, _ = gmsh.model.mesh.getNodes()

    # Reshape the node coordinates into a 2D array
    node_coords = node_coords.reshape(-1, 3)

    # Calculate the bounding box
    min_coords = node_coords.min(axis=0)
    max_coords = node_coords.max(axis=0)

    width_x = max_coords[0] - min_coords[0]
    width_y = max_coords[1] - min_coords[1]
    width_z = max_coords[2] - min_coords[2]

    gmsh.finalize()

    assert width_x == expected_width
    assert width_y == expected_width
    assert width_z == expected_width


@pytest.mark.parametrize(
    "scale_factor, expected_width",
    [
        (1, 10.0),
        (2, 20.0),
        (10, 100.0),
    ],
)
def test_scaling_factor_when_adding_cq_object(scale_factor, expected_width, tmp_path):

    box = cq.Workplane("XY").box(10, 10, 10)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, scale_factor=scale_factor, material_tags=["mat1"])
    mesh_file = tmp_path / f"cq_test_scaling_factor_{scale_factor}.msh"
    c2d.export_gmsh_mesh_file(str(mesh_file))

    gmsh.initialize()
    gmsh.open(str(mesh_file))
    _, node_coords, _ = gmsh.model.mesh.getNodes()

    # Reshape the node coordinates into a 2D array
    node_coords = node_coords.reshape(-1, 3)

    # Calculate the bounding box
    min_coords = node_coords.min(axis=0)
    max_coords = node_coords.max(axis=0)

    width_x = max_coords[0] - min_coords[0]
    width_y = max_coords[1] - min_coords[1]
    width_z = max_coords[2] - min_coords[2]

    gmsh.finalize()

    assert width_x == expected_width
    assert width_y == expected_width
    assert width_z == expected_width


@pytest.mark.parametrize(
    "scale_factor, expected_x_width, expected_y_width, expected_z_width",
    [
        (1, 20.0, 10.0, 10.0),
        (2, 40.0, 20.0, 20.0),
        (10, 200.0, 100.0, 100.0),
    ],
)
def test_two_box_scaling_factor_when_adding_cq_object(
    scale_factor, expected_x_width, expected_y_width, expected_z_width, tmp_path
):

    box = cq.Workplane("XY").box(10, 10, 10)
    box2 = cq.Workplane("XY").moveTo(10, 0).box(10, 10, 10)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, scale_factor=scale_factor, material_tags=["mat1"])
    c2d.add_cadquery_object(box2, scale_factor=scale_factor, material_tags=["mat1"])
    mesh_file = tmp_path / f"cq_test_2_box_scaling_factor_{scale_factor}.msh"
    c2d.export_gmsh_mesh_file(str(mesh_file))

    gmsh.initialize()
    gmsh.open(str(mesh_file))
    _, node_coords, _ = gmsh.model.mesh.getNodes()

    # Reshape the node coordinates into a numpy 2D array
    node_coords = node_coords.reshape(-1, 3)

    # Calculate the bounding box
    min_coords = node_coords.min(axis=0)
    max_coords = node_coords.max(axis=0)

    width_x = max_coords[0] - min_coords[0]
    width_y = max_coords[1] - min_coords[1]
    width_z = max_coords[2] - min_coords[2]

    gmsh.finalize()

    assert width_x == expected_x_width
    assert width_y == expected_y_width
    assert width_z == expected_z_width


def test_unstructured_mesh_export_with_surface_mesh(tmp_path):

    box_set_size_course_mesh = cq.Workplane().box(1, 1, 2)
    box_set_size_fine_mesh = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
    box_set_global_mesh = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

    assembly = cq.Assembly()
    assembly.add(box_set_size_course_mesh, color=cq.Color(0, 0, 1))
    assembly.add(box_set_size_fine_mesh, color=cq.Color(0, 1, 0))
    assembly.add(box_set_global_mesh, color=cq.Color(1, 0, 0))

    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags=["mat1", "mat2", "mat3"])

    h5m_file = tmp_path / "conformal-surface-mesh2.h5m"
    vtk_file = tmp_path / "conformal-volume-mesh2.vtk"

    dag_filename, umesh_filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        min_mesh_size=0.01,
        max_mesh_size=10,
        set_size={
            1: 0.5,
            2: 0.4,
            3: 0.4,
        },
        unstructured_volumes=[2],
        umesh_filename=str(vtk_file),
        meshing_backend="gmsh",
    )
    assert h5m_file.is_file()
    assert vtk_file.is_file()
    assert Path(dag_filename).is_file()
    assert Path(umesh_filename).is_file()
    # TODO check the volume mesh outer surface is the same as the surface mesh volume 2 surface


@pytest.mark.parametrize("meshing_backend", ["cadquery", "gmsh"])
def test_unstructured_mesh_with_volumes(meshing_backend, tmp_path):

    box_cutter = cq.Workplane("XY").moveTo(0, 5).box(20, 10, 20)
    inner_sphere = cq.Workplane("XY").sphere(6).cut(box_cutter)
    middle_sphere = cq.Workplane("XY").sphere(6.1).cut(box_cutter).cut(inner_sphere)
    outer_sphere = (
        cq.Workplane("XY")
        .sphere(10)
        .cut(box_cutter)
        .cut(inner_sphere)
        .cut(middle_sphere)
    )

    assembly = cq.Assembly()
    assembly.add(inner_sphere, name="inner_sphere")
    assembly.add(middle_sphere, name="middle_sphere")
    assembly.add(outer_sphere, name="outer_sphere")

    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags=["mat1", "mat2", "mat3"])

    h5m_file = tmp_path / "dagmc.h5m"
    filename = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        set_size={1: 0.9, 2: 0.1, 3: 0.9},
        meshing_backend=meshing_backend,
    )
    assert Path(filename).is_file()

    vtk_file1 = tmp_path / "umesh_vol_1.vtk"
    filename = model.export_unstructured_mesh_file(
        filename=str(vtk_file1),
        set_size={1: 0.9, 2: 0.1, 3: 0.9},
        volumes=[1],  # only mesh volume 1 out of the three volumes
    )
    assert Path(filename).is_file()

    vtk_file2 = tmp_path / "umesh_vol_2.vtk"
    filename = model.export_unstructured_mesh_file(
        filename=str(vtk_file2),
        set_size={1: 0.9, 2: 0.1, 3: 0.9},
        volumes=[2],  # only mesh volume 2 out of the three volumes
    )
    assert Path(filename).is_file()

    vtk_file3 = tmp_path / "umesh_vol_3.vtk"
    filename = model.export_unstructured_mesh_file(
        filename=str(vtk_file3),
        set_size={1: 0.9, 2: 0.1, 3: 0.9},
        volumes=[3],  # only mesh volume 3 out of the three volumes
    )
    assert Path(filename).is_file()

    vtk_file4 = tmp_path / "umesh_vol_1_2.vtk"
    filename = model.export_unstructured_mesh_file(
        filename=str(vtk_file4),
        set_size={1: 0.9, 2: 0.1, 3: 0.9},
        volumes=[1, 2],  # only mesh volumes 1 and 2 out of the three volumes
    )

    assert Path(filename).is_file()
