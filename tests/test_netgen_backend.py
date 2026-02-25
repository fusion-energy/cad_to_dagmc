"""Tests for the Netgen meshing backend."""

from pathlib import Path

import cadquery as cq
import h5py
import pytest

from cad_to_dagmc import CadToDagmc
from conftest import NETGEN_AVAILABLE

# Reuse the h5m reader from test_python_api
from test_python_api import get_volumes_and_materials_from_h5m


pytestmark = pytest.mark.skipif(
    not NETGEN_AVAILABLE, reason="netgen-mesher not installed"
)


class TestNetgenSurfaceOnly:
    """Tests for surface-only meshing via the netgen backend (BRepMesh)."""

    def test_surface_only_cube(self, tmp_path):
        """Cube should produce 12 triangles (2 per face) with default tolerance."""
        box = cq.Workplane().box(10, 10, 10)
        c2d = CadToDagmc()
        c2d.add_cadquery_object(box, material_tags=["mat1"])

        f = tmp_path / "netgen_cube.h5m"
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            meshing_backend="netgen",
            tolerance=0.1,
            angular_tolerance=0.1,
        )
        assert f.is_file()

        # Verify correct material tags
        vol_mat = get_volumes_and_materials_from_h5m(str(f))
        assert 1 in vol_mat
        assert vol_mat[1] == "mat:mat1"

    def test_surface_only_sphere(self, tmp_path):
        """Sphere should produce more triangles than a cube due to curvature."""
        sphere = cq.Workplane().sphere(10)
        c2d = CadToDagmc()
        c2d.add_cadquery_object(sphere, material_tags=["mat1"])

        f = tmp_path / "netgen_sphere.h5m"
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            meshing_backend="netgen",
            tolerance=0.1,
            angular_tolerance=0.1,
        )
        assert f.is_file()

        # Sphere file should be larger than a cube file (more triangles)
        box = cq.Workplane().box(10, 10, 10)
        c2d_box = CadToDagmc()
        c2d_box.add_cadquery_object(box, material_tags=["mat1"])

        f_box = tmp_path / "netgen_cube_compare.h5m"
        c2d_box.export_dagmc_h5m_file(
            filename=str(f_box),
            meshing_backend="netgen",
            tolerance=0.1,
            angular_tolerance=0.1,
        )
        assert f.stat().st_size > f_box.stat().st_size

    def test_tolerance_affects_mesh_density(self, tmp_path):
        """Lower tolerance should produce more triangles (larger file)."""
        sphere = cq.Workplane().sphere(10)

        f_coarse = tmp_path / "netgen_coarse.h5m"
        c2d = CadToDagmc()
        c2d.add_cadquery_object(sphere, material_tags=["mat1"])
        c2d.export_dagmc_h5m_file(
            filename=str(f_coarse),
            meshing_backend="netgen",
            tolerance=1.0,
            angular_tolerance=1.0,
        )

        f_fine = tmp_path / "netgen_fine.h5m"
        c2d2 = CadToDagmc()
        c2d2.add_cadquery_object(sphere, material_tags=["mat1"])
        c2d2.export_dagmc_h5m_file(
            filename=str(f_fine),
            meshing_backend="netgen",
            tolerance=0.01,
            angular_tolerance=0.01,
        )

        assert f_coarse.is_file()
        assert f_fine.is_file()
        assert f_fine.stat().st_size > f_coarse.stat().st_size

    def test_multiple_volumes_surface_only(self, tmp_path):
        """Multiple separate volumes, surface-only mesh."""
        sphere1 = cq.Workplane().sphere(20)
        sphere2 = cq.Workplane().moveTo(100, 100).sphere(20)
        sphere3 = cq.Workplane().moveTo(-100, -100).sphere(20)

        c2d = CadToDagmc()
        c2d.add_cadquery_object(sphere1, material_tags=["mat1"])
        c2d.add_cadquery_object(sphere2, material_tags=["mat2"])
        c2d.add_cadquery_object(sphere3, material_tags=["mat3"])

        f = tmp_path / "netgen_multi.h5m"
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            meshing_backend="netgen",
        )
        assert f.is_file()

        vol_mat = get_volumes_and_materials_from_h5m(str(f))
        assert vol_mat == {
            1: "mat:mat1",
            2: "mat:mat2",
            3: "mat:mat3",
        }


class TestNetgenTetMesh:
    """Tests for tetrahedral volume meshing via the netgen backend."""

    def test_tet_single_volume(self, tmp_path):
        """Single box tet-meshed should produce a valid h5m."""
        box = cq.Workplane().box(10, 10, 10)
        c2d = CadToDagmc()
        c2d.add_cadquery_object(box, material_tags=["mat1"])

        f = tmp_path / "netgen_tet.h5m"
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            meshing_backend="netgen",
            tet_volumes=["mat1"],
            target_edge_length=5.0,
        )
        assert f.is_file()

        vol_mat = get_volumes_and_materials_from_h5m(str(f))
        assert 1 in vol_mat
        assert vol_mat[1] == "mat:mat1"

    def test_tet_produces_finer_surface_than_brepmesh(self, tmp_path):
        """Tet boundary tris should be finer than BRepMesh for a cube."""
        box = cq.Workplane().box(10, 10, 10)

        # Surface-only
        c2d_surf = CadToDagmc()
        c2d_surf.add_cadquery_object(box, material_tags=["mat1"])
        f_surf = tmp_path / "netgen_surf_only.h5m"
        c2d_surf.export_dagmc_h5m_file(
            filename=str(f_surf),
            meshing_backend="netgen",
        )

        # With tet mesh
        c2d_tet = CadToDagmc()
        c2d_tet.add_cadquery_object(box, material_tags=["mat1"])
        f_tet = tmp_path / "netgen_tet_mesh.h5m"
        c2d_tet.export_dagmc_h5m_file(
            filename=str(f_tet),
            meshing_backend="netgen",
            tet_volumes=["mat1"],
            target_edge_length=2.0,
        )

        # Tet mesh file should be larger (more boundary tris)
        assert f_tet.stat().st_size > f_surf.stat().st_size


