"""Reset OpenMC auto IDs before each benchmark test.

The benchmark zoo gives the DAGMC bounding cell and surfaces fixed IDs, which
would otherwise collide across parametrised runs in the same process.
"""


def pytest_runtest_setup(item):
    import openmc

    openmc.reset_auto_ids()
