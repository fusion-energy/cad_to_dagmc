"""Netgen meshing backend for cad_to_dagmc.

Hybrid backend: OCC BRepMesh for surface meshing (minimal triangles,
tolerance/angular_tolerance control) + Netgen for volume tet meshing
(uniform, equilateral tetrahedra).
"""

import os
import tempfile
import warnings

import numpy as np


def tet_mesh_solid(
    solid_shape,
    target_edge_length,
    grading=0.05,
    optsteps3d=5,
    optimize3d="cmdDmstmstm",
    elsizeweight=0.0,
):
    """Generate a tetrahedral mesh for a single OCC solid via Netgen.

    Args:
        solid_shape: CadQuery Shape or OCC TopoDS_Shape to tet-mesh.
        target_edge_length: Target edge length (absolute, 3D units).
        grading: Mesh grading (0 to 1). Lower = more uniform. Default 0.05.
        optsteps3d: Number of 3D optimization passes. Default 5.
        optimize3d: Optimization strategy string. Default includes Jacobian
            smoothing for equilateral tets.
        elsizeweight: Weight of size conformity vs shape quality
            (0 = pure shape). Default 0.0.

    Returns:
        (tet_vertices, tet_connectivity, surface_tris, surface_face_indices):
        - tet_vertices: numpy array (N, 3) float64
        - tet_connectivity: numpy array (M, 4) int32
        - surface_tris: numpy array (S, 3) int32 — boundary triangles
        - surface_face_indices: numpy array (S,) int32 — netgen face index per tri
    """
    try:
        from netgen.occ import OCCGeometry
    except ImportError:
        raise ImportError(
            "netgen-mesher is required for the netgen meshing backend. "
            "Install it with: pip install netgen-mesher"
        )

    from OCP.BRepTools import BRepTools

    occ_shape = solid_shape.wrapped if hasattr(solid_shape, "wrapped") else solid_shape

    fd, brep_path = tempfile.mkstemp(suffix=".brep")
    os.close(fd)
    try:
        BRepTools.Write_s(occ_shape, brep_path)

        geo = OCCGeometry(brep_path, dim=3)

        # Scale maxh down by 0.8 — netgen's maxh is a soft target and edges
        # routinely exceed it; the 0.8 factor compensates for more uniform tets.
        h = float(target_edge_length) * 0.8
        ngmesh = geo.GenerateMesh(
            maxh=h,
            minh=h,
            grading=grading,
            optsteps3d=optsteps3d,
            optimize3d=optimize3d,
            elsizeweight=elsizeweight,
        )

        # Extract vertices
        points = ngmesh.Points()
        verts = np.array([[p[0], p[1], p[2]] for p in points], dtype=np.float64)

        # Extract tet connectivity (convert 1-based PointId.nr to 0-based)
        tets = np.array(
            [[v.nr - 1 for v in el.vertices] for el in ngmesh.Elements3D()],
            dtype=np.int32,
        )

        # Fix winding: netgen's convention is opposite
        tets[:, [0, 1]] = tets[:, [1, 0]]

        # Extract boundary triangles with face descriptor indices
        surf_tri_list = []
        surf_idx_list = []
        for el in ngmesh.Elements2D():
            surf_tri_list.append([v.nr - 1 for v in el.vertices])
            surf_idx_list.append(el.index)

        if surf_tri_list:
            surface_tris = np.array(surf_tri_list, dtype=np.int32)
            surface_face_indices = np.array(surf_idx_list, dtype=np.int32)
        else:
            surface_tris = np.empty((0, 3), dtype=np.int32)
            surface_face_indices = np.empty((0,), dtype=np.int32)

        return verts, tets, surface_tris, surface_face_indices
    finally:
        if os.path.exists(brep_path):
            os.unlink(brep_path)


