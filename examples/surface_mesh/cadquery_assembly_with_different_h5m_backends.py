"""Example demonstrating the use of different h5m file writing backends.

This example creates the same geometry and exports it using both available
h5m backends: 'pymoab' and 'h5py'.

The pymoab backend uses the PyMOAB library (Python bindings to MOAB) to write
the h5m file. This is the traditional approach and requires MOAB to be installed.

The h5py backend writes the h5m file directly using h5py, without requiring
MOAB/PyMOAB. This can be useful when MOAB is difficult to install or when
you want to avoid the MOAB dependency.

Both backends produce DAGMC-compatible h5m files that can be used for
neutronics simulations with codes like OpenMC.
"""

import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create a simple assembly with two spheres
sphere1 = cq.Workplane().sphere(5)
sphere2 = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere1)
assembly.add(sphere2)

# Create the model
my_model = CadToDagmc()
my_model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1", "mat2"])

# Export using the pymoab backend (default)
# This requires PyMOAB to be installed
my_model.export_dagmc_h5m_file(
    filename="dagmc_pymoab.h5m",
    h5m_backend="pymoab",
)
print("Created dagmc_pymoab.h5m using pymoab backend")

# Export using the h5py backend
# This only requires h5py (no MOAB/PyMOAB needed)
my_model.export_dagmc_h5m_file(
    filename="dagmc_h5py.h5m",
    h5m_backend="h5py",
)
print("Created dagmc_h5py.h5m using h5py backend")

# Both files are DAGMC-compatible and can be used interchangeably
# in neutronics simulations
