
[![N|Python](https://www.python.org/static/community_logos/python-powered-w-100x40.png)](https://www.python.org)

[![CI with install](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_install.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_install.yml)

[![Upload Python Package](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/python-publish.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/python-publish.yml)


[![PyPI](https://img.shields.io/pypi/v/cad_to_dagmc?color=brightgreen&label=pypi&logo=grebrightgreenen&logoColor=green)](https://pypi.org/project/cad_to_dagmc/)

___

A minimal package that uses CadQuery functionality to convert Cad geometry to [DAGMC](https://github.com/svalinn/DAGMC/) h5m files

This particular method of producing DAGMC compatible h5m files from CAD geometry
is intended to convert STP files or [CadQuery](https://cadquery.readthedocs.io) objects to h5m file.

One unique feature of this package is the ability to combine STP files with CadQuery objects.
This allows for the addition of parametric geometry to static geometry.

# Install (Conda)

Creates a new empty Conda environment and activate it
```bash
conda create --name new_env python=3.9
conda activate new_env
```

Installs cad_to_dagmc and dependencies
```bash
conda install -c fusion-energy -c cadquery -c conda-forge cad_to_dagmc
```
TODO move to conda-forge ~conda install -c conda-forge cad_to_dagmc~
# Install (Mamba)

Creates a new empty Conda environment and activate it
```bash
conda create --name new_env python=3.9
conda activate new_env
```

Installs Mamba
```bash
conda install -c conda-forge mamba
```

Installs cad_to_dagmc and dependencies
```bash
mamba install -c fusion-energy -c cadquery -c conda-forge cad_to_dagmc
```
TODO move to conda-forge ~mamba install -c conda-forge cad_to_dagmc~

# Install (Conda + pip)

You will need to install some dependencies that are not available via PyPi.
This example uses Conda but Mamba could also be used.
```bash
conda install -c conda-forge cadquery=2.2.0 occt=7.7.0 moab gmsh python-gmsh
```

Then you can install the cad_to_dagmc package with ```pip```

```bash
pip install cad_to_dagmc
```

# Usage

To use the h5m geometry you will need a transport code with DAGMC enabled such as OpenMC.
Just to note that currently the conda install for CadQuery and OpenMC can't be installed in the same conda environment.
A work around for this is to create the h5m geometry in one conda environment and simulate with OpenMC in another conda environment.

For examples see the [examples folder](https://github.com/fusion-energy/cad_to_dagmc/tree/main/examples)
