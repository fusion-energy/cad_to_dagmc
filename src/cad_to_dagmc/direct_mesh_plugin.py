# This is a temporary solution until we have to_mesh like functionality in a
# PYPI distributed version of CadQuery.
# This code is adapted from the cadquery-direct-mesh-plugin repository:
# https://github.com/jmwright/cadquery-direct-mesh-plugin

#                                  Apache License
#                            Version 2.0, January 2004
#                         http://www.apache.org/licenses/

#    TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

#    1. Definitions.

#       "License" shall mean the terms and conditions for use, reproduction,
#       and distribution as defined by Sections 1 through 9 of this document.

#       "Licensor" shall mean the copyright owner or entity authorized by
#       the copyright owner that is granting the License.

#       "Legal Entity" shall mean the union of the acting entity and all
#       other entities that control, are controlled by, or are under common
#       control with that entity. For the purposes of this definition,
#       "control" means (i) the power, direct or indirect, to cause the
#       direction or management of such entity, whether by contract or
#       otherwise, or (ii) ownership of fifty percent (50%) or more of the
#       outstanding shares, or (iii) beneficial ownership of such entity.

#       "You" (or "Your") shall mean an individual or Legal Entity
#       exercising permissions granted by this License.

#       "Source" form shall mean the preferred form for making modifications,
#       including but not limited to software source code, documentation
#       source, and configuration files.

#       "Object" form shall mean any form resulting from mechanical
#       transformation or translation of a Source form, including but
#       not limited to compiled object code, generated documentation,
#       and conversions to other media types.

#       "Work" shall mean the work of authorship, whether in Source or
#       Object form, made available under the License, as indicated by a
#       copyright notice that is included in or attached to the work
#       (an example is provided in the Appendix below).

#       "Derivative Works" shall mean any work, whether in Source or Object
#       form, that is based on (or derived from) the Work and for which the
#       editorial revisions, annotations, elaborations, or other modifications
#       represent, as a whole, an original work of authorship. For the purposes
#       of this License, Derivative Works shall not include works that remain
#       separable from, or merely link (or bind by name) to the interfaces of,
#       the Work and Derivative Works thereof.

#       "Contribution" shall mean any work of authorship, including
#       the original version of the Work and any modifications or additions
#       to that Work or Derivative Works thereof, that is intentionally
#       submitted to Licensor for inclusion in the Work by the copyright owner
#       or by an individual or Legal Entity authorized to submit on behalf of
#       the copyright owner. For the purposes of this definition, "submitted"
#       means any form of electronic, verbal, or written communication sent
#       to the Licensor or its representatives, including but not limited to
#       communication on electronic mailing lists, source code control systems,
#       and issue tracking systems that are managed by, or on behalf of, the
#       Licensor for the purpose of discussing and improving the Work, but
#       excluding communication that is conspicuously marked or otherwise
#       designated in writing by the copyright owner as "Not a Contribution."

#       "Contributor" shall mean Licensor and any individual or Legal Entity
#       on behalf of whom a Contribution has been received by Licensor and
#       subsequently incorporated within the Work.

#    2. Grant of Copyright License. Subject to the terms and conditions of
#       this License, each Contributor hereby grants to You a perpetual,
#       worldwide, non-exclusive, no-charge, royalty-free, irrevocable
#       copyright license to reproduce, prepare Derivative Works of,
#       publicly display, publicly perform, sublicense, and distribute the
#       Work and such Derivative Works in Source or Object form.

#    3. Grant of Patent License. Subject to the terms and conditions of
#       this License, each Contributor hereby grants to You a perpetual,
#       worldwide, non-exclusive, no-charge, royalty-free, irrevocable
#       (except as stated in this section) patent license to make, have made,
#       use, offer to sell, sell, import, and otherwise transfer the Work,
#       where such license applies only to those patent claims licensable
#       by such Contributor that are necessarily infringed by their
#       Contribution(s) alone or by combination of their Contribution(s)
#       with the Work to which such Contribution(s) was submitted. If You
#       institute patent litigation against any entity (including a
#       cross-claim or counterclaim in a lawsuit) alleging that the Work
#       or a Contribution incorporated within the Work constitutes direct
#       or contributory patent infringement, then any patent licenses
#       granted to You under this License for that Work shall terminate
#       as of the date such litigation is filed.

