from vertices_to_h5m import vertices_to_h5m
from pathlib import Path
import math


from cadquery import importers
from OCP.GCPnts import GCPnts_QuasiUniformDeflection

# from cadquery.occ_impl import shapes
import OCP
import cadquery as cq
from vertices_to_h5m import vertices_to_h5m
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation


def load_stp_file(filename: str, scale_factor: float = 1.0, auto_merge=True):
    """Loads a stp file and makes the 3D solid and wires available for use.
    Args:
        filename: the filename used to save the html graph.
        scale_factor: a scaling factor to apply to the geometry that can be
            used to increase the size or decrease the size of the geometry.
            Useful when converting the geometry to cm for use in neutronics
            simulations.
        auto_merge: whether or not to merge the surfaces. This defaults to True
            as merged surfaces are needed to avoid overlapping meshes in some
            cases. More details on the merging process in the DAGMC docs
            https://svalinn.github.io/DAGMC/usersguide/cubit_basics.html
    Returns:
        CadQuery.solid, CadQuery.Wires: solid and wires belonging to the object
    """

    part = importers.importStep(str(filename)).val()

    if scale_factor == 1:
        scaled_part = part
    else:
        scaled_part = part.scale(scale_factor)

    solid = scaled_part

    if auto_merge:
        solid = merge_surfaces(solid)

    return solid


