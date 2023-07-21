import cadquery as cq

b1 = cq.Workplane().box(1, 1, 1)
b2 = cq.Workplane(origin=(1, 0, 0)).box(1, 1, 1)

material_tags = ["mat1", "mat2"]

assembly = cq.Assembly().add(b1, color=cq.Color("red")).add(b2)


def get_ids_from_assembly(assembly):
    ids = []
    for obj, name, loc, _ in assembly:
        print(name)
        ids.append(name)
    return ids


def get_ids_from_imprinted_assembly(solid_id_dict):
    ids = []
    for id in list(solid_id_dict.values()):
        print(id[0])
        ids.append(id[0])
    return ids


imprinted_assembly, imprinted_solids_with_original_id = cq.occ_impl.assembly.imprint(
    assembly
)

original_ids = get_ids_from_assembly(assembly)
scrambled_ids = get_ids_from_imprinted_assembly(imprinted_solids_with_original_id)

brep_and_shape_ids = []
for scrambled_id, original_id in zip(scrambled_ids, original_ids):
    brep_and_shape_ids.append((scrambled_id, original_id))


# user knows order of solids in assembly

#
