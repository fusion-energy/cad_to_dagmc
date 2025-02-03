from pathlib import Path
import cadquery as cq
import gmsh
import numpy as np
from cadquery import importers
from pymoab import core, types
import tempfile
import warnings


def define_moab_core_and_tags() -> tuple[core.Core, dict]:
    """Creates a MOAB Core instance which can be built up by adding sets of
    triangles to the instance

    Returns:
        (pymoab Core): A pymoab.core.Core() instance
        (pymoab tag_handle): A pymoab.core.tag_get_handle() instance
    """

    # create pymoab instance
    moab_core = core.Core()

    tags = dict()

    sense_tag_name = "GEOM_SENSE_2"
    sense_tag_size = 2
    tags["surf_sense"] = moab_core.tag_get_handle(
        sense_tag_name,
        sense_tag_size,
        types.MB_TYPE_HANDLE,
        types.MB_TAG_SPARSE,
        create_if_missing=True,
    )

    tags["category"] = moab_core.tag_get_handle(
        types.CATEGORY_TAG_NAME,
        types.CATEGORY_TAG_SIZE,
        types.MB_TYPE_OPAQUE,
        types.MB_TAG_SPARSE,
        create_if_missing=True,
    )

    tags["name"] = moab_core.tag_get_handle(
        types.NAME_TAG_NAME,
        types.NAME_TAG_SIZE,
        types.MB_TYPE_OPAQUE,
        types.MB_TAG_SPARSE,
        create_if_missing=True,
    )

    tags["geom_dimension"] = moab_core.tag_get_handle(
        types.GEOM_DIMENSION_TAG_NAME,
        1,
        types.MB_TYPE_INTEGER,
        types.MB_TAG_DENSE,
        create_if_missing=True,
    )

    # Global ID is a default tag, just need the name to retrieve
    tags["global_id"] = moab_core.tag_get_handle(types.GLOBAL_ID_TAG_NAME)

    return moab_core, tags


