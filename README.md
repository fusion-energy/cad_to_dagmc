
[![N|Python](https://www.python.org/static/community_logos/python-powered-w-100x40.png)](https://www.python.org)

[![CI with install](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_install.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_install.yml)

[![Upload Python Package](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/python-publish.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/python-publish.yml)

[![PyPI](https://img.shields.io/pypi/v/cad_to_dagmc?color=brightgreen&label=pypi&logo=grebrightgreenen&logoColor=green)](https://pypi.org/project/cad_to_dagmc/)

___

A minimal package that uses CadQuery functionality to convert CAD geometry to [DAGMC](https://github.com/svalinn/DAGMC/) h5m files

This particular method of producing DAGMC compatible h5m files from CAD geometry
is intended to convert STP files or [CadQuery](https://cadquery.readthedocs.io) objects to h5m file.

One unique feature of this package is the ability to combine STP files with CadQuery objects.
This allows for the addition of parametric geometry to static geometry.

The resulting DAGMC geometry can then be used for simulations in [OpenMC](https://github.com/openmc-dev/openmc/) or [other supported codes](https://svalinn.github.io/DAGMC/).

# Installation prerequisite

In principle, any Conda/Mamba distribution will work. A few Conda/Mamba options are:
- [Mambaforge](https://github.com/conda-forge/miniforge#mambaforge)
- [Miniforge](https://github.com/conda-forge/miniforge#miniforge-pypy3)
- [Anaconda](https://www.anaconda.com/download)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)


# Install using Mamba and pip

This example assumes you have installed the MambaForge option or separately
installed Mamba with ```conda install -c conda-forge mamba -y```

Create a new conda environment, I've chosen Python 3.9 here but new versions are
also supported.
```bash
mamba create --name new_env python=3.9 -y
```

Activate the environment
```bash
mamba activate new_env
```

Install the dependencies
```bash
mamba install -c cadquery -c conda-forge moab gmsh python-gmsh cadquery=master -y
```

Then you can install the cad_to_dagmc package with ```pip```
```bash
pip install cad_to_dagmc
```

You may also want to install OpenMC with DAGMC to make use of the h5m geometry files produced in simulations. However you could also use other supported particle transport codes such as MCNP, FLUKA and others [link to DAGMC documentation](https://svalinn.github.io/DAGMC/).You can run ```conda install -c conda-forge openmc``` however this more specific command makes sure the latest version of OpenMC which contains DAGMC is chosen by conda / mamba
```bash
mamba install -c conda-forge -y "openmc=0.13.3=dagmc*nompi*"
```


# Install using Conda and pip

This example uses Conda to install some dependencies that are not available via PyPi.

Create a new conda environment
```bash
conda create --name new_env python=3.9 -y
```

Activate the environment
```bash
conda activate new_env
```

Install the dependencies
```bash
conda install -c cadquery -c conda-forge moab gmsh python-gmsh cadquery=master -y
```

Then you can install the cad_to_dagmc package with ```pip```
```bash
pip install cad_to_dagmc
```

You may also want to install OpenMC with DAGMC to make use of the h5m geometry files produced in simulations. However you could also use other supported particle transport codes such as MCNP, FLUKA and others [link to DAGMC documentation](https://svalinn.github.io/DAGMC/).You can run ```conda install -c conda-forge openmc``` however this more specific command makes sure the latest version of OpenMC which contains DAGMC is chosen by conda / mamba
```bash
conda install -c conda-forge -y "openmc=0.13.3=dagmc*nompi*"
```



# Usage - creation of DAGMC h5m files

For examples see the [examples folder](https://github.com/fusion-energy/cad_to_dagmc/tree/main/examples)

# Usage - simulation with transport code

For examples see the CAD tasks in the [neutronics-workshop](https://github.com/fusion-energy/neutronics-workshop)
