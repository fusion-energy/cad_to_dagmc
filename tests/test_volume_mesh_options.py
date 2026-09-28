"""3D Gmsh controls must not change the already-generated surface mesh."""

from collections import Counter
from itertools import combinations
from unittest.mock import Mock, call

import cadquery as cq
import gmsh
import h5py
import numpy as np
import pytest

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import _generate_volume_mesh, set_sizes_for_mesh


@pytest.fixture
def model():
    result = CadToDagmc()
    result.add_cadquery_object(cq.Workplane().box(4, 4, 4), material_tags=["steel"])
    return result


def _export(model, exporter, tmp_path, **kwargs):
    options = dict(
        min_mesh_size=0.5,
        max_mesh_size=2.0,
        set_size={"steel": 1.0},
        threads=1,
        imprint=False,
    )
    options.update(kwargs)
    if exporter == "vtk":
        filename = tmp_path / "volume.vtk"
        model.export_unstructured_mesh_file(filename=str(filename), **options)
    elif exporter == "msh":
        filename = tmp_path / "volume.msh"
        model.export_gmsh_mesh_file(filename=str(filename), dimensions=3, **options)
    else:
        filename = tmp_path / "volume.vtk"
        options.setdefault("unstructured_volumes", ["steel"])
        result = model.export_dagmc_h5m_file(
            filename=str(tmp_path / "surface.h5m"),
            umesh_filename=str(filename),
            **options,
        )
        assert result == (str(tmp_path / "surface.h5m"), str(filename))
        assert (tmp_path / "surface.h5m").is_file()
    assert filename.is_file()
    assert not gmsh.isInitialized()


def _surface_triangles():
    """Compare coordinates, since Gmsh can renumber nodes during generate(3)."""
    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    points = dict(zip(node_tags, map(tuple, coords.reshape(-1, 3))))
    return {
        tag: sorted(
            tuple(sorted(points[node] for node in triangle))
            for triangle in gmsh.model.mesh.getElementsByType(2, tag)[1].reshape(-1, 3)
        )
        for _, tag in gmsh.model.getEntities(2)
    }


def _read_vtk_tetrahedra(filename):
    """Read the written mesh, independently of the export's Gmsh session."""
    gmsh.initialize()
    try:
        gmsh.open(str(filename))
        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        _, connectivity = gmsh.model.mesh.getElementsByType(4)
        node_indices = {tag: index for index, tag in enumerate(node_tags)}
        tets = np.array([node_indices[tag] for tag in connectivity]).reshape(-1, 4)
        return coords.reshape(-1, 3), tets
    finally:
        gmsh.finalize()


def _triangle_coordinates(vertices, triangles):
    # VTK stores decimal coordinates, whereas H5M stores binary doubles.
    return {
        tuple(sorted(tuple(np.round(vertices[node], 10)) for node in triangle))
        for triangle in triangles
    }


