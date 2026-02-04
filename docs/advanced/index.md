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
    imprint=True,                          # Handle shared surfaces
    implicit_complement_material_tag="air", # Tag for void space
    h5m_backend="h5py",                    # H5M writing backend
    method="file",                         # CAD transfer method
)
```

### When to Use Each

| Option | When to Use |
|--------|-------------|
| `scale_factor` | CAD in different units than simulation |
| `imprint=False` | Single volume or non-touching geometry |
| `implicit_complement_material_tag` | Need to track particles in void |
| `h5m_backend="pymoab"` | Compatibility with older DAGMC tools |
| `method="inMemory"` | Large geometry with matching OCC versions |