#    4. Redistribution. You may reproduce and distribute copies of the
#       Work or Derivative Works thereof in any medium, with or without
#       modifications, and in Source or Object form, provided that You
#       meet the following conditions:

#       (a) You must give any other recipients of the Work or
#           Derivative Works a copy of this License; and

#       (b) You must cause any modified files to carry prominent notices
#           stating that You changed the files; and

#       (c) You must retain, in the Source form of any Derivative Works
#           that You distribute, all copyright, patent, trademark, and
#           attribution notices from the Source form of the Work,
#           excluding those notices that do not pertain to any part of
#           the Derivative Works; and

#       (d) If the Work includes a "NOTICE" text file as part of its
#           distribution, then any Derivative Works that You distribute must
#           include a readable copy of the attribution notices contained
#           within such NOTICE file, excluding those notices that do not
#           pertain to any part of the Derivative Works, in at least one
#           of the following places: within a NOTICE text file distributed
#           as part of the Derivative Works; within the Source form or
#           documentation, if provided along with the Derivative Works; or,
#           within a display generated by the Derivative Works, if and
#           wherever such third-party notices normally appear. The contents
#           of the NOTICE file are for informational purposes only and
#           do not modify the License. You may add Your own attribution
#           notices within Derivative Works that You distribute, alongside
#           or as an addendum to the NOTICE text from the Work, provided
#           that such additional attribution notices cannot be construed
#           as modifying the License.

#       You may add Your own copyright statement to Your modifications and
#       may provide additional or different license terms and conditions
#       for use, reproduction, or distribution of Your modifications, or
#       for any such Derivative Works as a whole, provided Your use,
#       reproduction, and distribution of the Work otherwise complies with
#       the conditions stated in this License.

#    5. Submission of Contributions. Unless You explicitly state otherwise,
#       any Contribution intentionally submitted for inclusion in the Work
#       by You to the Licensor shall be under the terms and conditions of
#       this License, without any additional terms or conditions.
#       Notwithstanding the above, nothing herein shall supersede or modify
#       the terms of any separate license agreement you may have executed
#       with Licensor regarding such Contributions.

#    6. Trademarks. This License does not grant permission to use the trade
#       names, trademarks, service marks, or product names of the Licensor,
#       except as required for reasonable and customary use in describing the
#       origin of the Work and reproducing the content of the NOTICE file.

#    7. Disclaimer of Warranty. Unless required by applicable law or
#       agreed to in writing, Licensor provides the Work (and each
#       Contributor provides its Contributions) on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#       implied, including, without limitation, any warranties or conditions
#       of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
#       PARTICULAR PURPOSE. You are solely responsible for determining the
#       appropriateness of using or redistributing the Work and assume any
#       risks associated with Your exercise of permissions under this License.

#    8. Limitation of Liability. In no event and under no legal theory,
#       whether in tort (including negligence), contract, or otherwise,
#       unless required by applicable law (such as deliberate and grossly
#       negligent acts) or agreed to in writing, shall any Contributor be
#       liable to You for damages, including any direct, indirect, special,
#       incidental, or consequential damages of any character arising as a
#       result of this License or out of the use or inability to use the
#       Work (including but not limited to damages for loss of goodwill,
#       work stoppage, computer failure or malfunction, or any and all
#       other commercial damages or losses), even if such Contributor
#       has been advised of the possibility of such damages.

