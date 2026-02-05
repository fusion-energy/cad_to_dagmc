"""Pytest configuration and fixtures for cad_to_dagmc tests."""

import os
import pytest


# Check if pymoab is available
try:
    import pymoab
    PYMOAB_AVAILABLE = True
except ImportError:
    PYMOAB_AVAILABLE = False

# Check if cadquery_direct_mesh_plugin is available
try:
    import cadquery_direct_mesh_plugin
    CADQUERY_DIRECT_MESHER_AVAILABLE = True
except ImportError:
    CADQUERY_DIRECT_MESHER_AVAILABLE = False


def pytest_addoption(parser):
    """Add command-line option for h5m backend."""
    parser.addoption(
        "--h5m-backend",
        action="store",
        default=os.environ.get("H5M_BACKEND", "h5py"),
        help="H5M backend to use: pymoab or h5py (default: h5py)",
    )


@pytest.fixture
def h5m_backend(request):
    """Fixture that returns the h5m backend to use for tests."""
    return request.config.getoption("--h5m-backend")


def pytest_collection_modifyitems(config, items):
    """Skip tests if required dependencies are not installed."""
    skip_pymoab = pytest.mark.skip(reason="pymoab not installed")
    skip_cadquery_mesher = pytest.mark.skip(reason="cadquery_direct_mesh_plugin not installed")

    for item in items:
        # Check if the test is parametrized
        if hasattr(item, "callspec") and item.callspec.params:
            params = item.callspec.params

            # Skip pymoab backend tests if pymoab is not installed
            if not PYMOAB_AVAILABLE:
                if params.get("method") == "pymoab" or params.get("h5m_backend") == "pymoab":
                    item.add_marker(skip_pymoab)

            # Skip cadquery meshing backend tests if cadquery_direct_mesh_plugin is not installed
            if not CADQUERY_DIRECT_MESHER_AVAILABLE:
                if params.get("meshing_backend") == "cadquery":
                    item.add_marker(skip_cadquery_mesher)
