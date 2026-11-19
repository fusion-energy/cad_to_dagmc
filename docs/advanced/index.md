# Advanced Options

Two of these pages apply to most imported CAD:
[Geometry Scaling](geometry_scaling.md), because CadQuery reads STEP files in
millimetres, and [Checking for Overlaps](overlaps.md), for CAD you have not
checked yourself.

## Topics

| Topic | Description |
|-------|-------------|
| [Geometry Scaling](geometry_scaling.md) | Unit conversion with `scale_factor`, and the units of mesh sizes |
| [Imprinting](imprinting.md) | Shared surfaces between touching solids |
| [Checking for Overlaps](overlaps.md) | Finding solids that occupy the same space |
| [Implicit Complement](implicit_complement.md) | Material for the space between volumes |
| [Parallel Processing](parallel_processing.md) | Thread counts and peak RAM |
| [h5m Backends](h5m_backends.md) | Writing the h5m file with h5py or pymoab |

## Quick Reference

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    scale_factor=0.1,                        # mm to cm
    imprint="partial",                       # the default glue mode
    implicit_complement_material_tag="air",  # material between and around the volumes
    h5m_backend="h5py",                      # the default h5m backend
)
```

| Option | When to use it |
|--------|----------------|
| `scale_factor` | The CAD is in different units from the simulation |
| `imprint=False` | Solids that do not touch (this also skips the overlap checks that come with the imprint). A single solid is never imprinted anyway. |
| `imprint=False` with a BREP | Geometry you [imprinted yourself](imprinting.md#meshing-geometry-you-imprinted-yourself) |
| `imprint_threads=1` | Imprinting runs out of RAM on a large model |
| `mesh_threads=4` | cad-to-dagmc-mesher meshing runs out of RAM on a large model |
| `implicit_complement_material_tag` | The space between and around the volumes is not vacuum (air, water) |
| `h5m_backend="pymoab"` | Write the file with MOAB's own library (needs pymoab) |
| `method="in memory"` | Large geometry on the Gmsh backend, when Gmsh and CadQuery use the same OpenCASCADE version. Passing `method` selects the Gmsh backend. |
