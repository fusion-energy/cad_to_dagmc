
[![N|Python](https://www.python.org/static/community_logos/python-powered-w-100x40.png)](https://www.python.org)

[![CI with pip install](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_pip_install.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_pip_install.yml) Testing package and running examples with dependencies installed via pip

[![CI with model benchmark zoo](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_benchmarks.yml/badge.svg?branch=main)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/ci_with_benchmarks.yml) Testing with [Model Benchmark Zoo](https://github.com/fusion-energy/model_benchmark_zoo)

[![Upload Python Package](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/python-publish.yml/badge.svg)](https://github.com/fusion-energy/cad_to_dagmc/actions/workflows/python-publish.yml)

[![PyPI](https://img.shields.io/pypi/v/cad_to_dagmc?color=brightgreen&label=pypi&logo=grebrightgreenen&logoColor=green)](https://pypi.org/project/cad_to_dagmc/)


A minimal package that converts CAD geometry to [DAGMC](https://github.com/svalinn/DAGMC/) (h5m) files, [unstructured mesh](https://docs.openmc.org/en/latest/pythonapi/generated/openmc.UnstructuredMesh.html) files (vtk) and Gmsh (msh) files ready for use in neutronics simulations.

## See the :point_right: [online documentation](https://fusion-energy.github.io/cad_to_dagmc/) :point_left: for installation options, usage recommendations and Python API details.

## Gmsh 3D meshing controls

The Gmsh backend exposes separate controls for the surface and volume mesh:

| Argument | Default | Controls |
|----------|---------|----------|
| `mesh_algorithm` | `1` | 2D surface algorithm (`Mesh.Algorithm`) |
| `mesh_algorithm_3d` | `1` (Delaunay) | 3D volume algorithm (`Mesh.Algorithm3D`); `10` selects multithreaded HXT |
| `volume_mesh_options` | `None` | Dictionary of Gmsh option names and numeric/string values, applied **after surface meshing and before volume meshing** |

These controls apply to **both combined conformal surface/volume export and
standalone 3D export**. They are Gmsh-specific; other meshing backends are
unchanged. Existing calls keep their defaults and meshing sequence.

### Conformal DAGMC geometry and unstructured tally mesh

When using a DAGMC geometry together with an unstructured mesh tally covering
the same volumes, export both in **one call**. This reuses the DAGMC surface
triangulation as the boundary of the tetrahedral mesh, avoiding mismatched
tracking and tally boundaries from independently generated meshes.

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
model.add_cadquery_object(
	cq.Workplane("XY").sphere(10), material_tags=["steel"]
)

dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
	filename="dagmc.h5m",
	umesh_filename="umesh.vtk",
	meshing_backend="gmsh",
	unstructured_volumes=["steel"],
	min_mesh_size=1.0,
	max_mesh_size=5.0,
	mesh_algorithm=6,        # Frontal-Delaunay for the surfaces
	mesh_algorithm_3d=10,    # HXT for the tetrahedra
	volume_mesh_options={
		"Mesh.Optimize": 0,
		"Mesh.MeshSizeExtendFromBoundary": 0,
		"Mesh.MeshSizeMax": 1e22,
	},
)
```

The surfaces are meshed using `min_mesh_size`, `max_mesh_size` and any
per-volume `set_size` values. Only then are the volume options applied. The
example relaxes interior sizing without coarsening the existing tracking
surface. `unstructured_volumes` can select volume IDs, material tags, or both;
the DAGMC file still includes all volumes. Keep `imprint=True` (the default)
for touching solids so their interfaces are shared.

### Standalone 3D mesh

The same controls are available when only a volume mesh is needed:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
model.add_cadquery_object(
	cq.Workplane("XY").sphere(10), material_tags=["steel"]
)

model.export_unstructured_mesh_file(
	filename="standalone_umesh.vtk",
	meshing_backend="gmsh",
	min_mesh_size=1.0,
	max_mesh_size=5.0,
	mesh_algorithm_3d=10,
	volume_mesh_options={
		"Mesh.Optimize": 0,
		"Mesh.MeshSizeExtendFromBoundary": 0,
		"Mesh.MeshSizeMax": 1e22,
	},
)
```

`export_gmsh_mesh_file(dimensions=3, ...)` accepts these arguments too.
Standalone export does **not** reuse a surface mesh from an earlier export;
use the combined call above when the tracking and tally meshes must conform.

With `volume_mesh_options=None` or `{}`, direct volume exports retain a single
`generate(3)` call. A non-empty dictionary stages this as `generate(2)`, option
overrides, then `generate(3)`. The combined export already creates the surface
mesh first and reuses it. Dictionary values override the corresponding named
settings during the volume step; surface-only exports ignore the dictionary.

The settings shown allow a coarser interior, but do not guarantee zero interior
refinement or a particular speedup. Check mesh quality and tally resolution
for your application. Other Gmsh size constraints still apply unless overridden.
Use volume sizing/optimisation options compatible with a first-order
tetrahedral mesh; options that change element order, recombine elements or
force remeshing can invalidate the conformal DAGMC/tally pairing.

See [conformal meshes](docs/outputs/conformal_meshes.md) and
[Gmsh volume options](docs/meshing/gmsh_backend.md#3d-algorithms-and-volume-only-options)
for more details.