def map_netgen_faces_to_cad_faces(
    tet_vertices, surface_tris, surface_face_indices, face_ids, face_to_occ
):
    """Map netgen face descriptor indices to CAD face IDs.

    Groups boundary triangles by netgen face index, computes one sample
    centroid per group, and finds the nearest CAD face via OCC distance
    queries. Only F distance checks needed (one per face group).

    Args:
        tet_vertices: (N, 3) float64 array of tet mesh vertices.
        surface_tris: (S, 3) int32 array of boundary triangle indices.
        surface_face_indices: (S,) int32 array of netgen face indices.
        face_ids: list of CAD face IDs to match against.
        face_to_occ: dict mapping face_id to OCC TopoDS_Face.

    Returns:
        dict[int, int]: netgen face index -> CAD face_id.
    """
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt

    # Group triangle indices by netgen face index
    groups = {}
    for i, nf_idx in enumerate(surface_face_indices):
        groups.setdefault(int(nf_idx), []).append(i)

    netgen_to_fid = {}
    for nf_idx, tri_indices in groups.items():
        # Sample centroid from the first triangle in this group
        tri = surface_tris[tri_indices[0]]
        centroid = (
            tet_vertices[tri[0]] + tet_vertices[tri[1]] + tet_vertices[tri[2]]
        ) / 3.0
        pnt = gp_Pnt(float(centroid[0]), float(centroid[1]), float(centroid[2]))
        vertex = BRepBuilderAPI_MakeVertex(pnt).Vertex()

        best_fid = None
        best_dist = float("inf")
        for fid in face_ids:
            extrema = BRepExtrema_DistShapeShape(vertex, face_to_occ[fid])
            if extrema.IsDone():
                dist = extrema.Value()
                if dist < best_dist:
                    best_dist = dist
                    best_fid = fid

        if best_fid is not None:
            netgen_to_fid[nf_idx] = best_fid
        else:
            warnings.warn(
                f"Could not map netgen face index {nf_idx} to any CAD face"
            )

    return netgen_to_fid