def vertices_to_h5m(
    vertices: list[tuple[float, float, float]] | list["cadquery.occ_impl.geom.Vector"],
    triangles_by_solid_by_face: list[list[tuple[int, int, int]]],
    material_tags: list[str],
    h5m_filename: str = "dagmc.h5m",
    implicit_complement_material_tag: str | None = None,
):
    """Converts vertices and triangle sets into a tagged h5m file compatible
    with DAGMC enabled neutronics simulations

    Args:
        vertices:
        triangles:
        material_tags:
        h5m_filename:
        implicit_complement_material_tag:
    """

    if len(material_tags) != len(triangles_by_solid_by_face):
        msg = f"The number of material_tags provided is {len(material_tags)} and the number of sets of triangles is {len(triangles_by_solid_by_face)}. You must provide one material_tag for every triangle set"
        raise ValueError(msg)

    # limited attribute checking to see if user passed in a list of CadQuery vectors
    if hasattr(vertices[0], "x") and hasattr(vertices[0], "y") and hasattr(vertices[0], "z"):
        vertices_floats = []
        for vert in vertices:
            vertices_floats.append((vert.x, vert.y, vert.z))
    else:
        vertices_floats = vertices

    face_ids_with_solid_ids = {}
    for solid_id, triangles_on_each_face in triangles_by_solid_by_face.items():
        for face_id, triangles_on_face in triangles_on_each_face.items():
            if face_id in face_ids_with_solid_ids.keys():
                face_ids_with_solid_ids[face_id].append(solid_id)
            else:
                face_ids_with_solid_ids[face_id] = [solid_id]

    moab_core, tags = define_moab_core_and_tags()

    volume_sets_by_solid_id = {}
    for material_tag, (solid_id, triangles_on_each_face) in zip(
        material_tags, triangles_by_solid_by_face.items()
    ):
        volume_set = moab_core.create_meshset()
        volume_sets_by_solid_id[solid_id] = volume_set

    added_surfaces_ids = {}
    for material_tag, (solid_id, triangles_on_each_face) in zip(
        material_tags, triangles_by_solid_by_face.items()
    ):
        volume_set = volume_sets_by_solid_id[solid_id]

        moab_core.tag_set_data(tags["global_id"], volume_set, solid_id)
        moab_core.tag_set_data(tags["geom_dimension"], volume_set, 3)
        moab_core.tag_set_data(tags["category"], volume_set, "Volume")

        group_set = moab_core.create_meshset()
        moab_core.tag_set_data(tags["category"], group_set, "Group")
        moab_core.tag_set_data(tags["name"], group_set, f"mat:{material_tag}")
        moab_core.tag_set_data(tags["global_id"], group_set, solid_id)
        # moab_core.tag_set_data(tags["geom_dimension"], group_set, 4)

        for face_id, triangles_on_face in triangles_on_each_face.items():
            if face_id not in added_surfaces_ids.keys():
                face_set = moab_core.create_meshset()
                moab_core.tag_set_data(tags["global_id"], face_set, face_id)
                moab_core.tag_set_data(tags["geom_dimension"], face_set, 2)
                moab_core.tag_set_data(tags["category"], face_set, "Surface")

                if len(face_ids_with_solid_ids[face_id]) == 2:
                    other_solid_id = face_ids_with_solid_ids[face_id][1]
                    other_volume_set = volume_sets_by_solid_id[other_solid_id]
                    sense_data = np.array([other_volume_set, volume_set], dtype="uint64")
                else:
                    sense_data = np.array([volume_set, 0], dtype="uint64")

                moab_core.tag_set_data(tags["surf_sense"], face_set, sense_data)

                moab_verts = moab_core.create_vertices(vertices)
                moab_core.add_entity(face_set, moab_verts)

                for triangle in triangles_on_face:
                    tri = (
                        moab_verts[int(triangle[0])],
                        moab_verts[int(triangle[1])],
                        moab_verts[int(triangle[2])],
                    )

                    moab_triangle = moab_core.create_element(types.MBTRI, tri)
                    moab_core.add_entity(face_set, moab_triangle)

                added_surfaces_ids[face_id] = face_set
            else:
                face_set = added_surfaces_ids[face_id]

                other_solid_id = face_ids_with_solid_ids[face_id][0]

                other_volume_set = volume_sets_by_solid_id[other_solid_id]

                sense_data = np.array([other_volume_set, volume_set], dtype="uint64")
                moab_core.tag_set_data(tags["surf_sense"], face_set, sense_data)

            moab_core.add_parent_child(volume_set, face_set)

        moab_core.add_entity(group_set, volume_set)

    if implicit_complement_material_tag:
        group_set = moab_core.create_meshset()
        moab_core.tag_set_data(tags["category"], group_set, "Group")
        moab_core.tag_set_data(
            tags["name"], group_set, f"mat:{implicit_complement_material_tag}_comp"
        )
        moab_core.tag_set_data(tags["geom_dimension"], group_set, 4)
        moab_core.add_entity(
            group_set, volume_set
        )  # volume is arbitrary but should exist in moab core

    all_sets = moab_core.get_entities_by_handle(0)

    file_set = moab_core.create_meshset()

    moab_core.add_entities(file_set, all_sets)

    # makes the folder if it does not exist
    if Path(h5m_filename).parent:
        Path(h5m_filename).parent.mkdir(parents=True, exist_ok=True)

    # moab_core.write_file only accepts strings
    if isinstance(h5m_filename, Path):
        moab_core.write_file(str(h5m_filename))
    else:
        moab_core.write_file(h5m_filename)

    print(f"written DAGMC file {h5m_filename}")

    return h5m_filename


def get_volumes(gmsh, assembly, method="file", scale_factor=1.0):

    if method == "in memory":
        volumes = gmsh.model.occ.importShapesNativePointer(assembly.wrapped._address())

    elif method == "file":
        with tempfile.NamedTemporaryFile(suffix=".brep") as temp_file:
            if isinstance(assembly, cq.Assembly):
                assembly.toCompound().exportBrep(temp_file.name)
            else:
                assembly.exportBrep(temp_file.name)
            volumes = gmsh.model.occ.importShapes(temp_file.name)

    # updating the model to ensure the entities in the geometry are found
    gmsh.model.occ.synchronize()

    if scale_factor != 1.0:
        dim_tags = gmsh.model.getEntities(3)
        gmsh.model.occ.dilate(dim_tags, 0.0, 0.0, 0.0, scale_factor, scale_factor, scale_factor)
        # update the model to ensure the scaling factor has been applied
        gmsh.model.occ.synchronize()

    return gmsh, volumes


