# Material Tagging

Every volume in the DAGMC file carries a material tag, which OpenMC matches to a material by name.

## Tagging Methods

| Method | Description | Best For |
|--------|-------------|----------|
| [Manual Tags](manual_tags.md) | A list, one tag per volume | Simple models, STEP files |
| [Assembly Names](assembly_names.md) | Assembly part names | CadQuery assemblies, STEP files with named parts |
| [Assembly Materials](assembly_materials.md) | The `cq.Material` of each assembly part | Names that describe geometry; several parts sharing a material |
| [Gmsh Physical Groups](gmsh_physical_groups.md) | Names of the 3D physical groups in a Gmsh mesh | Existing Gmsh meshes |

## Quick Comparison

| Feature | Manual Tags | Assembly Names | Assembly Materials | Gmsh Groups |
|---------|-------------|----------------|-------------------|-------------|
| Requires ordering | Yes | No | No | Yes: groups pair with volumes by position |
| Tags read from the input | No | Yes | Yes | Yes |
| Works with STEP files | Yes | Yes | Yes | No |

## How Tags Are Stored

cad_to_dagmc writes each tag to the h5m file with a `mat:` prefix, so `tungsten` is stored as `mat:tungsten`. OpenMC reads the tag without the prefix and looks for a material with that name:

<!--pytest-codeblocks:skip-->
```python
import openmc

tungsten = openmc.Material(name="tungsten")
tungsten.add_element("W", 1.0)
tungsten.set_density("g/cm3", 19.3)
```

If no material has the name, OpenMC stops with an error that names the tag. [Using in OpenMC](../outputs/dagmc_h5m.md#using-in-openmc) has the full setup.

## Tag Name Guidelines

:::{warning}
`vacuum`, `void` and `graveyard` are reserved names. Case does not matter, so `Vacuum` and `VOID` are reserved too. OpenMC gives a volume with one of these tags no material, so particles cross it without interacting, and particles that reach the surface of a `graveyard` volume are killed. Tag a low-density gas `air` or `helium`, not `vacuum`, and define that material.
:::

Keep tags to 27 characters or fewer. Each group name in the h5m file gets 32 bytes, and `mat:` and the null byte that ends the name take 5 of them. A 28-character tag leaves no room for the null byte, so DAGMC can read past the end of the name and OpenMC then stops because no material matches. A longer tag is cut to its first 28 characters, with the same result. cad_to_dagmc warns about a tag that is too long. The [implicit complement](../advanced/implicit_complement.md) tag also gets `_comp` appended, so keep it to 22 characters.

OpenMC ignores case when it matches tags to material names, so the tag `Steel` finds a material named `steel`. A tag that matches two materials whose names differ only in case stops OpenMC with "More than one material found".

Do not use `:` or `/` in a tag. DAGMC splits group names at these characters and would read only the part of the tag before them.
