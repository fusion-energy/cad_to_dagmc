"""Pytest configuration and fixtures for cad_to_dagmc tests."""

import os
import pytest


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
