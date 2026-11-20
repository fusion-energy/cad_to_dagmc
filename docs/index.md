# CAD to DAGMC

A package that converts CAD geometry to [DAGMC](https://github.com/svalinn/DAGMC/) h5m files,
[unstructured mesh](https://docs.openmc.org/en/latest/pythonapi/generated/openmc.UnstructuredMesh.html) files (VTK),
and Gmsh mesh files (`.msh`) ready for use in neutronics simulations.

## Workflow

Each solid gets a material tag. A meshing backend, cad-to-dagmc-mesher (the
default) or Gmsh, meshes the geometry. An h5m backend, h5py (the default) or
pymoab, then writes the surface mesh to a DAGMC h5m file. Either meshing backend
can also make a volume mesh of tetrahedra, written as a VTK file, and Gmsh can
save its own `.msh` file. A Gmsh mesh you already have skips the meshing stage.

One `export_dagmc_h5m_file()` call can write the h5m file and the VTK file
together, so that the tetrahedra share their boundary with the h5m surfaces; see
[Conformal Meshes](outputs/conformal_meshes.md).

```{image} _static/workflow_light.png
:alt: CadQuery objects and STEP files are given material tags, then meshed by the cad-to-dagmc-mesher or Gmsh backend. Both write DAGMC h5m files through the h5py or pymoab h5m backend. Both meshing backends also write volume meshes of tetrahedra to VTK files, and Gmsh also writes Gmsh .msh files. The DAGMC geometry output names both files export_dagmc_h5m_file can write, the dagmc.h5m on its own or with a conformal umesh.vtk. A Gmsh mesh, from a file or the gmsh session, takes its tags from physical groups or a list, skips the meshing stage and goes straight to an h5m backend.
:class: only-light
:width: 100%
```

```{image} _static/workflow_dark.png
:alt: CadQuery objects and STEP files are given material tags, then meshed by the cad-to-dagmc-mesher or Gmsh backend. Both write DAGMC h5m files through the h5py or pymoab h5m backend. Both meshing backends also write volume meshes of tetrahedra to VTK files, and Gmsh also writes Gmsh .msh files. The DAGMC geometry output names both files export_dagmc_h5m_file can write, the dagmc.h5m on its own or with a conformal umesh.vtk. A Gmsh mesh, from a file or the gmsh session, takes its tags from physical groups or a list, skips the meshing stage and goes straight to an h5m backend.
:class: only-dark
:width: 100%
```

## Features

- [Inputs](inputs/index.md): CadQuery objects and assemblies, STEP files, and
  Gmsh meshes from a `.msh` file or the current gmsh session.
- [Material tagging](material_tagging/index.md): a list of tags, assembly part
  names, `cq.Material`, or Gmsh physical groups.
- [Meshing](meshing/index.md): cad-to-dagmc-mesher, the default, makes
  curvature-adaptive surface meshes and tetrahedra. Gmsh has per-volume sizing
  and several meshing algorithms.
- [Outputs](outputs/index.md): a DAGMC h5m surface mesh, a VTK volume mesh, a
  conformal h5m and VTK pair from one call, and Gmsh `.msh` files.
- [h5m backends](advanced/h5m_backends.md): h5py (the default, which needs no
  MOAB) or pymoab.
- [Advanced options](advanced/index.md): unit scaling, imprinting, overlap
  checking, implicit complement material, and thread and RAM limits.


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
:caption: Meshing

meshing/index
meshing/cad_to_dagmc_mesher_backend
meshing/gmsh_backend
meshing/mesh_sizing
```

```{toctree}
:maxdepth: 2
:caption: Outputs

outputs/index
outputs/dagmc_h5m
outputs/unstructured_vtk
outputs/conformal_meshes
outputs/gmsh_mesh
```

```{toctree}
:maxdepth: 2
:caption: Advanced

advanced/index
advanced/geometry_scaling
advanced/imprinting
advanced/overlaps
advanced/implicit_complement
advanced/parallel_processing
advanced/h5m_backends
```

```{toctree}
:maxdepth: 2
:caption: Reference

api
```
