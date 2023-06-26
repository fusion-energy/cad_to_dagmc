
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

# Install (Conda + pip)

You will need to install some dependencies that are not available via PyPi.
This example uses Conda but Mamba could also be used.
Create a new conda environment
```bash
conda create --name cad-to-dagmc python=3.9 -y
```

Activate the environment
```bash
conda activate cad-to-dagmc
```

Install the dependencies
```bash
conda install -c cadquery -c conda-forge cadquery=master moab gmsh python-gmsh
```

Then you can install the cad_to_dagmc package with ```pip```
```bash
pip install cad_to_dagmc
```

# Usage - creation of DAGMC h5m files

For examples see the [examples folder](https://github.com/fusion-energy/cad_to_dagmc/tree/main/examples)

# Usage - simulation with transport code

For examples see the CAD tasks in the [neutronics-workshop](https://github.com/fusion-energy/neutronics-workshop)