def init_gmsh():
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add("made_with_cad_to_dagmc_package")
    return gmsh


def mesh_brep(
    gmsh,
    min_mesh_size: float | None = None,
    max_mesh_size: float | None = None,
    mesh_algorithm: int = 1,
    dimensions: int = 2,
    set_size: dict[int, float] | None = None,
):
    """Creates a conformal surface meshes of the volumes in a Brep file using Gmsh.

    Args:
        occ_shape: the occ_shape of the Brep file to convert
        min_mesh_size: the minimum mesh element size to use in Gmsh. Passed
            into gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)
        max_mesh_size: the maximum mesh element size to use in Gmsh. Passed
            into gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)
        mesh_algorithm: The Gmsh mesh algorithm number to use. Passed into
            gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)
        dimensions: The number of dimensions, 2 for a surface mesh 3 for a
            volume mesh. Passed to gmsh.model.mesh.generate()
        set_size: a dictionary of volume ids (int) and target mesh sizes
            (floats) to set for each volume, passed to gmsh.model.mesh.setSize.

    Returns:
        The resulting gmsh object and volumes
    """
    if min_mesh_size and max_mesh_size:
        if min_mesh_size > max_mesh_size:
            raise ValueError(
                f"min_mesh_size must be less than or equal to max_mesh_size. Currently min_mesh_size is set to {min_mesh_size} and max_mesh_size is set to {max_mesh_size}"
            )

    if min_mesh_size:
        gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)

    if max_mesh_size:
        gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)

    gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)
    gmsh.option.setNumber("General.NumThreads", 0)  # Use all available cores

    if set_size:
        volumes = gmsh.model.getEntities(3)
        available_volumes = [volume[1] for volume in volumes]
        print("volumes", volumes)
        for volume_id, size in set_size.items():
            if volume_id in available_volumes:
                size = set_size[volume_id]
                if isinstance(size, dict):
                    # TODO face specific mesh sizes
                    pass
                else:
                    boundaries = gmsh.model.getBoundary(
                        [(3, volume_id)], recursive=True
                    )  # dim must be set to 3
                    print("boundaries", boundaries)
                    gmsh.model.mesh.setSize(boundaries, size)
                    print(f"Set size of {size} for volume {volume_id}")
            else:
                raise ValueError(
                    f"volume ID of {volume_id} set in set_sizes but not found in available volumes {volumes}"
                )

    gmsh.model.mesh.generate(dimensions)

    return gmsh


def mesh_to_vertices_and_triangles(
    dims_and_vol_ids,
):
    """Converts gmsh volumes into vertices and triangles for each face.

    Args:
        volumes: the volumes in the gmsh file, found with gmsh.model.occ.importShapes

    Returns:
        vertices and triangles (grouped by solid then by face)
    """

    n = 3  # number of verts in a triangles
    triangles_by_solid_by_face = {}
    for dim_and_vol in dims_and_vol_ids:
        # removes all groups so that the following getEntitiesForPhysicalGroup
        # command only finds surfaces for the volume
        gmsh.model.removePhysicalGroups()

        vol_id = dim_and_vol[1]
        entities_in_volume = gmsh.model.getAdjacencies(3, vol_id)
        surfaces_in_volume = entities_in_volume[1]
        ps = gmsh.model.addPhysicalGroup(2, surfaces_in_volume)
        gmsh.model.setPhysicalName(2, ps, f"surfaces_on_volume_{vol_id}")

        groups = gmsh.model.getPhysicalGroups()
        group = groups[0]
        # for group in groups:
        dim = group[0]
        tag = group[1]

        surfaces = gmsh.model.getEntitiesForPhysicalGroup(dim, tag)

        # nodes_in_all_surfaces = []
        nodes_in_each_surface = {}
        for surface in surfaces:
            _, _, nodeTags = gmsh.model.mesh.getElements(2, surface)
            nodeTags = nodeTags[0].tolist()
            shifted_node_tags = []
            for nodeTag in nodeTags:
                shifted_node_tags.append(nodeTag - 1)
            grouped_node_tags = [
                shifted_node_tags[i : i + n] for i in range(0, len(shifted_node_tags), n)
            ]
            nodes_in_each_surface[surface] = grouped_node_tags
        triangles_by_solid_by_face[vol_id] = nodes_in_each_surface

    _, all_coords, _ = gmsh.model.mesh.getNodes()

    vertices = [all_coords[i : i + n].tolist() for i in range(0, len(all_coords), n)]

    return vertices, triangles_by_solid_by_face


