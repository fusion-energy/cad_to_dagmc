# Installation

cad_to_dagmc is on both [PyPI](https://pypi.org/project/cad_to_dagmc/) and
[conda-forge](https://anaconda.org/conda-forge/cad_to_dagmc), so it can be installed
with pip or with Conda/Mamba. Both are supported, pip is the more popular route.

The two routes differ in which optional packages come along with them, see
[Optional packages](#optional-packages) below.

## Install using pip

```bash
pip install cad_to_dagmc
```

This also installs [cad-to-dagmc-mesher](https://github.com/fusion-energy/cad-to-dagmc-mesher),
the default meshing backend.

## Install using Mamba

Mamba resolves environments faster than Conda.

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

## Optional packages

Two packages are optional, and which one is easy to add depends on how you installed
cad_to_dagmc.

| Package | Needed for | With pip | With Conda/Mamba |
|---------|------------|----------|------------------|
| [cad-to-dagmc-mesher](meshing/cad_to_dagmc_mesher_backend.md) | the default meshing backend | installed as a dependency | not on conda-forge, add with `pip install cad-to-dagmc-mesher` |
| pymoab | `h5m_backend="pymoab"` | `pip install --extra-index-url https://shimwell.github.io/wheels moab` | `conda install -c conda-forge moab` |

:::{note}
The h5py h5m backend is the default and does not need MOAB, so pymoab is only worth
installing if you specifically want `h5m_backend="pymoab"`. pymoab is not on PyPI
itself, which is why it is not a dependency of the pip package, but the extra index
above serves wheels for it so pip installing it is still a one liner.
:::

:::{note}
cad-to-dagmc-mesher is not on conda-forge. Without it, a call that names no meshing
backend falls back to the cadquery backend and warns. pip installing it works alongside
a Conda/Mamba installation.
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
