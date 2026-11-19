# Per-Volume Mesh Sizing

`set_size` gives individual volumes their own target mesh size, so the mesh can
be fine where detail matters and coarse elsewhere.

:::{note}
`set_size` is a Gmsh backend argument. Passing it to `export_dagmc_h5m_file`
selects Gmsh, so `meshing_backend` is not needed. The cad-to-dagmc-mesher
backend ignores it without a warning. That backend runs when `meshing_backend`
names it, and in `export_unstructured_mesh_file` whenever `target_edge_length`
or `tet_volumes` is given.
:::

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

coarse_box = cq.Workplane().box(1, 1, 2)
fine_box = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
default_box = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

assembly = cq.Assembly()
assembly.add(coarse_box, name="coarse")
assembly.add(fine_box, name="fine")
assembly.add(default_box, name="global")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

# Check available material tags
print("Material tags:", model.material_tags)
# Output: Material tags: ['coarse', 'fine', 'global']

model.export_dagmc_h5m_file(
    filename="different_resolution_meshes.h5m",
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,  # Coarse mesh for this volume
        "fine": 0.1,    # Fine mesh for this volume
        # "global" is not listed, so it has no size of its own
    },
)
```

## Specifying Volumes

Keys are material tags, each meaning every volume with that tag, or integer
volume IDs. They can be mixed:

<!--pytest-codeblocks:skip-->
```python
set_size={
    "coolant": 2.0,  # every volume tagged "coolant"
    1: 0.5,          # volume 1
}
```

## How It Works

cad_to_dagmc sets the size on the points of each listed volume's boundary (its
CAD vertices), and Gmsh grades the element size along the curves and surfaces
between them. A point shared by two listed volumes takes the smaller size, so a
surface between a coarse and a fine volume is meshed at the fine size. Volumes
not in `set_size` get no size of their own. `min_mesh_size` and
`max_mesh_size` bound their mesh, which grades towards the size of any listed
neighbour.

A size outside the range `min_mesh_size` to `max_mesh_size` is clamped to it,
with a warning. A volume given two different sizes (once by ID and once by tag,
say), a tag that no volume has and a volume ID that does not exist all raise
`ValueError`.

Volume IDs are Gmsh's volume numbers, starting at 1, after imprinting.
[Imprinting](../advanced/imprinting.md) can change the order of the volumes,
so an ID does not always match the order in which the solids were added. Tags
do not have this problem, so prefer them.

## Using with Volume Meshes

`set_size` works the same way in `export_unstructured_mesh_file`:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

coarse_box = cq.Workplane().box(1, 1, 2)
fine_box = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
default_box = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

assembly = cq.Assembly()
assembly.add(coarse_box, name="coarse")
assembly.add(fine_box, name="fine")
assembly.add(default_box, name="global")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

model.export_unstructured_mesh_file(
    filename="different_resolution_meshes.vtk",
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,
        "fine": 0.1,
    },
)
```

`export_gmsh_mesh_file` takes it too. In `export_dagmc_h5m_file` it also sizes
the conformal volume mesh written with `unstructured_volumes`.

## See Also

- [Gmsh Backend](gmsh_backend.md): the other Gmsh sizing arguments
- [Assembly Names](../material_tagging/assembly_names.md): tagging volumes with assembly part names, as in these examples