def get_ids_from_assembly(assembly: cq.assembly.Assembly):
    ids = []
    for obj, name, loc, _ in assembly:
        ids.append(name)
    return ids


def get_ids_from_imprinted_assembly(solid_id_dict):
    ids = []
    for id in list(solid_id_dict.values()):
        ids.append(id[0])
    return ids


def check_material_tags(material_tags, iterable_solids):
    if material_tags:
        if len(material_tags) != len(iterable_solids):
            msg = (
                "When setting material_tags the number of material_tags \n"
                "should be equal to the number of volumes in the CAD \n"
                f"geometry {len(iterable_solids)} volumes found in model \n"
                f"and {len(material_tags)} material_tags found"
            )
            raise ValueError(msg)
        for material_tag in material_tags:
            if not isinstance(material_tag, str):
                msg = f"material_tags should be an iterable of strings."
                raise ValueError(msg)
            if len(material_tag) > 28:
                msg = (
                    f"Material tag {material_tag} is too long. DAGMC will truncate this material tag "
                    f"to 28 characters. The resulting tag in the h5m file will be {material_tag[:28]}"
                )
                warnings.warn(msg)


def order_material_ids_by_brep_order(original_ids, scrambled_id, material_tags):
    material_tags_in_brep_order = []
    for brep_id in scrambled_id:
        id_of_solid_in_org = original_ids.index(brep_id)
        material_tags_in_brep_order.append(material_tags[id_of_solid_in_org])
    return material_tags_in_brep_order


class MeshToDagmc:
    """Convert a GMSH mesh file to a DAGMC h5m file"""

    def __init__(self, filename: str):
        self.filename = filename

    # TODO add export_unstructured_mesh_file
    # TODO add add_gmsh_msh_file
    # TODO test for exports result in files

    def export_dagmc_h5m_file(
        self,
        material_tags: list[str],
        implicit_complement_material_tag: str | None = None,
        filename: str = "dagmc.h5m",
    ):
        """Saves a DAGMC h5m file of the geometry

        Args:
            material_tags (list[str]): the names of the DAGMC
                material tags to assign. These will need to be in the same
                order as the volumes in the GMESH mesh and match the
                material tags used in the neutronics code (e.g. OpenMC).
            implicit_complement_material_tag (str | None, optional):
                the name of the material tag to use for the implicit
                complement (void space). Defaults to None which is a vacuum.
            filename (str, optional): _description_. Defaults to "dagmc.h5m".

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        """

        gmsh.initialize()
        self.mesh_file = gmsh.open(self.filename)
        dims_and_vol_ids = gmsh.model.getEntities(3)

        if len(dims_and_vol_ids) != len(material_tags):
            msg = f"Number of volumes {len(dims_and_vol_ids)} is not equal to number of material tags {len(material_tags)}"
            raise ValueError(msg)

        vertices, triangles_by_solid_by_face = mesh_to_vertices_and_triangles(
            dims_and_vol_ids=dims_and_vol_ids
        )

        gmsh.finalize()

        h5m_filename = vertices_to_h5m(
            vertices=vertices,
            triangles_by_solid_by_face=triangles_by_solid_by_face,
            material_tags=material_tags,
            h5m_filename=filename,
            implicit_complement_material_tag=implicit_complement_material_tag,
        )

        return h5m_filename