#    9. Accepting Warranty or Additional Liability. While redistributing
#       the Work or Derivative Works thereof, You may choose to offer,
#       and charge a fee for, acceptance of support, warranty, indemnity,
#       or other liability obligations and/or rights consistent with this
#       License. However, in accepting such obligations, You may act only
#       on Your own behalf and on Your sole responsibility, not on behalf
#       of any other Contributor, and only if You agree to indemnify,
#       defend, and hold each Contributor harmless for any liability
#       incurred by, or claims asserted against, such Contributor by reason
#       of your accepting any such warranty or additional liability.

#    END OF TERMS AND CONDITIONS

#    APPENDIX: How to apply the Apache License to your work.

#       To apply the Apache License to your work, attach the following
#       boilerplate notice, with the fields enclosed by brackets "[]"
#       replaced with your own identifying information. (Don't include
#       the brackets!)  The text should be enclosed in the appropriate
#       comment syntax for the file format. We also recommend that a
#       file or class name and description of purpose be included on the
#       same "printed page" as the copyright notice for easier
#       identification within third-party archives.

#    Copyright [yyyy] [name of copyright owner]

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP import GCPnts, BRepAdaptor
from OCP.TopAbs import TopAbs_REVERSED, TopAbs_IN
from OCP.gp import gp_Pnt, gp_Vec
import cadquery as cq


def _is_interior_face(face, solid, tolerance=0.01):
    """
    Determine if a face is interior to a solid (like a cavity wall).

    This is more robust than just checking face orientation, as it considers
    the geometric relationship between the face and the solid.
    """
    # Get geometric surface and parameter bounds
    surf = BRep_Tool.Surface_s(face.wrapped)
    u_min, u_max, v_min, v_max = face._uvBounds()

    # # Take center point in UV space on the face
    u = (u_min + u_max) * 0.5
    v = (v_min + v_max) * 0.5
    face_pnt = surf.Value(u, v)

    # Determine if the face is most likely inside the solid
    is_inside = solid.isInside((face_pnt.X(), face_pnt.Y(), face_pnt.Z()))

    # Determine if the normal of the face points generally towards to the center of the solid
    is_pointing_inward = False
    face_normal = face.normalAt((face_pnt.X(), face_pnt.Y(), face_pnt.Z()))
    solid_center = solid.Center()

    to_center = gp_Vec(face_pnt, gp_Pnt(solid_center.x, solid_center.y, solid_center.z))

    # Dot product: negative = toward, positive = away
    dot = face_normal.dot(cq.Vector(to_center.Normalized()))

    if dot < 0:
        is_pointing_inward = False
    else:
        is_pointing_inward = True

    # If the face seems to be inside the solid and its normal points inwards, it should be an internal face
    is_internal_face = False
    if is_inside and is_pointing_inward:
        is_internal_face = True

    return is_internal_face