@pytest.mark.parametrize("algorithm", [1, 10], ids=["delaunay", "hxt"])
@pytest.mark.parametrize("relax_interior", [False, True])
@pytest.mark.parametrize("selection", ["single", "both", "steel_only"])
def test_written_h5m_and_vtk_share_boundary_triangles(
    algorithm, relax_interior, selection, tmp_path
):
    """Tracking facets must match actual tet faces, including shared interfaces.

    Compare the written files, not just Gmsh's in-memory surface elements:
    keeping those elements alone would not prove the tets conform to them.
    """
    model = CadToDagmc()
    cylinder = cq.Workplane("XY").cylinder(height=4, radius=2)
    model.add_cadquery_object(cylinder, material_tags=["steel"])
    if selection != "single":
        model.add_cadquery_object(cylinder.translate((0, 0, 4)), material_tags=["water"])
    h5m_file = tmp_path / "conformal.h5m"
    vtk_file = tmp_path / "conformal.vtk"
    options = None
    if relax_interior:
        options = {
            "Mesh.Optimize": 0,
            "Mesh.MeshSizeExtendFromBoundary": 0,
            "Mesh.MeshSizeMax": 1e22,
        }
    result = model.export_dagmc_h5m_file(
        filename=str(h5m_file),
        umesh_filename=str(vtk_file),
        meshing_backend="gmsh",
        unstructured_volumes=["steel", "water"] if selection == "both" else ["steel"],
        min_mesh_size=0.5,
        max_mesh_size=1.5,
        mesh_algorithm_3d=algorithm,
        volume_mesh_options=options,
        threads=1,
    )
    assert result == (str(h5m_file), str(vtk_file))
    assert not gmsh.isInitialized()

    vertices, tets = _read_vtk_tetrahedra(vtk_file)
    assert tets.size > 0
    with h5py.File(h5m_file) as h5m:
        coords = h5m["tstt/nodes/coordinates"]
        surface_vertices = coords[:]
        surface_triangles = (
            h5m["tstt/elements/Tri3/connectivity"][:].astype(np.int64)
            - int(coords.attrs["start_id"])
        )
    triangle_z = surface_vertices[surface_triangles, 2]
    tet_z = vertices[tets, 2]
    # The cylinders touch on z=2. Checking each region also checks the internal
    # interface, which would disappear from a boundary of their combined mesh.
    for upper in ([False, True] if selection == "both" else [False]):
        mask = tet_z.mean(axis=1) > 2 if upper else tet_z.mean(axis=1) < 2
        region_tets = tets[mask]
        assert region_tets.size > 0
        if upper:
            assert (vertices[region_tets, 2] >= 2 - 1e-10).all()
            region_triangles = surface_triangles[(triangle_z >= 2 - 1e-10).all(axis=1)]
        else:
            assert (vertices[region_tets, 2] <= 2 + 1e-10).all()
            region_triangles = surface_triangles[(triangle_z <= 2 + 1e-10).all(axis=1)]
        faces = Counter(
            tuple(sorted(face))
            for tet in region_tets
            for face in combinations(tet, 3)
        )
        assert set(faces.values()) <= {1, 2}
        boundary = [face for face, count in faces.items() if count == 1]
        expected = _triangle_coordinates(surface_vertices, region_triangles)
        assert expected
        assert _triangle_coordinates(vertices, boundary) == expected
    if selection != "both":
        assert (tet_z <= 2 + 1e-10).all()


@pytest.mark.parametrize("algorithm", [1, 10])
def test_set_sizes_separates_surface_and_volume_algorithms(algorithm):
    mock_gmsh = Mock()
    # Keep all pre-existing positional arguments usable.
    result = set_sizes_for_mesh(
        mock_gmsh, 0.5, 2, 6, None, None, 2, mesh_algorithm_3d=algorithm
    )
    assert result is mock_gmsh
    mock_gmsh.option.setNumber.assert_has_calls(
        [
            call("Mesh.Algorithm", 6),
            call("Mesh.Algorithm3D", algorithm),
            call("General.NumThreads", 2),
        ]
    )


def test_set_sizes_defaults_to_delaunay():
    mock_gmsh = Mock()
    set_sizes_for_mesh(mock_gmsh)
    mock_gmsh.option.setNumber.assert_any_call("Mesh.Algorithm3D", 1)


@pytest.mark.parametrize("surfaces_meshed", [False, True])
def test_volume_options_call_order_and_value_types(surfaces_meshed):
    mock_gmsh = Mock()
    options = {
        "Mesh.Optimize": 0,
        "Mesh.MeshSizeMax": 1e22,
        "General.DefaultFileName": "volume.msh",
    }
    original_options = options.copy()

    _generate_volume_mesh(mock_gmsh, options, surfaces_meshed=surfaces_meshed)

    expected = [] if surfaces_meshed else [call.model.mesh.generate(2)]
    expected += [
        call.option.setNumber("Mesh.Optimize", 0),
        call.option.setNumber("Mesh.MeshSizeMax", 1e22),
        call.option.setString("General.DefaultFileName", "volume.msh"),
        call.model.mesh.generate(3),
    ]
    assert mock_gmsh.mock_calls == expected
    assert options == original_options


