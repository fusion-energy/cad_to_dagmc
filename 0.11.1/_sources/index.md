# CAD to DAGMC

A package that converts CAD geometry to [DAGMC](https://github.com/svalinn/DAGMC/) h5m files,
[unstructured mesh](https://docs.openmc.org/en/latest/pythonapi/generated/openmc.UnstructuredMesh.html) files (VTK),
and Gmsh (msh) files ready for use in neutronics simulations.

## Workflow

```{mermaid}
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '13px', 'fontFamily': 'Inter, system-ui, sans-serif'}, 'flowchart': { 'curve': 'monotoneX', 'padding': 30, 'nodeSpacing': 40, 'rankSpacing': 60, 'htmlLabels': true }}}%%
flowchart LR
    subgraph inputs [" "]
        direction TB
        CQ(["  CadQuery  "])
        STEP(["  STEP files  "])
        GMSH_IN(["  GMSH mesh  "])
        CQ ~~~ STEP ~~~ GMSH_IN
    end

    subgraph tagging [" "]
        TAG{"  Material  <br/>  Tagging  "}
    end

    subgraph meshing [" "]
        direction TB
        GMSH_E["  GMSH  "]
        CQ_E["  CadQuery  "]
    end

    subgraph h5m_backend [" "]
        direction TB
        H5PY(("  h5py  "))
        MOAB(("  pymoab  "))
    end

    subgraph outputs [" "]
        direction TB
        H5M[["  DAGMC h5m  "]]
        VTK[["  Unstructured VTK  "]]
        MSH[["  GMSH mesh  "]]
    end

    CQ & STEP & GMSH_IN --> TAG

    TAG --> GMSH_E & CQ_E

    GMSH_E & CQ_E --> H5PY & MOAB
    H5PY & MOAB --> H5M

    GMSH_E --> VTK & MSH

    style inputs fill:none,stroke:none
    style tagging fill:none,stroke:none
    style meshing fill:none,stroke:none
    style outputs fill:none,stroke:none
    style h5m_backend fill:none,stroke:none

    style CQ fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0c4a6e
    style STEP fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0c4a6e
    style GMSH_IN fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0c4a6e

    style TAG fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f

    style GMSH_E fill:#f3e8ff,stroke:#9333ea,stroke-width:1.5px,color:#581c87
    style CQ_E fill:#f3e8ff,stroke:#9333ea,stroke-width:1.5px,color:#581c87

    style H5PY fill:#fce7f3,stroke:#db2777,stroke-width:1.5px,color:#831843
    style MOAB fill:#fce7f3,stroke:#db2777,stroke-width:1.5px,color:#831843

    style H5M fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
    style VTK fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
    style MSH fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
```

<p style="text-align: center; margin-top: 0.5em; margin-bottom: 2em;">
<span style="display: inline-block; padding: 4px 12px; margin: 4px; background: #e0f2fe; border-radius: 4px; font-size: 0.85em;">Inputs</span>
<span style="display: inline-block; padding: 4px 12px; margin: 4px; background: #fef3c7; border-radius: 4px; font-size: 0.85em;">Tagging</span>
<span style="display: inline-block; padding: 4px 12px; margin: 4px; background: #f3e8ff; border-radius: 4px; font-size: 0.85em;">Meshing</span>
<span style="display: inline-block; padding: 4px 12px; margin: 4px; background: #fce7f3; border-radius: 4px; font-size: 0.85em;">H5M Backend</span>
<span style="display: inline-block; padding: 4px 12px; margin: 4px; background: #dcfce7; border-radius: 4px; font-size: 0.85em;">Outputs</span>
</p>

## Key Features

| | |
|---|---|
| **Multiple Input Formats** | **Flexible Material Tagging** |
| - CadQuery objects<br>- STEP files<br>- GMSH mesh files | - Manual tags<br>- Assembly names<br>- CadQuery Materials<br>- GMSH physical groups |
| **Two Meshing Backends** | **Multiple Output Formats** |
| - GMSH (full control, volume meshing)<br>- CadQuery (simpler, direct) | - DAGMC h5m (surface mesh)<br>- Unstructured VTK (volume mesh)<br>- GMSH files |
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