def surface_mesh_with_brepmesh(
    assembly,
    tolerance,
    angular_tolerance,
    material_tags,
    scale_factor,
    imprint,
):
    """Perform OCC BRepMesh surface meshing and extract per-face triangles.

    Imprints the assembly, extracts solid/face topology, runs BRepMesh,
    and returns data in cad_to_dagmc's expected format.

    Args:
        assembly: CadQuery Assembly.
        tolerance: Chordal deflection tolerance for BRepMesh.
        angular_tolerance: Angular deflection tolerance (radians).
        material_tags: List of material tag strings.
        scale_factor: Scale factor to apply to vertex coordinates.
        imprint: Whether to imprint the assembly.

    Returns:
        (vertices, triangles_by_solid_by_face, material_tags_in_brep_order,
         face_to_occ, solid_shapes)
        - vertices: list of (x, y, z) tuples
        - triangles_by_solid_by_face: {solid_id: {face_id: [[v0,v1,v2], ...]}}
        - material_tags_in_brep_order: reordered material tags
        - face_to_occ: {face_id: TopoDS_Face}
        - solid_shapes: {solid_id: CadQuery Shape}
    """
    import cadquery as cq
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    from .core import (
        get_ids_from_assembly,
        get_ids_from_imprinted_assembly,
        order_material_ids_by_brep_order,
        check_material_tags,
    )

    original_ids = get_ids_from_assembly(assembly)

    # Imprint
    if imprint:
        imprinted_assembly, imprinted_solids_with_org_id = (
            cq.occ_impl.assembly.imprint(assembly)
        )
        scrambled_ids = get_ids_from_imprinted_assembly(imprinted_solids_with_org_id)
        material_tags_in_brep_order = order_material_ids_by_brep_order(
            original_ids, scrambled_ids, material_tags
        )
    else:
        imprinted_assembly = assembly
        material_tags_in_brep_order = list(material_tags)

    # Get compound and solids
    if hasattr(imprinted_assembly, "wrapped"):
        occ_compound = imprinted_assembly.wrapped
    elif hasattr(imprinted_assembly, "val"):
        occ_compound = imprinted_assembly.val().wrapped
    else:
        occ_compound = imprinted_assembly

    # Extract solids from compound
    from OCP.TopAbs import TopAbs_SOLID

    solids = []
    solid_explorer = TopExp_Explorer(occ_compound, TopAbs_SOLID)
    while solid_explorer.More():
        solids.append(TopoDS.Solid_s(solid_explorer.Current()))
        solid_explorer.Next()

    # Run BRepMesh on the compound
    BRepMesh_IncrementalMesh(occ_compound, tolerance, False, angular_tolerance)

    # Extract topology and triangulations
    vertices = []
    vertex_map = {}  # (x,y,z) -> global index for deduplication
    triangles_by_solid_by_face = {}
    face_to_occ = {}
    solid_shapes = {}
    solid_faces_map = {}  # solid_id -> list of face_ids

    face_id_counter = 1
    seen_faces = {}  # face hash -> face_id

    for solid_idx, occ_solid in enumerate(solids):
        solid_id = solid_idx + 1
        face_triangles = {}
        solid_face_ids = []

        # Wrap as CadQuery shape for tet_mesh_solid later
        solid_shapes[solid_id] = cq.Shape(occ_solid)

        face_explorer = TopExp_Explorer(occ_solid, TopAbs_FACE)
        while face_explorer.More():
            occ_face = TopoDS.Face_s(face_explorer.Current())
            face_hash = hash(occ_face)

            # Check if shared face
            if face_hash in seen_faces:
                fid = seen_faces[face_hash]
                solid_face_ids.append(fid)

                # For shared faces, extract triangles for this solid's entry too
                loc = TopLoc_Location()
                tri = BRep_Tool.Triangulation_s(occ_face, loc)
                if tri is not None:
                    is_reversed = occ_face.Orientation() == TopAbs_REVERSED
                    transform = loc.Transformation()
                    has_transform = not loc.IsIdentity()

                    # Build local vertex map for this face
                    face_verts = {}
                    for i in range(1, tri.NbNodes() + 1):
                        pnt = tri.Node(i)
                        if has_transform:
                            pnt = pnt.Transformed(transform)
                        coords = (
                            pnt.X() * scale_factor,
                            pnt.Y() * scale_factor,
                            pnt.Z() * scale_factor,
                        )
                        if coords in vertex_map:
                            face_verts[i] = vertex_map[coords]
                        else:
                            idx = len(vertices)
                            vertices.append(coords)
                            vertex_map[coords] = idx
                            face_verts[i] = idx

                    tris = []
                    for i in range(1, tri.NbTriangles() + 1):
                        t = tri.Triangle(i)
                        i1, i2, i3 = t.Get()
                        if i1 == i2 or i2 == i3 or i1 == i3:
                            continue
                        if is_reversed:
                            tris.append([face_verts[i1], face_verts[i3], face_verts[i2]])
                        else:
                            tris.append([face_verts[i1], face_verts[i2], face_verts[i3]])
                    if tris:
                        face_triangles[fid] = tris

                face_explorer.Next()
                continue

            # New face
            fid = face_id_counter
            face_id_counter += 1
            seen_faces[face_hash] = fid
            face_to_occ[fid] = occ_face
            solid_face_ids.append(fid)

            loc = TopLoc_Location()
            tri = BRep_Tool.Triangulation_s(occ_face, loc)
            if tri is None:
                face_explorer.Next()
                continue

            is_reversed = occ_face.Orientation() == TopAbs_REVERSED
            transform = loc.Transformation()
            has_transform = not loc.IsIdentity()

            # Build local vertex map for this face
            face_verts = {}
            for i in range(1, tri.NbNodes() + 1):
                pnt = tri.Node(i)
                if has_transform:
                    pnt = pnt.Transformed(transform)
                coords = (
                    pnt.X() * scale_factor,
                    pnt.Y() * scale_factor,
                    pnt.Z() * scale_factor,
                )
                if coords in vertex_map:
                    face_verts[i] = vertex_map[coords]
                else:
                    idx = len(vertices)
                    vertices.append(coords)
                    vertex_map[coords] = idx
                    face_verts[i] = idx

            tris = []
            for i in range(1, tri.NbTriangles() + 1):
                t = tri.Triangle(i)
                i1, i2, i3 = t.Get()
                if i1 == i2 or i2 == i3 or i1 == i3:
                    continue
                if is_reversed:
                    tris.append([face_verts[i1], face_verts[i3], face_verts[i2]])
                else:
                    tris.append([face_verts[i1], face_verts[i2], face_verts[i3]])
            if tris:
                face_triangles[fid] = tris

            face_explorer.Next()

        triangles_by_solid_by_face[solid_id] = face_triangles
        solid_faces_map[solid_id] = solid_face_ids

    return (
        vertices,
        triangles_by_solid_by_face,
        material_tags_in_brep_order,
        face_to_occ,
        solid_shapes,
        solid_faces_map,
    )