@pytest.mark.parametrize("exporter", ["vtk", "msh", "dagmc"])
@pytest.mark.parametrize("algorithm", [1, 10])
def test_volume_options_preserve_surface_mesh(
    model, exporter, algorithm, tmp_path, monkeypatch
):
    options = {
        "Mesh.Optimize": 0,
        "Mesh.MeshSizeExtendFromBoundary": 0,
        "Mesh.MeshSizeMax": 1e22,
        "General.DefaultFileName": "volume.msh",
    }
    original_options = options.copy()
    generate = gmsh.model.mesh.generate
    dimensions = []
    surface_mesh = None

    def capture(dimension):
        nonlocal surface_mesh
        dimensions.append(dimension)
        assert gmsh.option.getNumber("Mesh.Algorithm") == 6
        assert gmsh.option.getNumber("Mesh.Algorithm3D") == algorithm
        if dimension == 2:
            assert gmsh.option.getNumber("Mesh.MeshSizeMax") == 2.0
            assert gmsh.option.getNumber("Mesh.MeshSizeExtendFromBoundary") == 1
            assert gmsh.option.getNumber("Mesh.Optimize") == 1
        else:
            assert dimensions == [2, 3]
            for name, value in options.items():
                if isinstance(value, str):
                    assert gmsh.option.getString(name) == value
                else:
                    assert gmsh.option.getNumber(name) == value
        generate(dimension)
        if dimension == 2:
            surface_mesh = _surface_triangles()
            assert surface_mesh and all(surface_mesh.values())
        else:
            assert _surface_triangles() == surface_mesh
            assert gmsh.model.mesh.getElementsByType(4)[0].size > 0

    monkeypatch.setattr(gmsh.model.mesh, "generate", capture)
    _export(
        model, exporter, tmp_path,
        mesh_algorithm=6,
        mesh_algorithm_3d=algorithm,
        volume_mesh_options=options,
    )
    assert dimensions == [2, 3]
    assert options == original_options


@pytest.mark.parametrize("exporter", ["vtk", "msh", "dagmc"])
@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"volume_mesh_options": None},
        {"volume_mesh_options": {}},
        {"mesh_algorithm_3d": 10},
    ],
)
def test_default_generation_sequence(model, exporter, kwargs, tmp_path, monkeypatch):
    generate = gmsh.model.mesh.generate
    dimensions = []

    def capture(dimension):
        dimensions.append(dimension)
        assert gmsh.option.getNumber("Mesh.Algorithm3D") == kwargs.get("mesh_algorithm_3d", 1)
        assert gmsh.option.getNumber("Mesh.MeshSizeMax") == 2.0
        assert gmsh.option.getNumber("Mesh.Optimize") == 1
        generate(dimension)

    monkeypatch.setattr(gmsh.model.mesh, "generate", capture)
    _export(model, exporter, tmp_path, **kwargs)
    assert dimensions == ([2, 3] if exporter == "dagmc" else [3])


@pytest.mark.parametrize("exporter", ["vtk", "dagmc"])
@pytest.mark.parametrize("algorithm", [1, 10])
def test_volume_options_with_selected_touching_volumes(
    model, exporter, algorithm, tmp_path, monkeypatch
):
    model.add_cadquery_object(
        cq.Workplane().box(4, 4, 4).translate((4, 0, 0)), material_tags=["water"]
    )
    generate = gmsh.model.mesh.generate
    surface_mesh = None

    def capture(dimension):
        nonlocal surface_mesh
        if dimension == 3:
            assert len(gmsh.model.getEntities(3)) == 1
        generate(dimension)
        if dimension == 2:
            surface_mesh = _surface_triangles()
        else:
            remaining = _surface_triangles()
            assert remaining
            assert remaining == {tag: surface_mesh[tag] for tag in remaining}
            assert gmsh.model.mesh.getElementsByType(4)[0].size > 0

    monkeypatch.setattr(gmsh.model.mesh, "generate", capture)
    selection = {"volumes": [1]} if exporter == "vtk" else {"unstructured_volumes": ["steel"]}
    _export(
        model, exporter, tmp_path,
        imprint=True,
        mesh_algorithm_3d=algorithm,
        volume_mesh_options={
            "Mesh.MeshSizeMax": 1e22,
            "Mesh.MeshSizeExtendFromBoundary": 0,
            "Mesh.Optimize": 0,
        },
        **selection,
    )


@pytest.mark.parametrize("exporter", ["vtk", "msh", "dagmc"])
def test_volume_options_override_algorithm(model, exporter, tmp_path, monkeypatch):
    generate = gmsh.model.mesh.generate

    def capture(dimension):
        assert gmsh.option.getNumber("Mesh.Algorithm3D") == (1 if dimension == 2 else 10)
        generate(dimension)

    monkeypatch.setattr(gmsh.model.mesh, "generate", capture)
    _export(model, exporter, tmp_path, volume_mesh_options={"Mesh.Algorithm3D": 10})


