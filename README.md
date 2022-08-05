[![CI with install](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_install.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_install.yml)

Single volumes pass tests :heavy_check_mark:

Multiple non touching volumes pass tests :heavy_check_mark:

Multiple touching volumes FAIL tests :heavy_multiplication_x:

Assigning material tags to correct volumes NON EXISTENT tests :heavy_multiplication_x:

___

A minimal package that uses CadQuery functionality to convert Cad geometry to DAGMC h5m files

This particular method of producing DAGMC compatible h5m files from CAD geometry
is intended to convert STP files or [CadQuery](https://cadquery.readthedocs.io) objects to h5m file.

The use of CadQuery based surface tesselation and then conversion of the
vertices and triangle sets into h5m files directly (in memory) is relatively
fast with minimal file IO and the resulting meshed volumes have low triangle
count while maintaining a good representation of the volume as described in
[this](https://www.sciencedirect.com/science/article/abs/pii/S0920379615301484)
publication.

While this package concentrates on loading the CAD and meshing the surface it
then hands off the vertices and triangles sets to
[vertices_to_h5m](https://github.com/fusion-energy/vertices_to_h5m) which
converts these into a h5m geometry file.
Due to the modularity of this workflow if you have a preferred meshing
algorithm then it is entirely possible to pipe your own vertices and triangles
directly into vertices_to_h5m.

# Install

You will some dependencies installing (moab, pymoab and cadquery).

```bash
conda install -c conda-forge mamba
mamba install -c conda-forge moab
mamba install -c cadquery -c conda-forge cadquery=master
```

There you can install the ```cad_to_dagmc``` package

```bash
pip install cad_to_dagmc
```

To use the h5m geometry you will need a transport code with DAGMC enabled such as OpenMC.
Just to note that currently the conda install for CadQuery and OpenMC can't be installed in the same conda environment.
A work around for this is to create the h5m geometry in one conda environment and simulate with OpenMC in another conda environment.

# Usage

Produces a tagged h5m file for a STP file with a single part / volume

```python
import cad_to_dagmc

stp_file = cad_to_dagmc.load_stp_file("tests/single_cube.stp")
vertices, triangles = cad_to_dagmc.tessellate(stp_file, tolerance=2)

vertices_to_h5m(
    vertices=vertices,
    triangles=triangles,
    material_tags=["mat1"],
    h5m_filename="dagmc.h5m",
)
```

Produces a tagged h5m file for a STP file with a multiple part / volume

```python
import cad_to_dagmc

stp_file = cad_to_dagmc.load_stp_file("tests/multi_volume_cylinders.stp")
vertices, triangles = cad_to_dagmc.tessellate(stp_file, tolerance=2)

vertices_to_h5m(
    vertices=vertices,
    triangles=triangles,
    material_tags=["mat1", "mat2", "mat3", "mat4", "mat5", "mat6"],
    h5m_filename="dagmc.h5m",
)
````