class CadToDagmc:
    """Converts Step files and CadQuery parts to a DAGMC h5m file"""

    def __init__(self):
        self.parts = []
        self.material_tags = []

    def add_stp_file(
        self,
        filename: str,
        scale_factor: float = 1.0,
        material_tags: list[str] | None = None,
    ) -> int:
        """Loads the parts from stp file into the model.

        Args:
            filename: the filename used to save the html graph.
            material_tags (list[str]): the names of the DAGMC
                material tags to assign. These will need to be in the
                same order as the volumes in the geometry added (STP
                file and CadQuery objects) and match the material tags
                used in the neutronics code (e.g. OpenMC).
            scale_factor: a scaling factor to apply to the geometry that can be
                used to increase the size or decrease the size of the geometry.
                Useful when converting the geometry to cm for use in neutronics
                simulations.

        Returns:
            int: number of volumes in the stp file.
        """
        part = importers.importStep(str(filename)).val()

        if scale_factor == 1.0:
            scaled_part = part
        else:
            scaled_part = part.scale(scale_factor)
        return self.add_cadquery_object(cadquery_object=scaled_part, material_tags=material_tags)

    def add_cadquery_object(
        self,
        cadquery_object: (
            cq.assembly.Assembly | cq.occ_impl.shapes.Compound | cq.occ_impl.shapes.Solid
        ),
        material_tags: list[str] | None,
        scale_factor: float = 1.0,
    ) -> int:
        """Loads the parts from CadQuery object into the model.

        Args:
            cadquery_object: the cadquery object to convert, can be a CadQuery assembly
                cadquery workplane or a cadquery solid
            material_tags (Optional list[str]): the names of the
                DAGMC material tags to assign. These will need to be in the
                same order as the volumes in the geometry added (STP file and
                CadQuery objects) and match the material tags used in the
                neutronics code (e.g. OpenMC).
            scale_factor: a scaling factor to apply to the geometry that can be
                used to increase the size or decrease the size of the geometry.
                Useful when converting the geometry to cm for use in neutronics
                simulations.

        Returns:
            int: number of volumes in the stp file.
        """

        if isinstance(cadquery_object, cq.assembly.Assembly):
            cadquery_object = cadquery_object.toCompound()

        if isinstance(cadquery_object, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            iterable_solids = cadquery_object.Solids()
        else:
            iterable_solids = cadquery_object.val().Solids()

        if scale_factor == 1.0:
            scaled_iterable_solids = iterable_solids
        else:
            scaled_iterable_solids = [part.scale(scale_factor) for part in iterable_solids]

        check_material_tags(material_tags, scaled_iterable_solids)
        if material_tags:
            self.material_tags = self.material_tags + material_tags
        self.parts = self.parts + scaled_iterable_solids

        return len(scaled_iterable_solids)

    def export_unstructured_mesh_file(
        self,
        filename: str = "umesh.vtk",
        min_mesh_size: float = 1,
        max_mesh_size: float = 5,
        mesh_algorithm: int = 1,
        method: str = "file",
        scale_factor: float = 1.0,
        imprint: bool = True,
        set_size: dict[int, float] | None = None,
    ):
        """
        Exports an unstructured mesh file in VTK format for use with openmc.UnstructuredMesh.
        Compatible with the MOAB unstructured mesh library. Example useage
        openmc.UnstructuredMesh(filename="umesh.vtk", library="moab")

        Parameters:
        -----------
            filename : str, optional
                The name of the output file. Default is "umesh.vtk".
            min_mesh_size: the minimum mesh element size to use in Gmsh. Passed
                into gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)
            max_mesh_size: the maximum mesh element size to use in Gmsh. Passed
                into gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)
            mesh_algorithm: The Gmsh mesh algorithm number to use. Passed into
                gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)
            method: the method to use to import the geometry into gmsh. Options
                are 'file' or 'in memory'. 'file' is the default and will write
                the geometry to a temporary file before importing it into gmsh.
                'in memory' will import the geometry directly into gmsh but
                requires the version of OpenCASCADE used to build gmsh to be
                the same as the version used by CadQuery. This is possible to
                ensure when installing the package with Conda but harder when
                installing from PyPI.
            scale_factor: a scaling factor to apply to the geometry that can be
                used to enlarge or shrink the geometry. Useful when converting
                Useful when converting the geometry to cm for use in neutronics
            imprint: whether to imprint the geometry or not. Defaults to True as this is
                normally needed to ensure the geometry is meshed correctly. However if
                you know your geometry does not need imprinting you can set this to False
                and this can save time.
            set_size: a dictionary of volume ids (int) and target mesh sizes
                (floats) to set for each volume, passed to gmsh.model.mesh.setSize.


        Returns:
        --------
            gmsh : gmsh
                The gmsh object after finalizing the mesh.
        """

        # gmesh writes out a vtk file that is accepted by openmc.UnstructuredMesh
        # The library argument must be set to "moab"
        if Path(filename).suffix != ".vtk":
            raise ValueError("Unstructured mesh filename must have a .vtk extension")

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        if imprint:
            imprinted_assembly, _ = cq.occ_impl.assembly.imprint(assembly)
        else:
            imprinted_assembly = assembly

        gmsh = init_gmsh()

        gmsh, _ = get_volumes(gmsh, imprinted_assembly, method=method, scale_factor=scale_factor)

        gmsh = mesh_brep(
            gmsh=gmsh,
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
            dimensions=3,
            set_size=set_size,
        )

        # makes the folder if it does not exist
        if Path(filename).parent:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

        # gmsh.write only accepts strings
        if isinstance(filename, Path):
            gmsh.write(str(filename))
        else:
            gmsh.write(filename)

        gmsh.finalize()

        return gmsh

    def export_gmsh_mesh_file(
        self,
        filename: str = "mesh.msh",
        min_mesh_size: float | None = None,
        max_mesh_size: float | None = None,
        mesh_algorithm: int = 1,
        dimensions: int = 2,
        method: str = "file",
        scale_factor: float = 1.0,
        imprint: bool = True,
        set_size: dict[int, float] | None = None,
    ):
        """Saves a GMesh msh file of the geometry in either 2D surface mesh or
        3D volume mesh.

        Args:
            filename
            min_mesh_size: the minimum size of mesh elements to use.
            max_mesh_size: the maximum size of mesh elements to use.
            mesh_algorithm: the gmsh mesh algorithm to use.
            dimensions: The number of dimensions, 2 for a surface mesh 3 for a
                volume mesh. Passed to gmsh.model.mesh.generate()
            method: the method to use to import the geometry into gmsh. Options
                are 'file' or 'in memory'. 'file' is the default and will write
                the geometry to a temporary file before importing it into gmsh.
                'in memory' will import the geometry directly into gmsh but
                requires the version of OpenCASCADE used to build gmsh to be
                the same as the version used by CadQuery. This is possible to
                ensure when installing the package with Conda but harder when
                installing from PyPI.
            scale_factor: a scaling factor to apply to the geometry that can be
                used to enlarge or shrink the geometry. Useful when converting
                Useful when converting the geometry to cm for use in neutronics
            imprint: whether to imprint the geometry or not. Defaults to True as this is
                normally needed to ensure the geometry is meshed correctly. However if
                you know your geometry does not need imprinting you can set this to False
                and this can save time.
            set_size: a dictionary of volume ids (int) and target mesh sizes
                (floats) to set for each volume, passed to gmsh.model.mesh.setSize.
        """

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        if imprint:
            imprinted_assembly, _ = cq.occ_impl.assembly.imprint(assembly)
        else:
            imprinted_assembly = assembly

        gmsh = init_gmsh()

        gmsh, _ = get_volumes(gmsh, imprinted_assembly, method=method, scale_factor=scale_factor)

        gmsh = mesh_brep(
            gmsh=gmsh,
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
            dimensions=dimensions,
            set_size=set_size,
        )

        # makes the folder if it does not exist
        if Path(filename).parent:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

        # gmsh.write only accepts strings
        if isinstance(filename, Path):
            gmsh.write(str(filename))
        else:
            gmsh.write(filename)

        print(f"written GMSH mesh file {filename}")

        gmsh.finalize()

    def export_dagmc_h5m_file(
        self,
        filename: str = "dagmc.h5m",
        min_mesh_size: float | None = None,
        max_mesh_size: float | None = None,
        mesh_algorithm: int = 1,
        implicit_complement_material_tag: str | None = None,
        method: str = "file",
        scale_factor: float = 1.0,
        imprint: bool = True,
        set_size: dict[int, float] | None = None,
    ) -> str:
        """Saves a DAGMC h5m file of the geometry

        Args:
            filename (str, optional): the filename to use for the saved DAGMC file. Defaults to "dagmc.h5m".
            min_mesh_size (float, optional): the minimum size of mesh elements to use. Defaults to 1.
            max_mesh_size (float, optional): the maximum size of mesh elements to use. Defaults to 5.
            mesh_algorithm (int, optional): the GMSH mesh algorithm to use.. Defaults to 1.
            implicit_complement_material_tag (str | None, optional):
                the name of the material tag to use for the implicit complement
                (void space). Defaults to None which is a vacuum. Defaults to None.
           method: the method to use to import the geometry into gmsh. Options
                are 'file' or 'in memory'. 'file' is the default and will write
                the geometry to a temporary file before importing it into gmsh.
                'in memory' will import the geometry directly into gmsh but
                requires the version of OpenCASCADE used to build gmsh to be
                the same as the version used by CadQuery. This is possible to
                ensure when installing the package with Conda but harder when
                installing from PyPI.
            scale_factor: a scaling factor to apply to the geometry that can be
                used to enlarge or shrink the geometry. Useful when converting
                Useful when converting the geometry to cm for use in neutronics
            imprint: whether to imprint the geometry or not. Defaults to True as this is
                normally needed to ensure the geometry is meshed correctly. However if
                you know your geometry does not need imprinting you can set this to False
                and this can save time.
            set_size: a dictionary of volume ids (int) and target mesh sizes
                (floats) to set for each volume, passed to gmsh.model.mesh.setSize.

        Returns:
            str: the DAGMC filename saved
        """

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        original_ids = get_ids_from_assembly(assembly)

        # both id lists should be the same length as each other and the same
        # length as the self.material_tags
        if len(original_ids) != len(self.material_tags):
            msg = f"Number of volumes {len(original_ids)} is not equal to number of material tags {len(self.material_tags)}"
            raise ValueError(msg)

        if imprint:
            imprinted_assembly, imprinted_solids_with_org_id = cq.occ_impl.assembly.imprint(
                assembly
            )

            scrambled_ids = get_ids_from_imprinted_assembly(imprinted_solids_with_org_id)

            material_tags_in_brep_order = order_material_ids_by_brep_order(
                original_ids, scrambled_ids, self.material_tags
            )
        else:
            material_tags_in_brep_order = self.material_tags
            imprinted_assembly = assembly

        check_material_tags(material_tags_in_brep_order, self.parts)

        gmsh = init_gmsh()

        gmsh, volumes = get_volumes(
            gmsh, imprinted_assembly, method=method, scale_factor=scale_factor
        )

        gmsh = mesh_brep(
            gmsh=gmsh,
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
            set_size=set_size,
        )

        dims_and_vol_ids = volumes

        vertices, triangles_by_solid_by_face = mesh_to_vertices_and_triangles(
            dims_and_vol_ids=dims_and_vol_ids
        )

        gmsh.finalize()

        # checks and fixes triangle fix_normals within vertices_to_h5m
        return vertices_to_h5m(
            vertices=vertices,
            triangles_by_solid_by_face=triangles_by_solid_by_face,
            material_tags=material_tags_in_brep_order,
            h5m_filename=filename,
            implicit_complement_material_tag=implicit_complement_material_tag,
        )
