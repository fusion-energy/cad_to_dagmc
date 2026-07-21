import os
import tempfile

import cadquery as cq
import numpy as np
import pytest

try:
    import openmc
except ImportError:
    openmc = None

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import write_vtk, combine_tet_meshes


def _box_to_tets(x0, y0, z0, dx, dy, dz):
    """Decompose an axis-aligned box into 6 tetrahedra.

    Returns (vertices, tetrahedra) with vertices as an (8, 3) array and
    tetrahedra as a (6, 4) array of zero-based indices. The 6 tets share the
    0-6 body diagonal and tile the box exactly.
    """
    vertices = np.array(
        [
            [x0, y0, z0],
            [x0 + dx, y0, z0],
            [x0 + dx, y0 + dy, z0],
            [x0, y0 + dy, z0],
            [x0, y0, z0 + dz],
            [x0 + dx, y0, z0 + dz],
            [x0 + dx, y0 + dy, z0 + dz],
            [x0, y0 + dy, z0 + dz],
        ],
        dtype=float,
    )
    tetrahedra = np.array(
        [
            [0, 1, 2, 6],
            [0, 2, 3, 6],
            [0, 3, 7, 6],
            [0, 7, 4, 6],
            [0, 4, 5, 6],
            [0, 5, 1, 6],
        ],
        dtype=np.int64,
    )
    return vertices, tetrahedra


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


def test_write_vtk_accepts_numpy_arrays():
    """write_vtk should accept numpy arrays as well as lists of lists."""
    vertices, tetrahedra = _box_to_tets(0, 0, 0, 1, 1, 1)

    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as f:
        filename = f.name

    try:
        write_vtk(filename, vertices, tetrahedra)
        with open(filename) as f:
            content = f.read()
        assert "POINTS 8 double" in content
        assert "CELLS 6 30" in content  # 6 tets * 5 ints
        assert "CELL_TYPES 6" in content
        # every cell is a VTK_TETRA (type 10) and starts with 4 nodes
        cell_block = content.split("CELLS 6 30\n")[1].split("CELL_TYPES")[0]
        for line in cell_block.strip().splitlines():
            assert line.split()[0] == "4"
            assert len(line.split()) == 5
    finally:
        os.unlink(filename)


def test_combine_tet_meshes_offsets_indices():
    """Per-solid tetrahedra must be offset by the running vertex count."""
    verts_a, tets_a = _box_to_tets(-2, -2, -2, 2, 4, 4)
    verts_b, tets_b = _box_to_tets(0, -2, -2, 2, 4, 4)

    # Both solids index into their own local vertex list (starting at 0).
    tet_data = {
        1: {"vertices": verts_a, "tetrahedra": tets_a},
        2: {"vertices": verts_b, "tetrahedra": tets_b},
    }

    vertices, tetrahedra = combine_tet_meshes(tet_data)

    # Vertices are concatenated.
    assert vertices.shape == (16, 3)
    assert tetrahedra.shape == (12, 4)
    np.testing.assert_array_equal(vertices[:8], verts_a)
    np.testing.assert_array_equal(vertices[8:], verts_b)

    # Solid 1 tets are unchanged, solid 2 tets are offset by len(verts_a) = 8.
    np.testing.assert_array_equal(tetrahedra[:6], tets_a)
    np.testing.assert_array_equal(tetrahedra[6:], tets_b + 8)

    # Every index is valid and the two solids reference disjoint vertex ranges.
    assert tetrahedra.max() == 15
    assert tetrahedra[:6].max() < 8
    assert tetrahedra[6:].min() >= 8


def test_combine_tet_meshes_empty():
    """An empty tet_data returns empty arrays with the right shape."""
    vertices, tetrahedra = combine_tet_meshes({})
    assert vertices.shape == (0, 3)
    assert tetrahedra.shape == (0, 4)


# The following validation tests exercise the fail-fast branches that guard the
# cad-to-dagmc-mesher backend. They raise before the mesher is imported, so
# they run even when cad-to-dagmc-mesher is not installed.


def test_export_unstructured_mesh_file_rejects_bad_backend():
    model = CadToDagmc()
    with pytest.raises(ValueError, match="meshing_backend"):
        model.export_unstructured_mesh_file("x.vtk", meshing_backend="not-a-backend")


def test_export_unstructured_mesh_file_mesher_requires_target_edge_length():
    model = CadToDagmc()
    with pytest.raises(ValueError, match="target_edge_length"):
        model.export_unstructured_mesh_file(
            "x.vtk", meshing_backend="cad-to-dagmc-mesher"
        )


