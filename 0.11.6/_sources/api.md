# Python API Reference

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
