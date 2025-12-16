# This example makes a CadQuery assembly and assigns materials to the parts
# The assembly is then exported to a STEP file and this STEP file that contains
# the materials is imported back in directly to cad-to-dagmc where the materials
# from the assembly STEP file are then used when exporting to a DAGMC H5M file
# This avoids needing to specify material tags separately when adding the CadQuery object

from cadquery import importers
import cadquery as cq
from cad_to_dagmc import CadToDagmc

result = cq.Workplane().sphere(5)
result2 = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(result, name="result", material=cq.Material("mat1"))  # note material assigned here
assembly.add(result2, name="result2", material=cq.Material("mat2"))  # note material assigned here

assembly.export("assembly_step.step")

# currently neither import the assembly material info
assembly=cq.Assembly().importStep('assembly_step.step')
workplane = importers.importStep('assembly_step.step')

my_model = CadToDagmc()
my_model.add_stp_file(
    filename="assembly_step.step"
)  # note that material tags are not needed here
my_model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)


