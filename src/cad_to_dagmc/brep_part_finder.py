from turtle import shape
import warnings
from collections.abc import Iterable
from typing import Tuple, Union
from os import PathLike
import numpy as np
from cadquery import *
from cadquery.occ_impl.shapes import Shape
import cadquery as cq


def get_part_properties_from_shape(shape: Shape) -> dict:
    """Accepts a cadquery solid object and returns the unique
    identify details of the solid

    Args:
        filename: the filename of the brep file
    """

    part_details = {}
    part_details["center_x"] = shape.Center().x
    part_details["center_y"] = shape.Center().y
    part_details["center_z"] = shape.Center().z

    part_details["volume"] = shape.Volume()

    part_details["bounding_box_xmin"] = shape.BoundingBox().xmin
    part_details["bounding_box_ymin"] = shape.BoundingBox().ymin
    part_details["bounding_box_zmin"] = shape.BoundingBox().zmin
    part_details["bounding_box_xmax"] = shape.BoundingBox().xmax
    part_details["bounding_box_ymax"] = shape.BoundingBox().ymax
    part_details["bounding_box_zmax"] = shape.BoundingBox().zmax

    return part_details


def convert_shape_to_iterable_of_shapes(shapes):

    if isinstance(shapes, cq.occ_impl.shapes.Compound):
        # brep route
        iterable_solids = shapes.Solids()
    elif isinstance(shapes, cq.Workplane):
        # workplane route
        iterable_solids = shapes.val().Solids()
    else:
        iterable_solids = shapes.Solids()

    return iterable_solids


def get_part_properties_from_shapes(shapes: Iterable) -> dict:
    """Accepts a cadquery.occ_impl.shapes object and returns the unique
    identify details of each Solid

    Args:
        filename: the filename of the brep file
    """

    if not isinstance(shapes, Iterable):
        iterable_of_shapes = convert_shape_to_iterable_of_shapes(shapes)
    else:
        # if a list of workplanes or other shapes is passed (e.g paramak) then
        # we iterate through the list and convert to solids that have the
        # expected properties (e.g. .Center.x)
        iterable_of_shapes = []
        for shape in shapes:
            more_shapes = convert_shape_to_iterable_of_shapes(shape)
            iterable_of_shapes = iterable_of_shapes + more_shapes

    all_part_details = {}
    for counter, part in enumerate(iterable_of_shapes, 1):
        part_details = get_part_properties_from_shape(part)
        all_part_details[counter] = part_details

    return all_part_details


def get_part_properties_from_file(filename: Union[str, PathLike]):
    """Imports a Brep CAD file and returns the unique identify details of each Solid

    Args:
        filename: the filename of the brep file
    """

    shapes = Shape.importBrep(filename)

    my_brep_part_details = get_part_properties_from_shapes(shapes)

    return my_brep_part_details


def get_matching_part_id(
    brep_part_properties: dict,
    center_x: float = None,
    center_y: float = None,
    center_z: float = None,
    volume: float = None,
    bounding_box_xmin: float = None,
    bounding_box_ymin: float = None,
    bounding_box_zmin: float = None,
    bounding_box_xmax: float = None,
    bounding_box_ymax: float = None,
    bounding_box_zmax: float = None,
    volume_atol: float = 1e-6,
    center_atol: float = 1e-6,
    bounding_box_atol: float = 1e-6,
    verbose=True,
):
    """Finds the key within a dictionary of parts that matches the user
    specified arguments for volume, center, bounding_box within the provided
    tolerances

    Arguments:
        brep_part_properties: a dictionary with the part id number as the key
            and a dictionary of values for the part properties. For example
            {1: {'Center.x':0, 'Center.y':0, 'Center.z':0, 'Volume':10, ....}}
        volume: the volume of the part to find.
        center: a tuple of x,y,z coordinates
        bounding_box: a tuple of two coordinates where the coordinates are the
            lower left and upper right corners of the bounding box.
        volume_atol: absolute tolerance acceptable on the volume comparison
        center_atol: absolute tolerance acceptable on the center comparison
        bounding_box_atol: absolute tolerance acceptable on the bounding box comparison
    """

    part_ids_matching = {}

    properties = [
        center_x,
        center_y,
        center_z,
        volume,
        bounding_box_xmin,
        bounding_box_ymin,
        bounding_box_zmin,
        bounding_box_xmax,
        bounding_box_ymax,
        bounding_box_zmax,
    ]
    properties_names = [
        "center_x",
        "center_y",
        "center_z",
        "volume",
        "bounding_box_xmin",
        "bounding_box_ymin",
        "bounding_box_zmin",
        "bounding_box_xmax",
        "bounding_box_ymax",
        "bounding_box_zmax",
    ]
    tolerances = [
        center_atol,
        center_atol,
        center_atol,
        volume_atol,
        bounding_box_atol,
        bounding_box_atol,
        bounding_box_atol,
        bounding_box_atol,
        bounding_box_atol,
        bounding_box_atol,
    ]
    if verbose:
        print(f"checking new shape against {len(brep_part_properties)} parts")
    for i, (property, names, tolerance) in enumerate(
        zip(properties, properties_names, tolerances)
    ):
        if verbose:
            print(f"    checking shape against brep part {i+1}")
        if property is not None:
            part_ids_matching_property = []
            for key, value in brep_part_properties.items():
                if np.isclose(value[names], property, atol=tolerance):
                    part_ids_matching_property.append(key)
            if len(part_ids_matching_property) == 0:
                warnings.warn(
                    f"No parts matching the specified {names} +/- tolerances were found"
                )
            else:
                part_ids_matching[names] = part_ids_matching_property

    lists_of_matching_parts_separate = list(part_ids_matching.values())

    if verbose:
        if lists_of_matching_parts_separate == []:
            warnings.warn("No single part found that matches all criteria")
            print("search criteria are:")
            print(" volume", volume)
            print(" center_x", center_x)
            print(" center_y", center_y)
            print(" center_z", center_z)
            print(" bounding_box_xmin", bounding_box_xmin)
            print(" bounding_box_ymin", bounding_box_ymin)
            print(" bounding_box_zmin", bounding_box_zmin)
            print(" bounding_box_xmax", bounding_box_xmax)
            print(" bounding_box_ymax", bounding_box_ymax)
            print(" bounding_box_zmax", bounding_box_zmax)
            print(" with tolerances")
            print("  volume_atol", volume_atol)
            print("  center_atol", center_atol)
            print("  bounding_box_atol", bounding_box_atol)
            print("\nbrep criteria are:")
            for key, value in brep_part_properties.items():
                print(f"    {key}")
                for key2, value2 in value.items():
                    print(f"        {key2}, {value2}")

    if lists_of_matching_parts_separate == []:
        raise ValueError("No matching part found")

    lists_of_matching_parts = list(
        set.intersection(*map(set, lists_of_matching_parts_separate))
    )

    if verbose:
        if len(lists_of_matching_parts) == 0:
            warnings.warn("No single part found that matches all criteria")
            print("search criteria are:")
            print(" volume", volume)
            print(" center_x", center_x)
            print(" center_y", center_y)
            print(" center_z", center_z)
            print(" bounding_box_xmin", bounding_box_xmin)
            print(" bounding_box_ymin", bounding_box_ymin)
            print(" bounding_box_zmin", bounding_box_zmin)
            print(" bounding_box_xmax", bounding_box_xmax)
            print(" bounding_box_ymax", bounding_box_ymax)
            print(" bounding_box_zmax", bounding_box_zmax)
            print(" with tolerances")
            print("  volume_atol", volume_atol)
            print("  center_atol", center_atol)
            print("  bounding_box_atol", bounding_box_atol)
            print("\nbrep criteria are:")
            for key, value in brep_part_properties.items():
                print(f"    {key}")
                for key2, value2 in value.items():
                    print(f"        {key2}, {value2}")

    return lists_of_matching_parts


