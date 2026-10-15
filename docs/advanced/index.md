# Advanced Options

This section covers advanced configuration options for fine-tuning your CAD to DAGMC workflow.

## Topics

| Topic | Description |
|-------|-------------|
| [Geometry Scaling](geometry_scaling.md) | Unit conversion with `scale_factor` |
| [Imprinting](imprinting.md) | Shared surface handling |
| [Implicit Complement](implicit_complement.md) | Void/air region tagging |
| [Parallel Processing](parallel_processing.md) | Thread control for performance |
| [H5M Backends](h5m_backends.md) | h5py vs pymoab comparison |

## Quick Reference

### Common Options

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    scale_factor=0.1,                      # mm to cm conversion
    imprint={"threads": "all", "glue": "partial"},  # Default imprint options
    implicit_complement_material_tag="air", # Tag for void space
    h5m_backend="h5py",                    # H5M writing backend
    method="file",                         # CAD transfer method, gmsh backend only
)
```

### When to Use Each

| Option | When to Use |
|--------|-------------|
| `scale_factor` | CAD in different units than simulation |
| `imprint=False` | Single volume or non-touching geometry |
| `imprint={"threads": 1, "glue": "partial"}` | Reduce imprinting peak RAM on a large model |
| `imprint={"threads": "all", "glue": "full"}` | Exact whole-face coincidence only; requires selectable CadQuery glue for multiple solids |
| `imprint={"threads": "all", "glue": None}` | General intersection without glue assumptions; requires selectable CadQuery glue for multiple solids, and overlaps remain invalid DAGMC |
| `imprint=False` with a BREP | Geometry you [imprinted yourself](imprinting.md#meshing-geometry-you-imprinted-yourself) |
| `implicit_complement_material_tag` | Need to track particles in void |
| `h5m_backend="pymoab"` | Compatibility with older DAGMC tools |
| `method="in memory"` | Large geometry with matching OCC versions |

Omitting `imprint` selects an immutable `{"threads": "all", "glue": "partial"}`
mapping. An explicit mapping must contain exactly both keys and is never modified.
`"threads"` accepts `"all"` or a positive integer, not a boolean; `"all"` requests
the OCC logical processor count and restores the previous pool after imprinting.
See [Imprinting](imprinting.md) for the complete contract and migration table.