def to_mesh(
    assembly,
    imprint=True,
    tolerance=0.1,
    angular_tolerance=0.1,
    scale_factor=1.0,
    include_brep_edges=False,
    include_brep_vertices=False,
):
    """
    Converts an assembly to a custom mesh format defined by the CadQuery team.

    :param imprint: Whether or not the assembly should be imprinted
    :param tolerance: Tessellation tolerance for mesh generation
    :param angular_tolerance: Angular tolerance for tessellation
    :param include_brep_edges: Whether to include BRep edge segments
    :param include_brep_vertices: Whether to include BRep vertices
    """

    # To keep track of the vertices and triangles in the mesh
    vertices = []
    vertex_map = {}
    solids = []
    solid_face_triangle = {}
    imprinted_assembly = None
    imprinted_solids_with_orginal_ids = None
    solid_colors = []
    solid_locs = []
    solid_brep_edge_segments = []
    solid_brep_vertices = []

    # Imprinted assemblies end up being compounds, whereas you have to step through each of the
    # parts in an assembly and extract the solids.
    if imprint:
        print("Imprinting assembly for mesh export...")
        # Imprint the assembly and process it as a compound
        (
            imprinted_assembly,
            imprinted_solids_with_orginal_ids,
        ) = cq.occ_impl.assembly.imprint(assembly)

        # Extract the solids from the imprinted assembly because we should not mesh the compound
        for solid in imprinted_assembly.Solids():
            solids.append(solid)

        # Keep track of the colors and location of each of the solids
        solid_colors.append((0.5, 0.5, 0.5, 1.0))
        solid_locs.append(cq.Location())
    else:
        # Step through every child in the assembly and save their solids
        for child in assembly.children:
            # Make sure we end up with a base shape
            obj = child.obj
            if type(child.obj).__name__ == "Workplane":
                solids.append(obj.val())
            else:
                solids.append(obj)

            # Use the color set for the assembly component, or use a default color
            if child.color:
                solid_colors.append(child.color.toTuple())
            else:
                solid_colors.append((0.5, 0.5, 0.5, 1.0))

            # Keep track of the location of each of the solids
            solid_locs.append(child.loc)

    # Solid and face IDs need to be unique unless they are a shared face
    solid_idx = 1  # We start at 1 to mimic gmsh
    face_idx = 1  # We start at id of 1 to mimic gmsh

    # Step through all of the collected solids and their respective faces to get the vertices
    for solid in solids:
        print(f'Tessellating solid {solid_idx} of {len(solids)}')
        # Reset this each time so that we get the correct number of faces per solid
        face_triangles = {}

        # Order the faces in order of area, largest first
        sorted_faces = []
        face_areas = []
        for face in solid.Faces():
            area = face.Area()
            sorted_faces.append((face, area))
            face_areas.append(area)

        # Sort by area (largest first)
        sorted_faces.sort(key=lambda x: x[1], reverse=False)

        # Extract just the sorted faces if you need them separately
        sorted_face_list = [face_info[0] for face_info in sorted_faces]

        # Walk through all the faces
        for face in sorted_face_list:
            # Figure out if the face has a reversed orientation so we can handle the triangles accordingly
            is_reversed = False
            if face.wrapped.Orientation() == TopAbs_REVERSED:
                is_reversed = True

            # Location information of the face to place the vertices and edges correctly
            loc = TopLoc_Location()

            # Perform the tessellation
            BRepMesh_IncrementalMesh(face.wrapped, tolerance, False, angular_tolerance)
            face_mesh = BRep_Tool.Triangulation_s(face.wrapped, loc)

            # If this is not an imprinted assembly, override the location of the triangulation
            if not imprint:
                loc = solid_locs[solid_idx - 1].wrapped

            # Save the transformation so that we can place vertices in the correct locations later
            Trsf = loc.Transformation()

            # Pre-process all vertices from the face mesh for better performance
            face_vertices = {}  # Map from face mesh node index to global vertex index
            for node_idx in range(1, face_mesh.NbNodes() + 1):
                node = face_mesh.Node(node_idx)
                v_trsf = node.Transformed(Trsf)
                vertex_coords = (
                    v_trsf.X() * scale_factor,
                    v_trsf.Y() * scale_factor,
                    v_trsf.Z() * scale_factor,
                )

                # Use dictionary for O(1) lookup instead of O(n) list operations
                if vertex_coords in vertex_map:
                    face_vertices[node_idx] = vertex_map[vertex_coords]
                else:
                    global_vertex_idx = len(vertices)
                    vertices.append(vertex_coords)
                    vertex_map[vertex_coords] = global_vertex_idx
                    face_vertices[node_idx] = global_vertex_idx

            # Step through the triangles of the face
            cur_triangles = []
            for i in range(1, face_mesh.NbTriangles() + 1):
                # Get the current triangle and its index vertices
                cur_tri = face_mesh.Triangle(i)
                idx_1, idx_2, idx_3 = cur_tri.Get()

                # Look up pre-processed vertex indices - O(1) operation
                if is_reversed:
                    triangle_vertex_indices = [
                        face_vertices[idx_1],
                        face_vertices[idx_3],
                        face_vertices[idx_2],
                    ]
                else:
                    triangle_vertex_indices = [
                        face_vertices[idx_1],
                        face_vertices[idx_2],
                        face_vertices[idx_3],
                    ]

                cur_triangles.append(triangle_vertex_indices)

            # Save this triangle for the current face
            face_triangles[face_idx] = cur_triangles

            # Move to the next face
            face_idx += 1

        solid_face_triangle[solid_idx] = face_triangles

        # If the caller wants to track edges, include them
        if include_brep_edges:
            # If this is not an imprinted assembly, override the location of the edges
            loc = TopLoc_Location()
            if not imprint:
                loc = solid_locs[solid_idx - 1].wrapped

            # Save the transformation so that we can place vertices in the correct locations later
            Trsf = loc.Transformation()

            # Add CadQuery-reported edges
            current_segments = []
            for edge in solid.edges():
                # We need to handle different kinds of edges differently
                gt = edge.geomType()

                # Line edges are just point to point
                if gt == "LINE":
                    start = edge.startPoint().toPnt()
                    end = edge.endPoint().toPnt()

                    # Apply the assembly location transformation to each vertex
                    start_trsf = start.Transformed(Trsf)
                    located_start = (start_trsf.X(), start_trsf.Y(), start_trsf.Z())
                    end_trsf = end.Transformed(Trsf)
                    located_end = (end_trsf.X(), end_trsf.Y(), end_trsf.Z())

                    # Save the start and end points for the edge
                    current_segments.append([located_start, located_end])
                # If dealing with some sort of arc, discretize it into individual lines
                elif gt in ("CIRCLE", "ARC", "SPLINE", "BSPLINE", "ELLIPSE"):
                    # Discretize the curve
                    disc = GCPnts.GCPnts_TangentialDeflection(
                        BRepAdaptor.BRepAdaptor_Curve(edge.wrapped),
                        tolerance,
                        angular_tolerance,
                    )

                    # Add each of the discretized sections to the edge list
                    if disc.NbPoints() > 1:
                        for i in range(2, disc.NbPoints() + 1):
                            p_0 = disc.Value(i - 1)
                            p_1 = disc.Value(i)

                            # Apply the assembly location transformation to each vertex
                            p_0_trsf = p_0.Transformed(Trsf)
                            located_p_0 = (p_0_trsf.X(), p_0_trsf.Y(), p_0_trsf.Z())
                            p_1_trsf = p_1.Transformed(Trsf)
                            located_p_1 = (p_1_trsf.X(), p_1_trsf.Y(), p_1_trsf.Z())

                            # Save the start and end points for the edge
                            current_segments.append([located_p_0, located_p_1])

            solid_brep_edge_segments.append(current_segments)

        # Add CadQuery-reported vertices, if requested
        if include_brep_vertices:
            # If this is not an imprinted assembly, override the location of the edges
            loc = TopLoc_Location()
            if not imprint:
                loc = solid_locs[solid_idx - 1].wrapped

            # Save the transformation so that we can place vertices in the correct locations later
            Trsf = loc.Transformation()

            current_vertices = []
            for vertex in solid.vertices():
                p = BRep_Tool.Pnt_s(vertex.wrapped)

                # Apply the assembly location transformation to each vertex
                p_trsf = p.Transformed(Trsf)
                located_p = (p_trsf.X(), p_trsf.Y(), p_trsf.Z())
                current_vertices.append(located_p)

            solid_brep_vertices.append(current_vertices)

        # Move to the next solid
        solid_idx += 1

    return {
        "vertices": vertices,
        "solid_face_triangle_vertex_map": solid_face_triangle,
        "solid_colors": solid_colors,
        "solid_brep_edge_segments": solid_brep_edge_segments,
        "solid_brep_vertices": solid_brep_vertices,
        "imprinted_assembly": imprinted_assembly,
        "imprinted_solids_with_orginal_ids": imprinted_solids_with_orginal_ids,
    }