def get_matching_part_ids(
    brep_part_properties: dict,
    shape_properties: dict,
    volume_atol: float = 1e-6,
    center_atol: float = 1e-6,
    bounding_box_atol: float = 1e-6,
    verbose=True,
):
    """finds the brep id that matches the shape ids and returns a list of tuples
    where the first tuple is the shape part id and the second tuple is the brep
    id"""

    brep_and_shape_part_id = []
    remaining_shape_ids = []
    for shape_id, value in shape_properties.items():

        if isinstance(value, dict):
            # check if value is a list of dictionaries or a dictionary
            matching_part_id = get_matching_part_id(
                brep_part_properties=brep_part_properties,
                volume_atol=volume_atol,
                center_atol=center_atol,
                bounding_box_atol=bounding_box_atol,
                **value,
            )
            # if len(matching_part_id) == 0:
            # nothing found, recheck
            if len(matching_part_id) > 1:
                raise ValueError(f"multiple matching volumes were found for {shape_id}")
            if len(matching_part_id) == 1:
                if verbose:
                    print(
                        f"    single matching pair, brep id = {matching_part_id[0]} shape id = {shape_id}"
                    )
                brep_and_shape_part_id.append((matching_part_id[0], shape_id))
                # print()
                brep_part_properties.pop(matching_part_id[0])
            # todo check that key is not already in use

            else:
                remaining_shape_ids.append(shape_id)

        else:
            msg = "shape_properties must be a dictionary of dictionaries"
            raise ValueError(msg)

    if verbose:
        print(
            f"remaining brep ids that were not matched = {brep_part_properties.keys()}"
        )

    if len(brep_part_properties.keys()) == 1:
        if len(remaining_shape_ids) == 1:

            value = shape_properties[remaining_shape_ids[0]]

            # removing bounding box check as a last resort.
            # The bounding box for cad is not as robust as the other checks
            # Therefore in the case where just a single volume remains we
            # check the volume and the center of mass but skip the bb check
            value.pop("bounding_box_xmin")
            value.pop("bounding_box_ymin")
            value.pop("bounding_box_zmin")
            value.pop("bounding_box_xmax")
            value.pop("bounding_box_ymax")
            value.pop("bounding_box_zmax")

            matching_part_id = get_matching_part_id(
                brep_part_properties=brep_part_properties,
                volume_atol=volume_atol,
                center_atol=center_atol,
                bounding_box_atol=None,
                **value,
            )

            if verbose:
                print("matching_part_id", matching_part_id)

            remaining_brep_id = list(brep_part_properties.keys())[0]
            remaining_shape_id = remaining_shape_ids[0]

            if verbose:
                print(
                    f"assigning brep id of {remaining_brep_id} to shape id of {remaining_shape_id} based on volume and center of mass check (bb check skipped)"
                )
            brep_and_shape_part_id.append((remaining_brep_id, remaining_shape_id))

    brep_and_shape_part_id = sorted(brep_and_shape_part_id, key=lambda x: x[0])

    return brep_and_shape_part_id