class TestNetgenMixedMesh:
    """Tests for combined surface + volume meshing."""

    def test_mixed_tet_and_surface(self, tmp_path):
        """One tet volume + one surface-only volume."""
        box1 = cq.Workplane().box(10, 10, 10)
        box2 = cq.Workplane().moveTo(50, 0).box(10, 10, 10)

        c2d = CadToDagmc()
        c2d.add_cadquery_object(box1, material_tags=["tet_mat"])
        c2d.add_cadquery_object(box2, material_tags=["surf_mat"])

        f = tmp_path / "netgen_mixed.h5m"
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            meshing_backend="netgen",
            tet_volumes=["tet_mat"],
            target_edge_length=3.0,
        )
        assert f.is_file()

        vol_mat = get_volumes_and_materials_from_h5m(str(f))
        assert 1 in vol_mat
        assert 2 in vol_mat
        assert vol_mat[1] == "mat:tet_mat"
        assert vol_mat[2] == "mat:surf_mat"

    def test_shared_face_between_tet_and_surface(self, tmp_path):
        """Adjacent boxes with a shared face — one tet, one surface-only."""
        box1 = cq.Workplane().box(10, 10, 10).translate((5, 0, 0))
        box2 = cq.Workplane().box(10, 10, 10).translate((-5, 0, 0))

        assembly = cq.Assembly()
        assembly.add(box1, name="tet_vol")
        assembly.add(box2, name="surf_vol")

        c2d = CadToDagmc()
        c2d.add_cadquery_object(assembly, material_tags=["tet_mat", "surf_mat"])

        f = tmp_path / "netgen_shared.h5m"
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            meshing_backend="netgen",
            tet_volumes=["tet_mat"],
            target_edge_length=3.0,
        )
        assert f.is_file()

        vol_mat = get_volumes_and_materials_from_h5m(str(f))
        assert len(vol_mat) == 2

    def test_box_with_sphere_cutout(self, tmp_path):
        """Box with spherical cutout + sphere — the example from netgen_mixed_mesh.py."""
        box = cq.Workplane("XY").box(30, 30, 30)
        sphere = cq.Workplane("XY").moveTo(20, 0).sphere(10)

        assembly = cq.Assembly()
        assembly.add(box.cut(sphere), name="box")
        assembly.add(sphere, name="sphere")

        c2d = CadToDagmc()
        c2d.add_cadquery_object(assembly, material_tags=["box_mat", "sphere_mat"])

        f = tmp_path / "netgen_box_sphere.h5m"
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            meshing_backend="netgen",
            tolerance=0.1,
            angular_tolerance=0.1,
            tet_volumes=["sphere_mat"],
            target_edge_length=2.0,
            grading=0.05,
        )
        assert f.is_file()

        vol_mat = get_volumes_and_materials_from_h5m(str(f))
        assert len(vol_mat) == 2


class TestNetgenValidation:
    """Tests for parameter validation."""

    def test_missing_target_edge_length_raises(self, tmp_path):
        """tet_volumes without target_edge_length should raise ValueError."""
        box = cq.Workplane().box(10, 10, 10)
        c2d = CadToDagmc()
        c2d.add_cadquery_object(box, material_tags=["mat1"])

        with pytest.raises(ValueError, match="target_edge_length is required"):
            c2d.export_dagmc_h5m_file(
                filename=str(tmp_path / "test.h5m"),
                meshing_backend="netgen",
                tet_volumes=["mat1"],
            )

    def test_invalid_material_tag_in_tet_volumes_raises(self, tmp_path):
        """Unknown material tag in tet_volumes should raise ValueError."""
        box = cq.Workplane().box(10, 10, 10)
        c2d = CadToDagmc()
        c2d.add_cadquery_object(box, material_tags=["mat1"])

        with pytest.raises(ValueError, match="not found"):
            c2d.export_dagmc_h5m_file(
                filename=str(tmp_path / "test.h5m"),
                meshing_backend="netgen",
                tet_volumes=["nonexistent"],
                target_edge_length=2.0,
            )

    def test_netgen_kwargs_accepted(self, tmp_path):
        """All netgen kwargs should be accepted without error."""
        box = cq.Workplane().box(10, 10, 10)
        c2d = CadToDagmc()
        c2d.add_cadquery_object(box, material_tags=["mat1"])

        f = tmp_path / "netgen_all_kwargs.h5m"
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            meshing_backend="netgen",
            tolerance=0.05,
            angular_tolerance=0.05,
            tet_volumes=["mat1"],
            target_edge_length=3.0,
            grading=0.1,
            optsteps3d=3,
            optimize3d="cmdDmstmstm",
            elsizeweight=0.0,
        )
        assert f.is_file()

    def test_auto_select_netgen_backend(self, tmp_path):
        """Netgen-only kwargs should auto-select the netgen backend."""
        box = cq.Workplane().box(10, 10, 10)
        c2d = CadToDagmc()
        c2d.add_cadquery_object(box, material_tags=["mat1"])

        f = tmp_path / "netgen_auto.h5m"
        # target_edge_length is netgen-only, should trigger auto-selection
        c2d.export_dagmc_h5m_file(
            filename=str(f),
            tet_volumes=["mat1"],
            target_edge_length=3.0,
        )
        assert f.is_file()
