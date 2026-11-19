# Quickstart

The first example converts a CadQuery assembly to a DAGMC h5m file. The later
sections start from a STEP file instead, write a volume mesh on its own or
conformal with the h5m file, and load the results in OpenMC.

## Basic Example

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane("XY").sphere(10)
# cut the sphere out of the box so the two solids do not overlap
box = cq.Workplane("XY").box(30, 30, 30).cut(sphere)

assembly = cq.Assembly()
assembly.add(sphere, name="tungsten")
assembly.add(box, name="steel")

model = CadToDagmc()
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_names",  # tag each solid with its part name
)
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

This writes `dagmc.h5m` with two volumes tagged `mat:tungsten` and
`mat:steel`. Tags can also be given as a list, one per volume, or taken from
`cq.Material`; see [Material Tagging](material_tagging/index.md).

:::{important}
Solids can touch but must not overlap, because DAGMC gives each region exactly
one material. That is why the example cuts the sphere out of the box. The
default cad-to-dagmc-mesher backend refuses to export the overlaps it can find
at no extra cost, such as an uncut sphere inside a box, and names the solids
involved. It does not catch every overlap, and the Gmsh backend checks none,
so run `model.check_overlaps()` for an exact test of every pair; see
[Checking for Overlaps](advanced/overlaps.md#checking-every-pair).
:::

## From a STEP File

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
model.add_stp_file(
    filename="geometry.step",
    # one tag per volume, in the order of the volumes in the file
    material_tags=["mat1", "mat2", "mat3"],
    scale_factor=0.1,
)
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

CadQuery reads a STEP file in millimetres, whatever unit it was saved in, so
`scale_factor=0.1` gives the centimetres OpenMC uses; see
[Geometry Scaling](advanced/geometry_scaling.md). To tag a STEP file by its
part names instead, see [STEP Files](inputs/step_files.md).

## Creating a Volume Mesh

`export_unstructured_mesh_file` writes a volume mesh of tetrahedra as a VTK
file, for unstructured mesh tallies in OpenMC:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane("XY").sphere(10)

model = CadToDagmc()
model.add_cadquery_object(sphere, material_tags=["tungsten"])

# target_edge_length selects the cad-to-dagmc-mesher backend
model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    target_edge_length=2.0,
)
```

Without `target_edge_length` or `tet_volumes` the method meshes with Gmsh
instead, sized by `min_mesh_size` and `max_mesh_size`; see
[Unstructured Mesh VTK Files](outputs/unstructured_vtk.md).

## Creating Conformal Surface and Volume Meshes

If you use DAGMC geometry and unstructured mesh tallies together, write both
meshes from one `export_dagmc_h5m_file` call so that they are conformal. Pass
`tet_volumes` and `target_edge_length`, and the call returns both filenames:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane("XY").sphere(10)
box = cq.Workplane("XY").box(30, 30, 30).cut(sphere)

assembly = cq.Assembly()
assembly.add(sphere, name="sphere")
assembly.add(box, name="box")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten", "steel"])

dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    tet_volumes=["steel"],  # material tags of the volumes to fill with tetrahedra
    target_edge_length=2.0,
    umesh_filename="umesh.vtk",
)
```

`tet_volumes` takes material tag names. For every listed volume the surface is
remeshed at `target_edge_length`, and that surface is both the DAGMC tracking
surface and the boundary of the tetrahedra.

The Gmsh backend does the same with `unstructured_volumes`, which takes volume
IDs or material tags; see [Conformal Meshes](outputs/conformal_meshes.md).

## Using in OpenMC

OpenMC gives each volume the material whose name matches its tag without the
`mat:` prefix, here `tungsten` and `steel`:

<!--pytest-codeblocks:skip-->
```python
import openmc

tungsten = openmc.Material(name="tungsten")
tungsten.add_element("W", 1.0)
tungsten.set_density("g/cm3", 19.3)

steel = openmc.Material(name="steel")
steel.add_element("Fe", 1.0)
steel.set_density("g/cm3", 7.8)

materials = openmc.Materials([tungsten, steel])

dag_universe = openmc.DAGMCUniverse(filename="dagmc.h5m")
# cad_to_dagmc writes no graveyard, so bound the geometry with a vacuum box
geometry = openmc.Geometry(root=dag_universe.bounded_universe())
```

[DAGMC h5m Files](outputs/dagmc_h5m.md#using-in-openmc) continues this example
with settings and a run. For a tally on the volume mesh, see
[Unstructured Mesh VTK Files](outputs/unstructured_vtk.md#using-in-openmc).
