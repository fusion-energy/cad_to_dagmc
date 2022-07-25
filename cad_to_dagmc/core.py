import numpy as np
from vertices_to_h5m import vertices_to_h5m
from pathlib import Path
import dagmc_h5m_file_inspector as di
import openmc
import openmc_data_downloader as odd
import math

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
    - h5m files can be used a transport geometry in DAGMC with OpenMC 
"""


from cadquery import importers
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
# from cadquery.occ_impl import shapes
import OCP
import cadquery as cq
from vertices_to_h5m import vertices_to_h5m
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation

def load_stp_file(filename: str, scale_factor: float = 1.0):
    """Loads a stp file and makes the 3D solid and wires available for use.
    Args:
        filename: the filename used to save the html graph.
        scale_factor: a scaling factor to apply to the geometry that can be
            used to increase the size or decrease the size of the geometry.
            Useful when converting the geometry to cm for use in neutronics
            simulations.
    Returns:
        CadQuery.solid, CadQuery.Wires: solid and wires belonging to the object
    """

    part = importers.importStep(str(filename)).val()

    if scale_factor == 1:
        scaled_part = part
    else:
        scaled_part = part.scale(scale_factor)

    solid = scaled_part

    return solid


def merge_surfaces(geometry):
    
    solids = geometry.Solids()

    bldr = OCP.BOPAlgo.BOPAlgo_Splitter()

    if len(solids) == 1:
        # merged_solid = cq.Compound(solids)
        return solids[0]

    for solid in solids:
        print(type(solid))
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

def tessellate(
   merged_solid, tolerance: float, angularTolerance: float = 0.1
):

        merged_solid.mesh(tolerance, angularTolerance)

        # vertices: List[Vector] = []
        # triangles: List[Tuple[int, int, int]] = []
        offset = 0

        all_vertices = {}
        all_triangles = {}

        vertices: List[Vector] = []
        triangles: List[Tuple[int, int, int]] = []

        for s in merged_solid.Solids():
            
            # vertices: List[Vector] = []
            # triangles: List[Tuple[int, int, int]] = []

            for f in s.Faces():
                
                # todo use hashCode() to remove duplicate vertices
                
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

                print('offset', offset)
                print('offset', offset)
                print('offset', offset)
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

        #     all_vertices[f.hashCode()] = vertices
        #     all_triangles[f.hashCode()] = triangles

        # return all_vertices, all_triangles
        return vertices, triangles
    

def tessellate_parts(merged_solid, tolerance=1):

    vert_tri_dict = {}
    for solid in merged_solid.Solids():
        
        for face in solid.Faces():
            print('    ',face.hashCode())
        
#     # meshes all the solids in the merged_solid and gets the triangles and vector_vertices
#     vector_vertices, triangles = merged_solid.tessellate(tolerance=tolerance)
    
# #     for solid in merged_solid:
# #         vector_vertices, triangles = solid.tessellate(tolerance=tolerance)
#     vertices = [(vector.x, vector.y, vector.z) for vector in vector_vertices]
#     return vertices,triangles