@pytest.mark.parametrize("exporter", ["msh", "dagmc"])
def test_surface_only_export_ignores_volume_options(model, exporter, tmp_path, monkeypatch):
    generate = gmsh.model.mesh.generate
    dimensions = []

    def capture(dimension):
        dimensions.append(dimension)
        assert gmsh.option.getNumber("Mesh.MeshSizeMax") == 2.0
        generate(dimension)

    monkeypatch.setattr(gmsh.model.mesh, "generate", capture)
    kwargs = dict(
        max_mesh_size=2.0,
        threads=1,
        volume_mesh_options={"Mesh.MeshSizeMax": 1e22, "Invalid.Option": 0},
    )
    if exporter == "msh":
        model.export_gmsh_mesh_file(filename=str(tmp_path / "surface.msh"), **kwargs)
    else:
        model.export_dagmc_h5m_file(filename=str(tmp_path / "surface.h5m"), **kwargs)
    assert dimensions == [2]
    assert not gmsh.isInitialized()


@pytest.mark.parametrize("exporter", ["vtk", "msh", "dagmc"])
def test_invalid_volume_option_finalizes_session(model, exporter, tmp_path, monkeypatch):
    generate = gmsh.model.mesh.generate
    dimensions = []

    def capture(dimension):
        dimensions.append(dimension)
        generate(dimension)

    monkeypatch.setattr(gmsh.model.mesh, "generate", capture)
    with pytest.raises(Exception, match="Could not set option 'Mesh.InvalidVolumeOption'"):
        _export(
            model, exporter, tmp_path,
            volume_mesh_options={"Mesh.InvalidVolumeOption": 0},
        )
    assert dimensions == [2]
    assert not gmsh.isInitialized()


@pytest.mark.parametrize(
    "kwargs",
    [{"mesh_algorithm_3d": 10}, {"volume_mesh_options": {"Mesh.Optimize": 0}}],
)
def test_new_options_select_gmsh_backend(model, kwargs, tmp_path, monkeypatch):
    mock_init = Mock(side_effect=RuntimeError("gmsh selected"))
    monkeypatch.setattr("cad_to_dagmc.core.init_gmsh", mock_init)
    with pytest.raises(RuntimeError, match="gmsh selected"):
        model.export_dagmc_h5m_file(filename=str(tmp_path / "surface.h5m"), **kwargs)
    mock_init.assert_called_once()


@pytest.mark.parametrize(
    "kwargs",
    [{"mesh_algorithm_3d": 10}, {"volume_mesh_options": {"Mesh.Optimize": 0}}],
)
def test_new_options_reject_ambiguous_backend(model, kwargs, tmp_path):
    with pytest.raises(ValueError, match="Ambiguous backend"):
        model.export_dagmc_h5m_file(
            filename=str(tmp_path / "surface.h5m"), target_edge_length=1, **kwargs
        )


@pytest.mark.parametrize("backend", ["cadquery", "cad-to-dagmc-mesher"])
def test_non_gmsh_backend_warns_about_volume_options(model, backend, tmp_path, monkeypatch):
    # Stop before either backend runs, after argument handling and warnings.
    monkeypatch.setattr(
        "cad_to_dagmc.core.get_ids_from_assembly",
        Mock(side_effect=RuntimeError("arguments handled")),
    )
    with pytest.warns(UserWarning, match="mesh_algorithm_3d, volume_mesh_options"):
        with pytest.raises(RuntimeError, match="arguments handled"):
            model.export_dagmc_h5m_file(
                filename=str(tmp_path / "surface.h5m"),
                meshing_backend=backend,
                mesh_algorithm_3d=10,
                volume_mesh_options={"Mesh.Optimize": 0},
            )


def test_unstructured_mesher_warns_about_volume_options(model, tmp_path, monkeypatch):
    mock_export = Mock(return_value="volume.vtk")
    monkeypatch.setattr(model, "_export_unstructured_mesh_file_with_mesher", mock_export)
    with pytest.warns(UserWarning, match="mesh_algorithm_3d, volume_mesh_options"):
        model.export_unstructured_mesh_file(
            filename=str(tmp_path / "volume.vtk"),
            target_edge_length=1,
            mesh_algorithm_3d=10,
            volume_mesh_options={"Mesh.Optimize": 0},
        )
    mock_export.assert_called_once()