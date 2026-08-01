# CAD to DAGMC

A package that converts CAD geometry to [DAGMC](https://github.com/svalinn/DAGMC/) h5m files,
[unstructured mesh](https://docs.openmc.org/en/latest/pythonapi/generated/openmc.UnstructuredMesh.html) files (VTK),
and Gmsh (msh) files ready for use in neutronics simulations.

## Workflow

CAD geometry is given a material tag per volume, meshed by one of three
backends, then written out. The DAGMC h5m file is written by the h5py or pymoab
writer, while the unstructured mesh vtk and GMSH msh files are written by the
meshing backend itself. A GMSH mesh is already meshed, so it converts straight
to a DAGMC h5m file.

```{image} _static/workflow_light.png
:alt: CadQuery objects and STEP files are given material tags, then meshed by the cad-to-dagmc-mesher, gmsh or cadquery backend. All three write DAGMC h5m files through the h5py or pymoab writer. The cad-to-dagmc-mesher and gmsh backends also write tetrahedra to unstructured mesh vtk files, and gmsh also writes GMSH msh files. A GMSH mesh input skips the meshing stage and goes straight to an h5m writer.
:class: only-light
:width: 100%
```

```{image} _static/workflow_dark.png
:alt: CadQuery objects and STEP files are given material tags, then meshed by the cad-to-dagmc-mesher, gmsh or cadquery backend. All three write DAGMC h5m files through the h5py or pymoab writer. The cad-to-dagmc-mesher and gmsh backends also write tetrahedra to unstructured mesh vtk files, and gmsh also writes GMSH msh files. A GMSH mesh input skips the meshing stage and goes straight to an h5m writer.
:class: only-dark
:width: 100%
```

## Key Features

| | |
|---|---|
| **Multiple Input Formats** | **Flexible Material Tagging** |
| - CadQuery objects<br>- STEP files<br>- GMSH mesh files | - Manual tags<br>- Assembly names<br>- CadQuery Materials<br>- GMSH physical groups |
| **Three Meshing Backends** | **Multiple Output Formats** |
| - GMSH (full control, volume meshing)<br>- CadQuery (simpler, direct)<br>- cad-to-dagmc-mesher (surface and volume meshing) | - DAGMC h5m (surface mesh)<br>- Unstructured VTK (volume mesh)<br>- GMSH files |
| **Two H5M Backends** | **Advanced Options** |
| - h5py (default, no MOAB needed)<br>- pymoab (official MOAB) | - Per-volume mesh sizing<br>- Geometry scaling<br>- Parallel meshing |


```{toctree}
:maxdepth: 2
:caption: Getting Started

installation
quickstart
```

```{toctree}
:maxdepth: 2
:caption: Inputs

inputs/index
inputs/cadquery_objects
inputs/cadquery_assemblies
inputs/step_files
inputs/gmsh_files
```

```{toctree}
:maxdepth: 2
:caption: Material Tagging

material_tagging/index
material_tagging/manual_tags
material_tagging/assembly_names
material_tagging/assembly_materials
material_tagging/gmsh_physical_groups
```

```{toctree}
:maxdepth: 2
:caption: Outputs

outputs/index
outputs/dagmc_h5m
outputs/unstructured_vtk
outputs/gmsh_mesh
outputs/conformal_meshes
```

```{toctree}
:maxdepth: 2
:caption: Meshing

meshing/index
meshing/gmsh_backend
meshing/cadquery_backend
meshing/cad_to_dagmc_mesher_backend
meshing/mesh_sizing
```

```{toctree}
:maxdepth: 2
:caption: Advanced

advanced/index
advanced/geometry_scaling
advanced/imprinting
advanced/implicit_complement
advanced/parallel_processing
advanced/h5m_backends
```

```{toctree}
:maxdepth: 2
:caption: Reference

api
```
