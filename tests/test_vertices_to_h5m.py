"""Tests for vertices_to_h5m function with both pymoab and h5py backends."""

import os
from pathlib import Path

import pytest

from cad_to_dagmc.core import vertices_to_h5m, PyMoabNotFoundError
from test_python_api import get_volumes_and_materials_from_h5m

# Check if pymoab is available
try:
    import pymoab
    PYMOAB_AVAILABLE = True
except ImportError:
    PYMOAB_AVAILABLE = False


# Single tetrahedron: 4 vertices, 4 triangular faces, 1 volume
TETRAHEDRON_VERTICES = [
    [0.0, 0.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
]

# Dict format: solid_id -> face_id -> triangles
TETRAHEDRON_SINGLE_VOLUME = {
    1: {
        1: [[0, 2, 1]],  # bottom face (z=0)
        2: [[0, 1, 3]],  # front face
        3: [[1, 2, 3]],  # diagonal face
        4: [[0, 3, 2]],  # left face
    }
}


@pytest.mark.parametrize("method", ["pymoab", "h5py"])
def test_single_tetrahedron(method, tmp_path):
    """Test creating h5m from a single tetrahedron."""
    h5m_filename = tmp_path / f"tetrahedron_{method}.h5m"

    vertices_to_h5m(
        vertices=TETRAHEDRON_VERTICES,
        triangles_by_solid_by_face=TETRAHEDRON_SINGLE_VOLUME,
        material_tags=["mat1"],
        h5m_filename=str(h5m_filename),
        method=method,
    )

    assert h5m_filename.exists()

    # Verify the h5m file contains the correct volume and material
    vol_mat = get_volumes_and_materials_from_h5m(str(h5m_filename))
    assert vol_mat == {1: "mat:mat1"}


# Two tetrahedra sharing a face
TWO_TETRAHEDRA_VERTICES = [
    [0.0, 0.0, 0.0],  # 0
    [1.0, 0.0, 0.0],  # 1
    [0.0, 1.0, 0.0],  # 2
    [0.0, 0.0, 1.0],  # 3
    [1.0, 1.0, 1.0],  # 4 - apex of second tetrahedron
]

# Two volumes sharing face 3 (the diagonal face)
TWO_TETRAHEDRA_SHARED_FACE = {
    1: {
        1: [[0, 2, 1]],  # bottom face (z=0)
        2: [[0, 1, 3]],  # front face
        3: [[1, 2, 3]],  # diagonal face (shared)
        4: [[0, 3, 2]],  # left face
    },
    2: {
        3: [[1, 3, 2]],  # diagonal face (shared, opposite winding)
        5: [[1, 4, 3]],  # new face
        6: [[2, 3, 4]],  # new face
        7: [[1, 2, 4]],  # new face
    },
}


@pytest.mark.parametrize("method", ["pymoab", "h5py"])
def test_two_tetrahedra_shared_face(method, tmp_path):
    """Test creating h5m from two tetrahedra sharing a face."""
    h5m_filename = tmp_path / f"two_tetrahedra_{method}.h5m"

    vertices_to_h5m(
        vertices=TWO_TETRAHEDRA_VERTICES,
        triangles_by_solid_by_face=TWO_TETRAHEDRA_SHARED_FACE,
        material_tags=["mat1", "mat2"],
        h5m_filename=str(h5m_filename),
        method=method,
    )

    assert h5m_filename.exists()

    # Verify the h5m file contains the correct volumes and materials
    vol_mat = get_volumes_and_materials_from_h5m(str(h5m_filename))
    assert vol_mat == {1: "mat:mat1", 2: "mat:mat2"}


@pytest.mark.parametrize("method", ["pymoab", "h5py"])
def test_implicit_complement(method, tmp_path):
    """Test creating h5m with implicit complement material tag."""
    h5m_filename = tmp_path / f"tetrahedron_complement_{method}.h5m"

    vertices_to_h5m(
        vertices=TETRAHEDRON_VERTICES,
        triangles_by_solid_by_face=TETRAHEDRON_SINGLE_VOLUME,
        material_tags=["mat1"],
        h5m_filename=str(h5m_filename),
        implicit_complement_material_tag="void",
        method=method,
    )

    assert h5m_filename.exists()


@pytest.mark.skipif(PYMOAB_AVAILABLE, reason="Test only runs when pymoab is not installed")
def test_pymoab_not_found_error_message(tmp_path):
    """Test that PyMoabNotFoundError provides helpful installation instructions."""
    h5m_filename = tmp_path / "test.h5m"

    with pytest.raises(PyMoabNotFoundError) as excinfo:
        vertices_to_h5m(
            vertices=TETRAHEDRON_VERTICES,
            triangles_by_solid_by_face=TETRAHEDRON_SINGLE_VOLUME,
            material_tags=["mat1"],
            h5m_filename=str(h5m_filename),
            method="pymoab",  # explicitly request pymoab backend
        )

    error_message = str(excinfo.value)
    # Check that the error message contains helpful installation instructions
    assert "pymoab is not installed" in error_message
    assert "conda-forge" in error_message
    assert "pip install --extra-index-url" in error_message
    assert "shimwell.github.io/wheels" in error_message
    assert "bitbucket" in error_message.lower()
    assert "h5py" in error_message  # mentions the alternative


def test_pymoab_not_found_error_is_importerror():
    """Test that PyMoabNotFoundError is a subclass of ImportError."""
    assert issubclass(PyMoabNotFoundError, ImportError)
