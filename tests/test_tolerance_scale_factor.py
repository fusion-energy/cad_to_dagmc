import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc


class _StopAfterCapture(Exception):
    """Raised by the toMesh stub once the arguments have been recorded."""


def _capture_cadquery_tolerance(monkeypatch, scale_factor, **kwargs):
    """Return the tolerance that reaches CadQuery's toMesh.

    The cadquery backend tessellates the unscaled geometry and scales the
    resulting vertices, so cad_to_dagmc has to convert the caller's
    scaled-geometry tolerance before handing it over. Capture that value
    rather than meshing, which keeps the test fast and exact.
    """
    import cadquery_direct_mesh_plugin  # noqa: F401  registers Assembly.toMesh

    captured = {}

    def fake_to_mesh(self, **to_mesh_kwargs):
        captured.update(to_mesh_kwargs)
        raise _StopAfterCapture

    monkeypatch.setattr(cq.Assembly, "toMesh", fake_to_mesh)

    model = CadToDagmc()
    model.add_cadquery_object(cq.Workplane().sphere(1), material_tags=["mat1"])

    with pytest.raises(_StopAfterCapture):
        model.export_dagmc_h5m_file(
            filename="unused.h5m",
            meshing_backend="cadquery",
            scale_factor=scale_factor,
            **kwargs,
        )
    return captured


@pytest.mark.parametrize("scale_factor", [2.0, 100.0])
def test_cadquery_tolerance_is_in_scaled_units(monkeypatch, scale_factor):
    """tolerance is divided by scale_factor for the cadquery backend.

    Without this the same tolerance means a scale_factor times coarser mesh on
    the cadquery backend than on gmsh/cad-to-dagmc-mesher, which scale the
    geometry before meshing it.
    """
    with pytest.warns(UserWarning, match="units of the scaled geometry"):
        captured = _capture_cadquery_tolerance(
            monkeypatch, scale_factor, tolerance=0.5
        )

    assert captured["tolerance"] == pytest.approx(0.5 / scale_factor)
    # the geometry itself is still scaled by the plugin, unchanged
    assert captured["scale_factor"] == scale_factor


def test_cadquery_tolerance_unchanged_without_scaling(monkeypatch):
    """scale_factor=1.0 passes the tolerance straight through and does not warn."""
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        captured = _capture_cadquery_tolerance(monkeypatch, 1.0, tolerance=0.5)

    assert captured["tolerance"] == pytest.approx(0.5)


def test_cadquery_default_tolerance_is_scaled(monkeypatch):
    """The 0.1 default is in scaled units too, so it is converted as well."""
    with pytest.warns(UserWarning, match="units of the scaled geometry"):
        captured = _capture_cadquery_tolerance(monkeypatch, 100.0)

    assert captured["tolerance"] == pytest.approx(0.1 / 100.0)


def test_angular_tolerance_is_not_scaled(monkeypatch):
    """angular_tolerance is an angle, so scale_factor must not touch it."""
    with pytest.warns(UserWarning):
        captured = _capture_cadquery_tolerance(
            monkeypatch, 100.0, tolerance=0.5, angular_tolerance=0.3
        )

    assert captured["angular_tolerance"] == pytest.approx(0.3)