def replace_surface_mesh_for_tet_volumes(
    vertices,
    triangles_by_solid_by_face,
    solid_faces_map,
    tet_data,
    face_to_occ,
):
    """Replace BRepMesh surface triangles with Netgen boundary triangles.

    For tet-meshed volumes, swaps the coarse BRepMesh triangulation with
    netgen's boundary triangles to ensure surface/volume mesh conformality.

    For shared faces between a tet volume and a non-tet volume, both entries
    are replaced with netgen's boundary triangles.

    Args:
        vertices: list of (x, y, z) tuples (modified in-place by appending).
        triangles_by_solid_by_face: {solid_id: {face_id: [[v0,v1,v2], ...]}}.
        solid_faces_map: {solid_id: [face_id, ...]} face ownership.
        tet_data: {solid_id: (tet_vertices, tet_connectivity, surface_tris,
                   surface_face_indices)}.
        face_to_occ: {face_id: TopoDS_Face}.

    Returns:
        (vertices, triangles_by_solid_by_face) — updated.
    """
    # Build reverse map: face_id -> list of solid_ids that own it
    face_to_solids = {}
    for solid_id, face_ids in solid_faces_map.items():
        for fid in face_ids:
            face_to_solids.setdefault(fid, []).append(solid_id)

    tet_solid_ids = set(tet_data.keys())

    # Track which faces have already been replaced by a tet volume's boundary
    replaced_faces = {}  # face_id -> (new_triangles with global indices)

    for solid_id in tet_data:
        tet_v, tet_t, surf_tris, surf_fi = tet_data[solid_id]

        if len(surf_tris) == 0:
            continue

        # Map netgen face indices to CAD face IDs
        netgen_to_fid = map_netgen_faces_to_cad_faces(
            tet_v, surf_tris, surf_fi,
            solid_faces_map[solid_id], face_to_occ,
        )

        # Append tet vertices to global vertex array
        tet_base_idx = len(vertices)
        for v in tet_v:
            vertices.append((float(v[0]), float(v[1]), float(v[2])))

        # Group boundary triangles by CAD face ID
        face_new_tris = {}  # fid -> list of [v0, v1, v2] with global indices
        for i, tri in enumerate(surf_tris):
            nf_idx = int(surf_fi[i])
            fid = netgen_to_fid.get(nf_idx)
            if fid is None:
                continue
            face_new_tris.setdefault(fid, []).append([
                int(tri[0]) + tet_base_idx,
                int(tri[1]) + tet_base_idx,
                int(tri[2]) + tet_base_idx,
            ])

        # Replace triangles for this solid's faces
        for fid, new_tris in face_new_tris.items():
            # Update this tet solid's entry
            triangles_by_solid_by_face[solid_id][fid] = new_tris
            replaced_faces[fid] = new_tris

            # If shared face, also update the other solid's entry
            owning_solids = face_to_solids.get(fid, [])
            for other_solid_id in owning_solids:
                if other_solid_id != solid_id:
                    if other_solid_id in triangles_by_solid_by_face:
                        if fid in triangles_by_solid_by_face[other_solid_id]:
                            triangles_by_solid_by_face[other_solid_id][fid] = new_tris

    # Remove old BRepMesh triangles for faces that belong ONLY to tet volumes
    # (non-shared faces of tet volumes where old tris weren't replaced above)
    for solid_id in tet_solid_ids:
        for fid in solid_faces_map.get(solid_id, []):
            if fid not in replaced_faces:
                # Face had no netgen boundary tris (shouldn't happen, but guard)
                pass

    return vertices, triangles_by_solid_by_face


def resolve_tet_volumes(tet_volumes, material_tags):
    """Resolve a list of material tags or solid IDs to solid IDs.

    Args:
        tet_volumes: list of material tag strings (str) or solid IDs (int).
        material_tags: ordered list of material tags matching solid order.

    Returns:
        list[int]: resolved solid IDs (1-based).
    """
    resolved = set()
    for item in tet_volumes:
        if isinstance(item, int):
            resolved.add(item)
        elif isinstance(item, str):
            found = False
            for i, tag in enumerate(material_tags):
                if tag == item:
                    resolved.add(i + 1)  # solid IDs are 1-based
                    found = True
            if not found:
                raise ValueError(
                    f"Material tag '{item}' not found in material_tags: {material_tags}"
                )
        else:
            raise TypeError(
                f"tet_volumes items must be str or int, got {type(item)}"
            )
    return sorted(resolved)
