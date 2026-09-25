"""Mesh quality tests for the cad-to-dagmc-mesher backend.

The transport tests check that the outputs are usable by OpenMC. These tests
check that the meshes themselves are geometrically correct: the tetrahedra
fill the CAD volume, the vtk volume mesh is conformal with the h5m surface
mesh, touching solids share an identical interface triangulation, and
scale_factor is applied consistently to both outputs.

All checks use numpy, h5py and trimesh only (no openmc, no pymoab), so they
run in every CI environment where cad-to-dagmc-mesher is installed.
"""

from collections import Counter

import cadquery as cq
import numpy as np
import pytest

from cad_to_dagmc import CadToDagmc

pytest.importorskip("cad_to_dagmc_mesher")


def parse_vtk(filename):
    """Parse the ASCII legacy VTK written by write_vtk.

    Returns (vertices (N, 3) float array, tets (M, 4) int array).
    """
    with open(filename) as f:
        tok = f.read().split()
    i = tok.index("POINTS")
    n_pts = int(tok[i + 1])
    verts = np.array(tok[i + 3:i + 3 + 3 * n_pts], dtype=float).reshape(n_pts, 3)
    j = tok.index("CELLS", i)
    n_cells, n_ints = int(tok[j + 1]), int(tok[j + 2])
    assert n_ints == n_cells * 5, "expected pure tetrahedron cells"
    data = np.array(tok[j + 3:j + 3 + n_ints], dtype=np.int64).reshape(n_cells, 5)
    assert (data[:, 0] == 4).all()
    return verts, data[:, 1:]


def tet_signed_volumes(verts, tets):
    a, b, c, d = (verts[tets[:, k]] for k in range(4))
    return np.einsum("ij,ij->i", np.cross(b - a, c - a), d - a) / 6.0


def boundary_faces(tets):
    """Faces (sorted vertex index tuples) belonging to exactly one tet."""
    faces = Counter()
    for t in tets:
        for f in ((t[0], t[1], t[2]), (t[0], t[1], t[3]),
                  (t[0], t[2], t[3]), (t[1], t[2], t[3])):
            faces[tuple(sorted(f))] += 1
    return [f for f, n in faces.items() if n == 1]


def read_h5m_surface(filename):
    """Read vertices and triangles from an h5m file written by cad_to_dagmc."""
    import h5py

    with h5py.File(filename, "r") as f:
        coords = f["tstt/nodes/coordinates"][:]
        start_id = int(f["tstt/nodes/coordinates"].attrs["start_id"])
        tris = f["tstt/elements/Tri3/connectivity"][:].astype(np.int64) - start_id
    return coords, tris


def test_tet_mesh_fills_the_cad_volume(tmp_path):
    """The tetrahedra must tile the solid: valid indices, no degenerate or
    inverted tets, and a total volume matching the CAD solid."""
    cylinder = cq.Workplane("XY").cylinder(height=10, radius=4)
    cad_volume = cylinder.val().Volume()

    model = CadToDagmc()
    model.add_cadquery_object(cylinder, material_tags=["mat1"])
    vtk_file = str(tmp_path / "umesh.vtk")
    model.export_unstructured_mesh_file(filename=vtk_file, target_edge_length=1.5,
                                        meshing_backend="cad-to-dagmc-mesher")

    verts, tets = parse_vtk(vtk_file)
    assert tets.min() >= 0 and tets.max() < len(verts)

    signed = tet_signed_volumes(verts, tets)
    assert (np.abs(signed) > 1e-12).all(), "degenerate (zero volume) tet"
    assert (signed > 0).all() or (signed < 0).all(), "mixed tet orientation"

    tet_volume = np.abs(signed).sum()
    assert abs(tet_volume - cad_volume) / cad_volume < 0.01


def test_h5m_and_vtk_are_conformal(tmp_path):
    """The h5m tracking surface and the vtk tet mesh must enclose the same
    volume, and the tet boundary must be watertight. This is what makes
    unstructured mesh tallies score every collision of the DAGMC geometry."""
    import trimesh

    cylinder = cq.Workplane("XY").cylinder(height=10, radius=4)
    model = CadToDagmc()
    model.add_cadquery_object(cylinder, material_tags=["mat1"])
    h5m_file = str(tmp_path / "conformal.h5m")
    vtk_file = str(tmp_path / "conformal.vtk")
    model.export_dagmc_h5m_file(filename=h5m_file, meshing_backend="cad-to-dagmc-mesher", tet_volumes=["mat1"],
                                target_edge_length=1.5, umesh_filename=vtk_file)

    verts, tets = parse_vtk(vtk_file)
    tet_volume = np.abs(tet_signed_volumes(verts, tets)).sum()

    hverts, htris = read_h5m_surface(h5m_file)
    surface = trimesh.Trimesh(vertices=hverts, faces=htris, process=True)
    assert surface.is_watertight
    assert abs(abs(surface.volume) - tet_volume) / tet_volume < 0.005

    # the tet boundary itself must be a closed surface: every boundary edge
    # shared by exactly 2 boundary faces
    edges = Counter()
    for f in boundary_faces(tets):
        for e in ((f[0], f[1]), (f[0], f[2]), (f[1], f[2])):
            edges[tuple(sorted(e))] += 1
    non_manifold = [e for e, n in edges.items() if n != 2]
    assert not non_manifold, f"{len(non_manifold)} non-manifold boundary edges"


