# h5m Backends

The `h5m_backend` argument chooses how the DAGMC h5m file is written: with h5py
(the default) or with pymoab. `export_dagmc_h5m_file` takes it, and so do the
Gmsh conversion functions `export_gmsh_file_to_dagmc_h5m_file` and
`export_gmsh_object_to_dagmc_h5m_file`. The two backends do not write
byte-for-byte identical files, but both load in DAGMC.

## h5py Backend (Default)

cad_to_dagmc writes the file itself with h5py, which is installed with it, so
MOAB is not needed.

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    h5m_backend="h5py",  # the default
)
```

## pymoab Backend

MOAB's own library writes the file, through its Python package pymoab. pymoab
is not on PyPI, so it is not installed with cad_to_dagmc. The install commands
are under [Optional packages](../installation.md#optional-packages). If DAGMC
has trouble with a file, writing the same model with pymoab shows whether the
h5py backend is the cause.

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    h5m_backend="pymoab",
)
```

## Error Handling

`h5m_backend="pymoab"` without pymoab installed raises `PyMoabNotFoundError`, a
subclass of `ImportError`. Its message begins as follows, then lists the
install commands:

```text
PyMoabNotFoundError: pymoab is not installed. pymoab/MOAB is not available
on PyPI so it cannot be included as a dependency of cad-to-dagmc.
```

Any value other than `"h5py"` or `"pymoab"` raises `ValueError` ("method must be
'pymoab' or 'h5py'"). Both errors come when the file is written, after meshing
has finished, so on a large model check that `import pymoab` works before
starting a long export.

## See Also

- [DAGMC h5m Files](../outputs/dagmc_h5m.md): the other export options
