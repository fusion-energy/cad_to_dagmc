# Installation

cad_to_dagmc can be installed using pip or Conda/Mamba.


## Install using pip

```bash
pip install cad_to_dagmc
```
<!-- 
## Install using Mamba

Mamba is faster than Conda and recommended for installing this package.

<!--pytest-codeblocks:skip-->
```bash
# Create a new environment
mamba create --name cad_to_dagmc_env python=3.13 -y

# Activate the environment
mamba activate cad_to_dagmc_env

# Install cad_to_dagmc
mamba install -y -c conda-forge cad_to_dagmc
```

## Install using Conda

<!--pytest-codeblocks:skip-->
```bash
# Create a new environment
conda create --name cad_to_dagmc_env python=3.13 -y

# Activate the environment
conda activate cad_to_dagmc_env

# Install cad_to_dagmc
conda install -y -c conda-forge cad_to_dagmc
```
 -->

:::{note}
The pip installation uses the **h5py backend** by default, which does not require MOAB/pymoab.
As pymoab is not currently available on PyPi it can't be included in the PyPi distributed pip cad_to_dagmc pip package.
If you want to use pymoab backend and you installed via pip you'll need to install MOAB separately.
The Conda/Mamba installed version of cad-to-dagmc includes pymoab.
:::

## Optional: Installing pymoab

pymoab is optional and only needed if you want to use the `h5m_backend="pymoab"` option.

**Option 1: Via Conda**

<!--pytest-codeblocks:skip-->
```bash
conda install -c conda-forge moab
```

**Option 2: Via extra index**

<!--pytest-codeblocks:skip-->
```bash
pip install --extra-index-url https://shimwell.github.io/wheels moab
```

**Option 3: From source**

<!--pytest-codeblocks:skip-->
```bash
pip install git+https://bitbucket.org/fathomteam/moab/
```

## Optional: Installing OpenMC

To use the generated h5m files in neutronics simulations, you'll need a DAGMC-enabled
transport code like OpenMC.

**Option 1: Via Conda**

<!--pytest-codeblocks:skip-->
```bash
conda install -c conda-forge -y "openmc=0.15.2=dagmc*"
```

**Option 2: Via extra index**

<!--pytest-codeblocks:skip-->
```bash
pip install --extra-index-url https://shimwell.github.io/wheels openmc
```

**Option 3: From source**

Alternatively, see the [OpenMC installation guide](https://docs.openmc.org/en/stable/quickinstall.html)
for building from source.
