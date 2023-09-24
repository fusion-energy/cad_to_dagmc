import typing
from cadquery import importers

# from cadquery import Assembly
# from OCP.GCPnts import GCPnts_QuasiUniformDeflection

# from cadquery.occ_impl import shapes
import OCP
import cadquery as cq

# from OCP.TopLoc import TopLoc_Location
# from OCP.BRep import BRep_Tool
# from OCP.TopAbs import TopAbs_Orientation

from .brep_to_h5m import mesh_brep, mesh_to_h5m_in_memory_method
from .brep_part_finder import (
    get_ids_from_assembly,
    get_ids_from_imprinted_assembly,
    order_material_ids_by_brep_order,
)


class CadToDagmc:
    def __init__(self):
        self.parts = []
        self.material_tags = []

    def add_stp_file(
        self,
        filename: str,
        material_tags: typing.Iterable[str],
        scale_factor: float = 1.0,
    ):
        """Loads the parts from stp file into the model keeping track of the
        parts and their material tags.

        Args:
            filename: the filename used to save the html graph.
            material_tags: the names of the DAGMC material tags to assign.
                These will need to be in the same order as the volumes in the
                STP file and match the material tags used in the neutronics
                code (e.g. OpenMC).
            scale_factor: a scaling factor to apply to the geometry that can be
                used to increase the size or decrease the size of the geometry.
                Useful when converting the geometry to cm for use in neutronics
                simulations.
        """
        part = importers.importStep(str(filename)).val()

        if scale_factor == 1:
            scaled_part = part
        else:
            scaled_part = part.scale(scale_factor)
        self.add_cadquery_object(object=scaled_part, material_tags=material_tags)

    def add_cadquery_object(
        self,
        object: typing.Union[
            cq.assembly.Assembly, cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid
        ],
        material_tags: typing.Iterable[str],
    ):
        """Loads the parts from CadQuery object into the model keeping track of
        the parts and their material tags.

        Args:
            object: the cadquery object to convert
            material_tags: the names of the DAGMC material tags to assign.
                These will need to be in the same order as the volumes in the
                STP file and match the material tags used in the neutronics
                code (e.g. OpenMC).
        """

        if isinstance(object, cq.assembly.Assembly):
            object = object.toCompound()

        if isinstance(object, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            iterable_solids = object.Solids()
        else:
            iterable_solids = object.val().Solids()
        self.parts = self.parts + iterable_solids

        if len(iterable_solids) != len(material_tags):
            msg = f"Number of volumes {len(iterable_solids)} is not equal to number of material tags {len(material_tags)}"
            raise ValueError(msg)

        for material_tag in material_tags:
            self.material_tags.append(material_tag)

    def export_dagmc_h5m_file(
        self,
        filename: str = "dagmc.h5m",
        min_mesh_size: float = 1,
        max_mesh_size: float = 5,
        mesh_algorithm: int = 1,
        msh_filename: str = None,
    ):
        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        (
            imprinted_assembly,
            imprinted_solids_with_original_id,
        ) = cq.occ_impl.assembly.imprint(assembly)

        original_ids = get_ids_from_assembly(assembly)
        scrambled_ids = get_ids_from_imprinted_assembly(
            imprinted_solids_with_original_id
        )

        # both id lists should be the same length as each other and the same
        # length as the self.material_tags

        material_tags_in_brep_order = order_material_ids_by_brep_order(
            original_ids, scrambled_ids, self.material_tags
        )

        gmsh, volumes = mesh_brep(
            brep_object=imprinted_assembly.wrapped._address(),
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
        )

        h5m_filename = mesh_to_h5m_in_memory_method(
            volumes=volumes,
            material_tags=material_tags_in_brep_order,
            h5m_filename=filename,
            msh_filename=msh_filename,
        )
        return h5m_filename


def merge_surfaces(parts):
    """Merges surfaces in the geometry that are the same. More details on
    the merging process in the DAGMC docs
    https://svalinn.github.io/DAGMC/usersguide/cubit_basics.html"""

    # solids = geometry.Solids()

    bldr = OCP.BOPAlgo.BOPAlgo_Splitter()

    if len(parts) == 1:
        # merged_solid = cq.Compound(solids)

        if isinstance(
            parts[0], (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)
        ):
            # stp file
            return parts[0], parts[0].wrapped
        else:
            return parts[0], parts[0].toOCC()

    # else:
    for solid in parts:
        # checks if solid is a compound as .val() is not needed for compounds
        if isinstance(solid, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            bldr.AddArgument(solid.wrapped)
        else:
            bldr.AddArgument(solid.val().wrapped)

    bldr.SetNonDestructive(True)

    bldr.Perform()

    bldr.Images()

    merged_solid = cq.Compound(bldr.Shape())

    return merged_solid, merged_solid.wrapped
