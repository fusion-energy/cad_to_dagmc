"""Regression tests for issue #187.

CadToDagmc used the gmsh global singleton without finalizing it on the
surface-mesh export path, so repeated calls accumulated gmsh models in the
session. These tests assert that the gmsh session is properly cleaned up.
"""

import cadquery as cq
import gmsh
import pytest

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import init_gmsh


def _sphere_model(radius):
    model = CadToDagmc()
    model.add_cadquery_object(
        cadquery_object=cq.Workplane().sphere(radius),
        material_tags=["mat_steel"],
    )
    return model


def test_gmsh_surface_export_does_not_leak_session(tmp_path):
    """Repeatedly exporting a surface mesh with the gmsh backend must not
    leave the gmsh session initialized nor accumulate gmsh models."""
    for i in range(4):
        model = _sphere_model(5.0 + i)
        model.export_dagmc_h5m_file(
            filename=str(tmp_path / f"geom_{i}.h5m"),
            min_mesh_size=2.0,
            max_mesh_size=10.0,
            mesh_algorithm=1,
        )
        # The export must finalize the gmsh session it opened, so nothing is
        # left alive between calls.
        assert not gmsh.isInitialized()


def test_gmsh_unstructured_export_does_not_leak_session(tmp_path):
    """The unstructured-volume export path must also finalize gmsh."""
    model = _sphere_model(5.0)
    model.export_dagmc_h5m_file(
        filename=str(tmp_path / "geom.h5m"),
        umesh_filename=str(tmp_path / "umesh.vtk"),
        min_mesh_size=2.0,
        max_mesh_size=10.0,
        unstructured_volumes=[1],
    )
    assert not gmsh.isInitialized()


def test_gmsh_export_finalizes_on_meshing_error(tmp_path, monkeypatch):
    """If gmsh meshing raises part way through, the session must still be
    finalized within the same call (not left open until the next init_gmsh)."""
    model = _sphere_model(5.0)

    def boom(*args, **kwargs):
        raise RuntimeError("simulated meshing failure")

    # Make 2D surface mesh generation fail after the gmsh session has been
    # initialized by init_gmsh().
    monkeypatch.setattr("gmsh.model.mesh.generate", boom)

    with pytest.raises(RuntimeError, match="simulated meshing failure"):
        model.export_dagmc_h5m_file(
            filename=str(tmp_path / "geom.h5m"),
            min_mesh_size=2.0,
            max_mesh_size=10.0,
        )

    # The failed export must not leave the gmsh session initialized.
    assert not gmsh.isInitialized()


def test_gmsh_export_propagates_error_raised_before_session_starts(
    tmp_path, monkeypatch
):
    """If the gmsh path fails before init_gmsh() runs (e.g. imprinting fails),
    the original error must propagate. The finally must not mask it with an
    UnboundLocalError from touching the function-local gmsh name before it is
    bound."""
    model = _sphere_model(5.0)

    def boom():
        raise RuntimeError("failure before gmsh session starts")

    # init_gmsh() is the first statement in the gmsh path that binds the local
    # gmsh name; failing here leaves it unbound when the finally runs.
    monkeypatch.setattr("cad_to_dagmc.core.init_gmsh", boom)

    with pytest.raises(RuntimeError, match="failure before gmsh session starts"):
        model.export_dagmc_h5m_file(
            filename=str(tmp_path / "geom.h5m"),
            min_mesh_size=2.0,
            max_mesh_size=10.0,
        )


def test_init_gmsh_clears_leaked_session():
    """init_gmsh must start from a clean session even if gmsh was already
    initialized with stale models (self-healing against leaked sessions)."""
    # Simulate a leaked session containing multiple stale models.
    if gmsh.isInitialized():
        gmsh.finalize()
    gmsh.initialize()
    gmsh.model.add("stale_model_a")
    gmsh.model.add("stale_model_b")
    assert "stale_model_a" in gmsh.model.list()

    try:
        init_gmsh()
        models = gmsh.model.list()
        # The stale models from the leaked session must have been cleared.
        assert "stale_model_a" not in models
        assert "stale_model_b" not in models
        # A fresh session holds only gmsh's default unnamed model plus the
        # single model init_gmsh adds (which becomes the current one). The
        # count must not have grown by piling onto the leaked session.
        assert len(models) == 2
        assert gmsh.model.getCurrent().startswith("made_with_cad_to_dagmc_package")
    finally:
        if gmsh.isInitialized():
            gmsh.finalize()
