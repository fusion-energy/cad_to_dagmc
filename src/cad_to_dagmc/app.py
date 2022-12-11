
from pathlib import Path
from cadquery import importers
import streamlit as st
import cadquery as cq
       
from cad_to_dagmc import CadToDagmc


def save_uploadedfile(uploadedfile):
    with open(uploadedfile.name, "wb") as f:
        f.write(uploadedfile.getbuffer())
    return st.success(f"Saved File to {uploadedfile.name}")


def header():
    """This section writes out the page header common to all tabs"""

    st.set_page_config(
        page_title="OpenMC Geometry Plot",
        page_icon="⚛",
        layout="wide",
    )

    hide_streamlit_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {
                    visibility: hidden;
                    }
                </style>
                """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    st.write(
        """
            # CAD to DAGMC

            ### ⚛ A geometry conversion tool.

            🐍 Run this app locally with Python ```pip install cad_to_dagmc[gui]``` then run with ```cad_to_dagmc```

            ⚙ Produce DAGMC files in batch with the 🐍 [Python API](https://github.com/fusion-energy/cad_to_dagmc/tree/main/examples)

            💾 Raise a feature request, report and issue or make a contribution on [GitHub](https://github.com/fusion-energy/cad_to_dagmc)

            📧 Email feedback to mail@jshimwell.com

            🔗 You might be interested in the related package [dagmc_geometry_slice_plotter](https://github.com/fusion-energy/dagmc_geometry_slice_plotter).
        """
    )
    st.write("<br>", unsafe_allow_html=True)


def main():

    header()

    st.write(
        """
            👉 Create your CAD geometry, export to a STP file file and upload the STP file here.
        """
    )
    geometry_stp_file = st.file_uploader("Upload your CAD files (stp file format)", type=["stp", "step"])

    if geometry_stp_file == None:
        new_title = '<p style="font-family:sans-serif; color:Red; font-size: 30px;">Upload your STP file</p>'
        st.markdown(new_title, unsafe_allow_html=True)

        #TODO find a nice stp file and url
        # st.markdown(
        #     'Not got STP files handy? Download an example [](https://raw.githubusercontent.com/fusion-energy/openmc_plot/main/examples/tokamak/geometry.xml "download")'
        # )

    else:

        save_uploadedfile(geometry_stp_file)
        
        part = importers.importStep(geometry_stp_file.name).val()

        if isinstance(part, cq.assembly.Assembly):
            print("assembly found")
            part = part.toCompound()

        if isinstance(part, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            iterable_solids = part.Solids()
        else:
            iterable_solids = part.val().Solids()
            
        print(iterable_solids)
        mat_tags = []
        for i, solid in enumerate(iterable_solids):
            mat_tag = st.text_input(label=f'material tag for volume {i}', key=f'mat_tags_{i}', value=f'mat_{i}')
            mat_tags.append(mat_tag)
        
        print(mat_tags)
        
        if st.button('Say hello'):

            my_model = CadToDagmc()
            # the d and c from the word dagmc would be tagged with one material and the agm are tagged with another material
            my_model.add_cadquery_object(
                part, material_tags=mat_tags
            )
            my_model.export_dagmc_h5m_file()
        

        with open(geometry_stp_file.name, "rb") as file:

            my_model = CadToDagmc()
            # the d and c from the word dagmc would be tagged with one material and the agm are tagged with another material
            my_model.add_cadquery_object(
                part, material_tags=mat_tags
            )
            my_model.export_dagmc_h5m_file()
            st.download_button(
                label="Download DAGMC h5m file",
                data=file,
                file_name="dagmc.h5m",
                mime=None
            )

if __name__ == "__main__":
    main()
