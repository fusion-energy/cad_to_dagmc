from cad_to_dagmc import CadToDagmc

import cadquery as cq

result = cq.Workplane().text(txt="DAGMC", fontsize=10, distance=1)
assembly = cq.Assembly()
assembly.add(result)
assembly.save("text_dagmc.stp", exportType="STEP")


my_model = CadToDagmc()
# the d and c from the word dagmc would be tagged with one material and the agm are tagged with another material
my_model.add_stp_file(
    filename="text_dagmc.stp", material_tags=["mat1", "mat2", "mat2", "mat2", "mat1"]
)
my_model.export_dagmc_h5m_file()
