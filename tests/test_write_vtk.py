import os
import tempfile
from cad_to_dagmc.core import write_vtk


def test_write_vtk_single_tet():
    """Write a single tetrahedron and verify the VTK file contents."""
    vertices = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    tetrahedra = [[0, 1, 2, 3]]

    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as f:
        filename = f.name

    try:
        write_vtk(filename, vertices, tetrahedra)

        with open(filename) as f:
            lines = f.readlines()

        assert lines[0].strip() == "# vtk DataFile Version 2.0"
        assert lines[2].strip() == "ASCII"
        assert lines[3].strip() == "DATASET UNSTRUCTURED_GRID"
        assert lines[4].strip() == "POINTS 4 double"
        assert lines[5].strip() == "0.0 0.0 0.0"
        assert lines[6].strip() == "1.0 0.0 0.0"
        assert lines[7].strip() == "0.0 1.0 0.0"
        assert lines[8].strip() == "0.0 0.0 1.0"
        assert lines[9].strip() == "CELLS 1 5"
        assert lines[10].strip() == "4 0 1 2 3"
        assert lines[11].strip() == "CELL_TYPES 1"
        assert lines[12].strip() == "10"
    finally:
        os.unlink(filename)


def test_write_vtk_two_tets():
    """Write two tetrahedra sharing a face."""
    vertices = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
    ]
    tetrahedra = [[0, 1, 2, 3], [1, 2, 3, 4]]

    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as f:
        filename = f.name

    try:
        write_vtk(filename, vertices, tetrahedra)

        with open(filename) as f:
            content = f.read()

        assert "POINTS 5 double" in content
        assert "CELLS 2 10" in content
        assert "CELL_TYPES 2" in content
        # check two tet cell type lines after CELL_TYPES header
        cell_types_section = content.split("CELL_TYPES 2\n")[1]
        assert cell_types_section.strip() == "10\n10"
    finally:
        os.unlink(filename)
