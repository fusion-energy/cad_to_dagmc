# TODO test brep_part_finder

from cad_to_dagmc import order_material_ids_by_brep_order

# def get_ids_from_assembly(assembly):
#     ids = []
#     for obj, name, loc, _ in assembly:
#         ids.append(name)
#     return ids

# def get_ids_from_imprinted_assembly(solid_id_dict):
#     ids = []
#     for id in list(solid_id_dict.values()):
#         print(id[0])
#         ids.append(id[0])
#     return ids


def test_order_material_ids_by_brep_order():
    # two entries, reverse order
    new_order = order_material_ids_by_brep_order(["1", "2"], ["2", "1"], ["m1", "m2"])
    assert new_order == ["m2", "m1"]

    # three entries, partly duplicate materials
    new_order = order_material_ids_by_brep_order(
        ["1", "2", "3"], ["2", "1", "3"], ["m1", "m2", "m2"]
    )
    assert new_order == ["m2", "m1", "m2"]

    # three entries, unique materials
    new_order = order_material_ids_by_brep_order(
        ["1", "2", "3"], ["2", "1", "3"], ["m1", "m2", "m3"]
    )
    assert new_order == ["m2", "m1", "m3"]

    # three entries, duplicate materials
    new_order = order_material_ids_by_brep_order(
        ["1", "2", "3"], ["2", "1", "3"], ["m1", "m1", "m1"]
    )
    assert new_order == ["m1", "m1", "m1"]
