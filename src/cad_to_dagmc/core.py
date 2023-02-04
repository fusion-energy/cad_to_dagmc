from tempfile import mkstemp

import typing
from cadquery import importers
from cadquery import Assembly
from OCP.GCPnts import GCPnts_QuasiUniformDeflection

# from cadquery.occ_impl import shapes
import OCP
import cadquery as cq
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation

from brep_to_h5m import brep_to_h5m
import brep_part_finder as bpf


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
            print("assembly found")
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
        max_mesh_size: float = 10,
        verbose: bool = False,
        volume_atol: float = 0.000001,
        center_atol: float = 0.000001,
        bounding_box_atol: float = 0.000001,
    ):
        brep_shape = self._merge_surfaces()

        tmp_brep_filename = mkstemp(suffix=".brep", prefix="paramak_")[1]
        brep_shape.exportBrep(tmp_brep_filename)

        if verbose:
            print(f"Brep file saved to {tmp_brep_filename}")

        brep_file_part_properties = bpf.get_part_properties_from_shapes(brep_shape)

        shape_properties = bpf.get_part_properties_from_shapes(self.parts)

        brep_and_shape_part_ids = bpf.get_matching_part_ids(
            brep_part_properties=brep_file_part_properties,
            shape_properties=shape_properties,
            volume_atol=volume_atol,
            center_atol=center_atol,
            bounding_box_atol=bounding_box_atol,
        )

        material_tags_in_brep_order = []
        for brep_id, shape_id in brep_and_shape_part_ids:
            material_tags_in_brep_order.append(self.material_tags[shape_id - 1])

        brep_to_h5m(
            brep_filename=tmp_brep_filename,
            material_tags=material_tags_in_brep_order,
            h5m_filename=filename,
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
        )

    def _merge_surfaces(self):
        """Merges surfaces in the geometry that are the same. More details on
        the merging process in the DAGMC docs
        https://svalinn.github.io/DAGMC/usersguide/cubit_basics.html"""

        # solids = geometry.Solids()

        bldr = OCP.BOPAlgo.BOPAlgo_Splitter()

        if len(self.parts) == 1:
            # merged_solid = cq.Compound(solids)
            return self.parts[0]

        for solid in self.parts:
            # checks if solid is a compound as .val() is not needed for compounds
            if isinstance(
                solid, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)
            ):
                bldr.AddArgument(solid.wrapped)
            else:
                bldr.AddArgument(solid.val().wrapped)

        bldr.SetNonDestructive(True)

        bldr.Perform()

        bldr.Images()

        merged_solid = cq.Compound(bldr.Shape())

        return merged_solid

    # this didn't produce non overlapping water tight parts when the geometry was in contact with other surfaces
    # def tessellate(parts, tolerance: float = 0.1, angularTolerance: float = 0.1):
    #     """Creates a mesh / faceting / tessellation of the surface"""

    #     parts.mesh(tolerance, angularTolerance)

    #     offset = 0

    #     vertices: List[Vector] = []
    #     triangles = {}

    #     for f in parts.Faces():

    #         loc = TopLoc_Location()
    #         poly = BRep_Tool.Triangulation_s(f.wrapped, loc)
    #         Trsf = loc.Transformation()

    #         reverse = (
    #             True
    #             if f.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
    #             else False
    #         )

    #         # add vertices
    #         face_verticles = [
    #             (v.X(), v.Y(), v.Z()) for v in (v.Transformed(Trsf) for v in poly.Nodes())
    #         ]
    #         vertices += face_verticles

    #         face_triangles = [
    #             (
    #                 t.Value(1) + offset - 1,
    #                 t.Value(3) + offset - 1,
    #                 t.Value(2) + offset - 1,
    #             )
    #             if reverse
    #             else (
    #                 t.Value(1) + offset - 1,
    #                 t.Value(2) + offset - 1,
    #                 t.Value(3) + offset - 1,
    #             )
    #             for t in poly.Triangles()
    #         ]
    #         triangles[f.hashCode()] = face_triangles

    #         offset += poly.NbNodes()

    #     list_of_triangles_per_solid = []
    #     for s in parts.Solids():
    #         triangles_on_solid = []
    #         for f in s.Faces():
    #             triangles_on_solid += triangles[f.hashCode()]
    #         list_of_triangles_per_solid.append(triangles_on_solid)
    #     for vert in vertices:
    #     for tri in list_of_triangles_per_solid:
    #     return vertices, list_of_triangles_per_solid
