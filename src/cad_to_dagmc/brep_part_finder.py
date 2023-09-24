import cadquery as cq


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


def get_ids_from_assembly(assembly):
    ids = []
    for obj, name, loc, _ in assembly:
        ids.append(name)
    return ids


def get_ids_from_imprinted_assembly(solid_id_dict):
    ids = []
    for id in list(solid_id_dict.values()):
        ids.append(id[0])
    return ids


def order_material_ids_by_brep_order(original_ids, scrambled_id, material_tags):
    material_tags_in_brep_order = []
    for brep_id in scrambled_id:
        id_of_solid_in_org = original_ids.index(brep_id)
        material_tags_in_brep_order.append(material_tags[id_of_solid_in_org])
    return material_tags_in_brep_order
