# Python API Reference

## Export Imprint Configuration

`export_dagmc_h5m_file`, `export_unstructured_mesh_file`, and
`export_gmsh_mesh_file` share the `cad-to-dagmc-mesher==0.3.5` imprint API:

- Omit `imprint` to use the immutable default mapping
   `{"threads": "all", "glue": "partial"}`, or pass `imprint=False` to disable it.
- An enabled mapping must contain exactly `"threads"` and `"glue"`. It is never
   modified, and is passed directly to the mesher backend; GMSH uses the same
   validated options.
- `"threads"` accepts `"all"` or a positive Python `int`, not a boolean.
   `"all"` actively requests the OCC logical processor count for imprinting,
   rather than preserving an existing limit. The previous pool is restored
   afterwards, including on errors, without changing meshing thread settings.
- `"glue"` accepts `"partial"`, `"full"`, or `None`. `"full"` requires exact
   whole-face coincidence; `None` disables glue, but overlapping solids remain
   invalid DAGMC geometry.
- CadQuery 2.8's legacy imprint supports partial glue. For multiple solids,
   `"full"` and `None` raise before imprinting or writing output. A single solid
   skips actual imprinting, but all options are still validated.

See [Imprinting](advanced/imprinting.md) for examples, rejected inputs, and the
[migration table](advanced/imprinting.md#migrating-from-the-previous-api).

## Main Class

```{eval-rst}
.. autoclass:: cad_to_dagmc.CadToDagmc
   :members:
   :undoc-members:
   :show-inheritance:
```

## Standalone Functions

### GMSH to DAGMC Conversion

```{eval-rst}
.. autofunction:: cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file
```

```{eval-rst}
.. autofunction:: cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file
```

### Low-Level Functions

```{eval-rst}
.. autofunction:: cad_to_dagmc.vertices_to_h5m
```

```{eval-rst}
.. autofunction:: cad_to_dagmc.init_gmsh
```

```{eval-rst}
.. autofunction:: cad_to_dagmc.get_volumes
```

```{eval-rst}
.. autofunction:: cad_to_dagmc.set_sizes_for_mesh
```

```{eval-rst}
.. autofunction:: cad_to_dagmc.mesh_to_vertices_and_triangles
```

## Exceptions

```{eval-rst}
.. autoexception:: cad_to_dagmc.PyMoabNotFoundError
   :show-inheritance:
```

```{eval-rst}
.. autoexception:: cad_to_dagmc.CadToDagmcMesherNotFoundError
   :show-inheritance:
```
