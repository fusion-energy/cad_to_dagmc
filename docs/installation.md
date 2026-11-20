# Installation

cad_to_dagmc is on [PyPI](https://pypi.org/project/cad_to_dagmc/) and
[conda-forge](https://anaconda.org/conda-forge/cad_to_dagmc). Installing with
pip also brings cad-to-dagmc-mesher, the default meshing backend, which is not
on conda-forge.

## Install with pip

<!--pytest-codeblocks:skip-->
```bash
pip install cad_to_dagmc
```

## Install with conda or mamba

<!--pytest-codeblocks:skip-->
```bash
conda create --name cad_to_dagmc_env python=3.13 -y
conda activate cad_to_dagmc_env
conda install -y -c conda-forge cad_to_dagmc
```

The same commands work with mamba, which resolves environments faster. To add
cad-to-dagmc-mesher, see [Optional packages](#optional-packages).

## Optional packages

| Package | Needed for | With pip | With conda or mamba |
|---------|------------|----------|---------------------|
| [cad-to-dagmc-mesher](meshing/cad_to_dagmc_mesher_backend.md) | the default meshing backend and `check_overlaps()` | installed as a dependency | not on conda-forge, but `pip install cad-to-dagmc-mesher` works in the conda environment |
| pymoab | `h5m_backend="pymoab"` | `pip install --extra-index-url https://shimwell.github.io/wheels moab` | `conda install -c conda-forge moab` |

If cad-to-dagmc-mesher is not installed, `export_dagmc_h5m_file` with no meshing
arguments falls back to the Gmsh backend and warns. Asking for the mesher, with
`meshing_backend="cad-to-dagmc-mesher"` or one of its arguments such as
`tolerance` or `target_edge_length`, raises `CadToDagmcMesherNotFoundError`, and
so does `check_overlaps()`.

The default h5py h5m backend does not need MOAB, so pymoab is only needed for
`h5m_backend="pymoab"`. It is not on PyPI, which is why the pip command uses an
extra index. To build it from source, run
`pip install git+https://bitbucket.org/fathomteam/moab/`.

## Install OpenMC

To use the h5m files in a simulation you need a transport code built with DAGMC,
such as OpenMC. From conda-forge, the `dagmc*` build string picks a build with
DAGMC. The version is only an example:

<!--pytest-codeblocks:skip-->
```bash
conda install -c conda-forge -y "openmc=0.15.2=dagmc*"
```

With pip, from the same extra index as pymoab:

<!--pytest-codeblocks:skip-->
```bash
pip install --extra-index-url https://shimwell.github.io/wheels openmc
```

To build from source, see the
[OpenMC installation guide](https://docs.openmc.org/en/stable/quickinstall.html).
