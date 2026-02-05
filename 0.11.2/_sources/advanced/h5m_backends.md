# H5M File Backends

cad_to_dagmc supports two backends for writing DAGMC h5m files: h5py (default) and pymoab.

## h5py Backend (Default)

The h5py backend writes h5m files using the h5py library directly. This is the default because it doesn't require MOAB to be installed.

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    h5m_backend="h5py",  # Default
)
```

**Advantages:**
- No MOAB/pymoab installation required
- Available via simple `pip install cad_to_dagmc`
- Produces DAGMC-compatible h5m files

**When to use:**
- When you can't or don't want to install MOAB
- For most standard use cases
- When deploying in environments without MOAB

## pymoab Backend

The pymoab backend uses the official MOAB library to write h5m files.

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    h5m_backend="pymoab",
)
```

**Advantages:**
- Uses the official MOAB library
- May have better compatibility with some DAGMC tools

**When to use:**
- When you need guaranteed MOAB compatibility
- When working with legacy DAGMC workflows
- When pymoab is already installed

## Installing pymoab

pymoab/MOAB must be installed separately (not available on PyPI):

**Option 1: Conda (easiest)**

<!--pytest-codeblocks:skip-->
```bash
conda install -c conda-forge moab
```

**Option 2: Extra index**

<!--pytest-codeblocks:skip-->
```bash
pip install --extra-index-url https://shimwell.github.io/wheels moab
```

**Option 3: From source**

<!--pytest-codeblocks:skip-->
```bash
pip install git+https://bitbucket.org/fathomteam/moab/
```

## Error Handling

If you request pymoab but it's not installed:

<!--pytest-codeblocks:skip-->
```python
>>> model.export_dagmc_h5m_file(h5m_backend="pymoab")
PyMoabNotFoundError: pymoab is not installed. pymoab/MOAB is not available
on PyPI so it cannot be included as a dependency of cad-to-dagmc.

You can install pymoab via one of these methods:
  1. From conda-forge: conda install -c conda-forge moab
  2. From extra index: pip install --extra-index-url https://shimwell.github.io/wheels moab
  3. From source: https://bitbucket.org/fathomteam/moab

Alternatively, use the h5py backend (the default) which does not require pymoab:
  export_dagmc_h5m_file(..., h5m_backend='h5py')
```

## Comparing Backends

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere1 = cq.Workplane().sphere(5)
sphere2 = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere1)
assembly.add(sphere2)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1", "mat2"])

# Export using h5py backend
model.export_dagmc_h5m_file(
    filename="dagmc_h5py.h5m",
    h5m_backend="h5py",
)
print("Created dagmc_h5py.h5m using h5py backend")

# Export using pymoab backend (requires MOAB)
model.export_dagmc_h5m_file(
    filename="dagmc_pymoab.h5m",
    h5m_backend="pymoab",
)
print("Created dagmc_pymoab.h5m using pymoab backend")
```

## File Compatibility

Both backends produce semantically equivalent h5m files that work with DAGMC. The files may not be byte-for-byte identical due to:

- Different HDF5 compression settings
- Different internal data ordering
- Different metadata

However, both will work correctly with:
- OpenMC with DAGMC
- MCNP with DAGMC
- Other DAGMC-enabled transport codes

## Comparison Table

| Feature | h5py Backend | pymoab Backend |
|---------|--------------|----------------|
| Installation | Included with pip install | Requires separate MOAB install |
| PyPI availability | Yes | No (conda or source) |
| DAGMC compatibility | Yes | Yes |
| File size | Similar | Similar |
| Performance | Similar | Similar |

## See Also

- [Installation](../installation.md) - Installing cad_to_dagmc and optional dependencies
- [DAGMC H5M Output](../outputs/dagmc_h5m.md) - Full export options
