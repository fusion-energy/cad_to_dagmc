
[![N|Python](https://www.python.org/static/community_logos/python-powered-w-100x40.png)](https://www.python.org)

[![CI with Conda install](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_conda_install.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_conda_install.yml) Testing package and running examples with dependencies installed via Conda

[![CI with pip install](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_pip_install.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_pip_install.yml) Testing package and running examples with dependencies installed vua PIP

[![CI with model benchmark zoo](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_benchmarks.yml/badge.svg?branch=main)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_benchmarks.yml) Testing with [Model Benchmark Zoo](https://github.com/fusion-energy/model_benchmark_zoo)

[![Upload Python Package](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/python-publish.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/python-publish.yml)

[![PyPI](https://img.shields.io/pypi/v/cad_to_dagmc?color=brightgreen&label=pypi&logo=grebrightgreenen&logoColor=green)](https://pypi.org/project/cad_to_dagmc/)


A minimal package that converts CAD geometry to [DAGMC](https://github.com/svalinn/DAGMC/) h5m files

cad-to-dagmc can create:
- surface meshes / faceted geometry / triangular meshes
- unstructured mesh / tetrahedral meshes / volume meshes

cad-to-dagmc can convert:
- STEP files
- CadQuery objects (in memory)

cad-to-dagmc aims to produce DAGMC compatible h5m files from CAD geometry is intended to convert [STEP](http://www.steptools.com/stds/step/) files or [CadQuery](https://cadquery.readthedocs.io) objects to a [DAGMC](https://github.com/svalinn/DAGMC/) compatible h5m file.

The resulting DAGMC geometry can then be used for simulations in [OpenMC](https://github.com/openmc-dev/openmc/) or [other supported codes](https://svalinn.github.io/DAGMC/).

This package is tested with [pytest tests](https://github.com/fusion-energy/cad_to_dagmc/tree/main/tests) and also the DAGMC geometry made with this package is compared to simulation carried out with native constructive solid geometry, see [Model Benchmark Zoo](https://github.com/fusion-energy/model_benchmark_zoo) for more details.

Also checkout these other software projects that also create DAGMC geometry [CAD-to-OpenMC](https://github.com/openmsr/CAD_to_OpenMC), [Stellarmesh](https://github.com/Thea-Energy/stellarmesh) and [Coreform Cubit](https://coreform.com/products/coreform-cubit/)

# Installation options

- Install using Mamba
- Install using Conda
- Install using pip and source compilations

## Install using Mamba

In principle, installing any Conda/Mamba distribution will work. A few Conda/Mamba options are:
- [Miniforge](https://github.com/conda-forge/miniforge) (recommended as it includes mamba)
- [Anaconda](https://www.anaconda.com/download)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

This example assumes you have installed the Miniforge option or separately have installed Mamba with ```conda install -c conda-forge mamba -y```

Create a new environment, I've chosen Python 3.10 here but newer versions are
also supported.
```bash
mamba create --name new_env python=3.10 -y
```

Activate the environment
```bash
mamba activate new_env
```

Then you can install the cad_to_dagmc package
```bash
mamba install -y -c conda-forge cad_to_dagmc
```

## Install using Conda

In principle, installing any Conda/Mamba distribution will work. A few Conda/Mamba options are:
- [Miniforge](https://github.com/conda-forge/miniforge) (recommended as it includes mamba)
- [Anaconda](https://www.anaconda.com/download)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

Create a new environment, I've chosen Python 3.10 here but newer versions are
also supported.
```bash
conda create --name new_env python=3.10 -y
```

Activate the environment
```bash
conda activate new_env
```

Then you can install the cad_to_dagmc package
```bash
conda install -y -c conda-forge cad_to_dagmc
```

## Install using pip and source compilations

It is also possible to avoid the use of conda/mamba and installing using pip.

First ensure hdf5 is installed as this is needed by MOAB pip install command

```
sudo apt-get install libhdf5-dev
```

Then clone the latest version of MOAB and cd into the moab directory.

```
git clone  master https://bitbucket.org/fathomteam/moab/
cd moab
```

Ensure pip is up to date as a new version is needed
```
python -m pip install --upgrade pip
```

Run the pip install command with cmake arguments.
```
pip install . --config-settings=cmake.args=-DENABLE_HDF5=ON
```

Then you can install the cad_to_dagmc package with ```pip```

```bash
pip install cad_to_dagmc
```

## Install with OpenMC or other particle transport codes

You may also want to install OpenMC with DAGMC to make use of the h5m geometry files produced in simulations. However you could also use other supported particle transport codes such as MCNP, FLUKA and others [link to DAGMC documentation](https://svalinn.github.io/DAGMC/).

To install OpenMC you can run ```mamba install -c conda-forge openmc``` however this more specific command makes sure the latest version of OpenMC which contains DAGMC is chosen by conda / mamba
```bash
mamba install -c conda-forge -y "openmc=0.14.0=dagmc*nompi*"
```

It might not be possible to install OpenMC and cad-to-dagmc in the same conda/mamba python environment so you may have to create a new conda/mamba environment and install OpenMC there.

Another option would be to [install OpenMC from source](https://docs.openmc.org/en/stable/quickinstall.html) which would also need compiling with MOAB and DAGMC options.


# Known incompatibilities

The package requires newer versions of Linux. For example the package does not work on Ubuntu 18.04 or older.

The package requires newer versions of pip. It is recommended to ensure that your version of pip is up to date. This can be done with ```python -m pip install --upgrade pip```

Installing one of the package dependancies (gmsh) with pip appears to result in errors when passing cad objects in memory between cadquery / ocp and gmsh. The default method of passing cad objects is via file so this should not impact most users. The conda install gmsh appears to work fine with in memory passing of cad objects as the version of OCP matches between Gmsh and CadQuery.


# Usage - creation of DAGMC h5m files

For examples see the [examples folder](https://github.com/fusion-energy/cad_to_dagmc/tree/main/examples)

# Usage - simulation with transport code

For examples see the [examples folder](https://github.com/fusion-energy/cad_to_dagmc/tree/main/examples)

For more examples see the CAD tasks in the [neutronics-workshop](https://github.com/fusion-energy/neutronics-workshop) and [model benchmark zoo](https://github.com/fusion-energy/model_benchmark_zoo)