def merge_surfaces(geometry):
    """Merges surfaces in the geometry that are the same"""

    solids = geometry.Solids()

    bldr = OCP.BOPAlgo.BOPAlgo_Splitter()

    if len(solids) == 1:
        # merged_solid = cq.Compound(solids)
        return solids[0]

    for solid in solids:
        # print(type(solid))
        # checks if solid is a compound as .val() is not needed for compounds
        if isinstance(solid, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            bldr.AddArgument(solid.wrapped)
        else:
            bldr.AddArgument(solid.val().wrapped)

    bldr.SetNonDestructive(True)

    bldr.Perform()

    bldr.Images()

    merged_solid = cq.Compound(bldr.Shape())

    return merged_solid


def tessellate_single_part(
    merged_solid, tolerance: float, angularTolerance: float = 0.1
):

    merged_solid.mesh(tolerance, angularTolerance)

    offset = 0

    vertices: List[Vector] = []
    triangles: List[Tuple[int, int, int]] = []

    for s in merged_solid.Solids():

        for f in s.Faces():

            loc = TopLoc_Location()
            poly = BRep_Tool.Triangulation_s(f.wrapped, loc)
            Trsf = loc.Transformation()

            reverse = (
                True
                if f.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
                else False
            )

            # add vertices
            vertices += [
                (v.X(), v.Y(), v.Z())
                for v in (v.Transformed(Trsf) for v in poly.Nodes())
            ]

            # add triangles
            triangles += [
                (
                    t.Value(1) + offset - 1,
                    t.Value(3) + offset - 1,
                    t.Value(2) + offset - 1,
                )
                if reverse
                else (
                    t.Value(1) + offset - 1,
                    t.Value(2) + offset - 1,
                    t.Value(3) + offset - 1,
                )
                for t in poly.Triangles()
            ]

            offset += poly.NbNodes()

    return vertices, triangles


def tessellate_parts(merged_solid, tolerance: float, angularTolerance: float = 0.1):

    merged_solid.mesh(tolerance, angularTolerance)

    offset = 0

    vertices: List[Vector] = []
    triangles: List[Tuple[int, int, int]] = []

    all_vertices = {}
    triangles_on_solids_faces = {}
    faces_already_added = []

    loop_counter = 0

    for s in merged_solid.Solids():
        # print(s.hashCode())
        # all_vertices[s.hashCode()] = {}
        triangles_on_solids_faces[s.hashCode()] = {}
        for f in s.Faces():

            if f.hashCode() not in faces_already_added:
                faces_already_added.append(f.hashCode())

                loop_counter = loop_counter + 1
                loc = TopLoc_Location()
                poly = BRep_Tool.Triangulation_s(f.wrapped, loc)
                Trsf = loc.Transformation()

                reverse = (
                    True
                    if f.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
                    else False
                )

                # add vertices
                face_verticles = [
                    (v.X(), v.Y(), v.Z())
                    for v in (v.Transformed(Trsf) for v in poly.Nodes())
                ]
                vertices += face_verticles

                # add triangles
                face_triangles = [
                    (
                        t.Value(1) + offset - 1,
                        t.Value(3) + offset - 1,
                        t.Value(2) + offset - 1,
                    )
                    if reverse
                    else (
                        t.Value(1) + offset - 1,
                        t.Value(2) + offset - 1,
                        t.Value(3) + offset - 1,
                    )
                    for t in poly.Triangles()
                ]
                triangles.append(face_triangles)

                # solid_verticles

                offset += poly.NbNodes()

                # new_code = str(f.hashCode()) + "____" + str(loop_counter)
                triangles_on_solids_faces[s.hashCode()][f.hashCode()] = face_triangles
                # face_verticles
            else:
                triangles_on_solids_faces[s.hashCode()][f.hashCode()] = face_triangles

    list_of_triangles_per_solid = []
    for key, value in triangles_on_solids_faces.items():
        triangles_on_solid = []
        for key, face in value.items():
            triangles_on_solid = triangles_on_solid + face
        list_of_triangles_per_solid.append(triangles_on_solid)

    return vertices, list_of_triangles_per_solid


def tessellate(parts, tolerance: float = 0.1, angularTolerance: float = 0.1):
    """Creates a mesh / faceting / tessellation of the surface"""

    parts.mesh(tolerance, angularTolerance)

    offset = 0

    vertices: List[Vector] = []
    triangles: List[Tuple[int, int, int]] = []

    # all_vertices = {}
    triangles_on_solids_faces = {}
    faces_already_added = []

    loop_counter = 0

    for s in parts.Solids():
        # print(s.hashCode())
        # all_vertices[s.hashCode()] = {}
        triangles_on_solids_faces[s.hashCode()] = {}
        for f in s.Faces():

            loop_counter = loop_counter + 1
            loc = TopLoc_Location()
            poly = BRep_Tool.Triangulation_s(f.wrapped, loc)
            Trsf = loc.Transformation()

            reverse = (
                True
                if f.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
                else False
            )

            # add vertices
            face_verticles = [
                (v.X(), v.Y(), v.Z())
                for v in (v.Transformed(Trsf) for v in poly.Nodes())
            ]
            vertices += face_verticles

            if f.hashCode() not in faces_already_added:
                faces_already_added.append(f.hashCode())

                # add triangles
                face_triangles = [
                    (
                        t.Value(1) + offset - 1,
                        t.Value(3) + offset - 1,
                        t.Value(2) + offset - 1,
                    )
                    if reverse
                    else (
                        t.Value(1) + offset - 1,
                        t.Value(2) + offset - 1,
                        t.Value(3) + offset - 1,
                    )
                    for t in poly.Triangles()
                ]
                triangles.append(face_triangles)

                # solid_verticles

                offset += poly.NbNodes()

            else:
                # print("found face in existing faces, reusing triangles")
                for key_s, value in triangles_on_solids_faces.items():
                    for key_f, face in value.items():
                        if key_f == f.hashCode():
                            # print(f"found face {f.hashCode()}")
                            face_triangles = triangles_on_solids_faces[key_s][key_f]
                            # triangles.append(face_triangles)
                # triangles_on_solids_faces[s.hashCode()]

            # new_code = str(f.hashCode()) + "____" + str(loop_counter)
            triangles_on_solids_faces[s.hashCode()][f.hashCode()] = face_triangles
            # face_verticles
        # else:
        # triangles_on_solids_faces[s.hashCode()][f.hashCode()] = face_triangles

    list_of_triangles_per_solid = []
    for key, value in triangles_on_solids_faces.items():
        # print(key)
        triangles_on_solid = []
        for key, face in value.items():
            # print("    ", key, face)
            triangles_on_solid = triangles_on_solid + face
        list_of_triangles_per_solid.append(triangles_on_solid)
    # for vertice in vertices:
    # print(vertice)
    # print(len(vertices))

    return vertices, list_of_triangles_per_solid