def test_touching_solids_share_identical_interface(tmp_path):
    """Two imprinted touching boxes must get identical interface
    triangulations so the combined volume mesh has no gaps or double
    counted regions at the shared face."""
    from cad_to_dagmc_mesher.cad import mesh_assembly

    assembly = cq.Assembly()
    assembly.add(cq.Workplane("XY").box(10, 10, 10))
    assembly.add(cq.Workplane("XY").moveTo(10, 0).box(10, 10, 10))
    result = mesh_assembly(assembly, ["m1", "m2"], tolerance=0.01,
                           angular_tolerance=0.2, tet_volumes=["m1", "m2"],
                           target_edge_length=2.5)

    interface_keys = []
    for solid_data in result["tet_data"].values():
        verts = np.asarray(solid_data["vertices"], dtype=float).reshape(-1, 3)
        tets = np.asarray(solid_data["tetrahedra"], dtype=np.int64).reshape(-1, 4)

        volume = np.abs(tet_signed_volumes(verts, tets)).sum()
        assert abs(volume - 1000) < 5

        # interface plane is x=5
        faces = [f for f in boundary_faces(tets)
                 if all(abs(verts[i][0] - 5.0) < 1e-6 for i in f)]
        keys = {tuple(sorted(tuple(np.round(verts[i], 6)) for i in f))
                for f in faces}
        interface_keys.append(keys)

    assert len(interface_keys) == 2
    assert interface_keys[0] == interface_keys[1]


def test_scale_factor_consistent_between_h5m_and_vtk(tmp_path):
    """scale_factor must scale the h5m and the vtk identically."""
    cylinder = cq.Workplane("XY").cylinder(height=10, radius=4)
    cad_volume = cylinder.val().Volume()

    model = CadToDagmc()
    model.add_cadquery_object(cylinder, material_tags=["mat1"])
    h5m_file = str(tmp_path / "scaled.h5m")
    vtk_file = str(tmp_path / "scaled.vtk")
    model.export_dagmc_h5m_file(filename=h5m_file, meshing_backend="cad-to-dagmc-mesher", tet_volumes=["mat1"],
                                target_edge_length=3.0, umesh_filename=vtk_file,
                                scale_factor=2.0)

    verts, tets = parse_vtk(vtk_file)
    tet_volume = np.abs(tet_signed_volumes(verts, tets)).sum()
    assert abs(tet_volume - 8 * cad_volume) / (8 * cad_volume) < 0.02

    hverts, _ = read_h5m_surface(h5m_file)
    h5m_bbox = np.array([hverts.min(axis=0), hverts.max(axis=0)])
    vtk_bbox = np.array([verts.min(axis=0), verts.max(axis=0)])
    np.testing.assert_allclose(h5m_bbox, vtk_bbox, atol=1e-6)
    np.testing.assert_allclose(h5m_bbox, [[-8, -8, -10], [8, 8, 10]], atol=0.5)


def test_repeated_exports_are_deterministic_and_independent(tmp_path):
    """Exporting twice from one model gives identical meshes, and an earlier
    scaled export must not leak its scaling into later exports."""
    cylinder = cq.Workplane("XY").cylinder(height=10, radius=4)
    cad_volume = cylinder.val().Volume()

    model = CadToDagmc()
    model.add_cadquery_object(cylinder, material_tags=["mat1"])

    scaled = str(tmp_path / "scaled.vtk")
    model.export_unstructured_mesh_file(filename=scaled, target_edge_length=3.0,
                                        meshing_backend="cad-to-dagmc-mesher",
                                        scale_factor=2.0)

    first = str(tmp_path / "first.vtk")
    second = str(tmp_path / "second.vtk")
    model.export_unstructured_mesh_file(filename=first, target_edge_length=2.0,
                                        meshing_backend="cad-to-dagmc-mesher")
    model.export_unstructured_mesh_file(filename=second, target_edge_length=2.0,
                                        meshing_backend="cad-to-dagmc-mesher")

    v1, t1 = parse_vtk(first)
    v2, t2 = parse_vtk(second)
    assert v1.shape == v2.shape and (t1 == t2).all()
    np.testing.assert_array_equal(v1, v2)

    tet_volume = np.abs(tet_signed_volumes(v1, t1)).sum()
    assert abs(tet_volume - cad_volume) / cad_volume < 0.01