def test_export_unstructured_mesh_file_auto_selects_mesher():
    """Passing a mesher-specific tet argument without meshing_backend selects
    the cad-to-dagmc-mesher backend automatically. The mesher branch then
    fails fast on the missing target_edge_length, which proves the backend
    was selected (the gmsh backend would not raise this error)."""
    model = CadToDagmc()
    with pytest.raises(ValueError, match="target_edge_length"):
        model.export_unstructured_mesh_file("x.vtk", tet_volumes=["mat1"])


def test_export_dagmc_h5m_file_mesher_requires_both_tet_args():
    """tet_volumes without target_edge_length must fail fast, not silently skip
    writing the .vtk and change the return type to a bare string."""
    model = CadToDagmc()
    model.add_cadquery_object(
        cq.Workplane("XY").box(10, 10, 10), material_tags=["mat1"]
    )
    with pytest.raises(ValueError, match="target_edge_length"):
        model.export_dagmc_h5m_file(
            filename="x.h5m",
            meshing_backend="cad-to-dagmc-mesher",
            tet_volumes=["mat1"],
        )


@pytest.mark.skipif(openmc is None, reason="openmc tests only required for CI")
def test_write_vtk_openmc_moab_round_trip(tmp_path):
    """The written .vtk must load via openmc.UnstructuredMesh(library="moab")
    and produce a working transport tally.

    This is the test that actually proves the file is usable (rather than just
    well-formed ASCII) and settles the question of whether GLOBAL_ID blocks are
    required by the MOAB reader - they are not.
    """
    # Two adjacent boxes, combined into one mesh that fills [-2, 2]^3.
    verts_a, tets_a = _box_to_tets(-2, -2, -2, 2, 4, 4)
    verts_b, tets_b = _box_to_tets(0, -2, -2, 2, 4, 4)
    tet_data = {
        1: {"vertices": verts_a, "tetrahedra": tets_a},
        2: {"vertices": verts_b, "tetrahedra": tets_b},
    }
    vertices, tetrahedra = combine_tet_meshes(tet_data)
    n_tets = len(tetrahedra)

    vtk_file = str(tmp_path / "umesh.vtk")
    write_vtk(vtk_file, vertices, tetrahedra)

    # cross_sections.xml pointing at the bundled H1 data file (absolute path
    # so the run works from any working directory).
    h1 = os.path.join(os.path.dirname(__file__), "ENDFB-7.1-NNDC_H1.h5")
    xs_xml = tmp_path / "cross_sections.xml"
    xs_xml.write_text(
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        "<cross_sections>\n"
        f'<library materials="H1" path="{h1}" type="neutron"/>\n'
        "</cross_sections>\n"
    )
    openmc.config["cross_sections"] = str(xs_xml)

    mat = openmc.Material(name="mat1")
    mat.add_nuclide("H1", 1.0, "ao")
    mat.set_density("g/cm3", 0.01)
    materials = openmc.Materials([mat])

    box = openmc.model.RectangularParallelepiped(
        -2, 2, -2, 2, -2, 2, boundary_type="vacuum"
    )
    cell = openmc.Cell(region=-box, fill=mat)
    geometry = openmc.Geometry([cell])

    source = openmc.IndependentSource()
    source.space = openmc.stats.Point((0.1, 0.1, 0.1))
    source.angle = openmc.stats.Isotropic()
    source.energy = openmc.stats.Discrete([14e6], [1.0])

    settings = openmc.Settings()
    settings.run_mode = "fixed source"
    settings.batches = 4
    settings.particles = 2000
    settings.source = source
    settings.photon_transport = False

    umesh = openmc.UnstructuredMesh(vtk_file, library="moab")
    tally = openmc.Tally(name="umesh_tally")
    tally.filters = [openmc.MeshFilter(umesh)]
    tally.scores = ["flux"]
    tallies = openmc.Tallies([tally])

    model = openmc.Model(
        materials=materials, geometry=geometry, settings=settings, tallies=tallies
    )

    sp_path = model.run(cwd=str(tmp_path), output=False)
    statepoint = openmc.StatePoint(sp_path)
    result = statepoint.get_tally(name="umesh_tally")
    mean = np.asarray(result.mean).flatten()
    statepoint.close()

    # MOAB read back exactly the tetrahedra we wrote ...
    assert len(mean) == n_tets
    # ... and the tally recorded a finite, non-zero flux somewhere.
    assert np.all(np.isfinite(mean))
    assert mean.sum() > 0.0
