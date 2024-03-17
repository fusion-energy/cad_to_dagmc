
[![N|Python](https://www.python.org/static/community_logos/python-powered-w-100x40.png)](https://www.python.org)

[![CI with install](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_install.yml/badge.svg?branch=main)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_install.yml) Testing package and running examples

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

- Install using Mamba and minimal pip
- Install using Conda and minimal pip
- Install using pip and source compilations
- Install using Conda and maximum pip  TODO
- Install using Mamba and maximum pip  TODO


## Install using Mamba and pip

In principle, installing any Conda/Mamba distribution will work. A few Conda/Mamba options are:
- [Miniforge](https://github.com/conda-forge/miniforge) (recommended as it includes mamba)
- [Anaconda](https://www.anaconda.com/download)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

This example assumes you have installed the Miniforge option or separately have installed Mamba with ```conda install -c conda-forge mamba -y```

Create a new conda environment, I've chosen Python 3.10 here but newer versions are
also supported.
```bash
mamba create --name new_env python=3.10 -y
```

Activate the environment
```bash
mamba activate new_env
```

Install the dependencies
```bash
mamba install -y -c conda-forge gmsh python-gmsh moab>=5.3.0 ocp>=7.7.2.0 cadquery>=2.4.0
```

Then you can install the cad_to_dagmc package with ```pip```
```bash
pip install cad_to_dagmc
```

You may also want to install OpenMC with DAGMC to make use of the h5m geometry files produced in simulations. However you could also use other supported particle transport codes such as MCNP, FLUKA and others [link to DAGMC documentation](https://svalinn.github.io/DAGMC/).

To install OpenMC You can run ```mamba install -c conda-forge openmc``` however this more specific command makes sure the latest version of OpenMC which contains DAGMC is chosen by conda / mamba
```bash
mamba install -c conda-forge -y "openmc=0.14.0=dagmc*nompi*"
```

It might not be possible to install OpenMC and cad-to-dagmc in the same conda/mamba python environment so you may have to create a new conda/mamba environment and install OpenMC there.

Another option would be to [install OpenMC from source](https://docs.openmc.org/en/stable/quickinstall.html) which would also need compiling with MOAB and DAGMC options. 


## Install using Conda and pip

In principle, installing any Conda/Mamba distribution will work. A few Conda/Mamba options are:
- [Miniforge](https://github.com/conda-forge/miniforge) (recommended as it includes mamba)
- [Anaconda](https://www.anaconda.com/download)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

This example uses Conda to install some dependencies that are not available via PyPi.

Create a new conda environment
```bash
conda create --name new_env python=3.10 -y
```

Activate the environment
```bash
conda activate new_env
```

Install the dependencies
```bash
conda install -y -c conda-forge gmsh python-gmsh moab>=5.3.0 ocp>=7.7.2.0 cadquery>=2.4.0
```

Then you can install the cad_to_dagmc package with ```pip```
```bash
pip install cad_to_dagmc
```

## Install using pip and source compilations

It is possible to avoid the use of conda and installing using pip and compiling from source.

First compile MOAB (and install Pymoab) from source

Then install cadquery and ocp using pip

```bash
pip install cadquery-ocp==7.7.2
pip install cadquery==2.4.0
```

Then you can install the cad_to_dagmc package with ```pip```

```bash
pip install cad_to_dagmc
```


# Usage - with OpenMC

You may also want to install OpenMC with DAGMC to make use of the h5m geometry files produced in simulations. However you could also use other supported particle transport codes such as MCNP, FLUKA and others supported by [DAGMC](https://svalinn.github.io/DAGMC/).

You can run ```mamba install -c conda-forge openmc``` however this may choose to install OpenMC without DAGMC included.

You can be more specific with conda/mamba commands to make sure the latest version of OpenMC which contains DAGMC is chosen by conda / mamba
```bash
mamba install -c conda-forge -y "openmc=0.14.0=dagmc*nompi*"
```

You could also [install OpenMC from source](https://docs.openmc.org/en/stable/quickinstall.html) which might be prefered as it can be tricky for the conda enviroment to get resolved.



# Usage - creation of DAGMC h5m files

For examples see the [examples folder](https://github.com/fusion-energy/cad_to_dagmc/tree/main/examples)

# Usage - simulation with transport code

For examples see the [examples folder](https://github.com/fusion-energy/cad_to_dagmc/tree/main/examples)

For more examples see the CAD tasks in the [neutronics-workshop](https://github.com/fusion-energy/neutronics-workshop) and [model benchmark zoo](https://github.com/fusion-energy/model_benchmark_zoo)
