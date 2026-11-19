"""Tags must fit in the 32-byte group names of the h5m file with "mat:" in
front and a null byte at the end, so material tags can have 27 characters
and the implicit complement tag, which also gets "_comp", 22."""

import warnings

import cadquery as cq
import gmsh
import pytest

import cad_to_dagmc
from cad_to_dagmc import CadToDagmc


def test_27_character_tag_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        CadToDagmc().add_cadquery_object(
            cq.Workplane().box(1, 1, 1), material_tags=["a" * 27]
        )


def test_28_character_tag_warns():
    with pytest.warns(UserWarning, match="Material tag a{28} is too long"):
        CadToDagmc().add_cadquery_object(
            cq.Workplane().box(1, 1, 1), material_tags=["a" * 28]
        )


def test_long_implicit_complement_tag_warns_on_export(tmp_path):
    model = CadToDagmc()
    model.add_cadquery_object(cq.Workplane().box(1, 1, 1), material_tags=["mat1"])

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        model.export_dagmc_h5m_file(
            filename=str(tmp_path / "ok.h5m"),
            implicit_complement_material_tag="b" * 22,
            meshing_backend="gmsh",
        )

    with pytest.warns(
        UserWarning, match="Implicit complement material tag b{23} is too long"
    ):
        model.export_dagmc_h5m_file(
            filename=str(tmp_path / "long.h5m"),
            implicit_complement_material_tag="b" * 23,
            meshing_backend="gmsh",
        )


def test_gmsh_file_conversion_warns_about_long_tags(tmp_path):
    with pytest.warns(UserWarning) as record:
        cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
            gmsh_filename="tests/tagged_mesh.msh",
            material_tags=["a" * 28, "short"],
            implicit_complement_material_tag="b" * 23,
            dagmc_filename=str(tmp_path / "dagmc.h5m"),
        )
    messages = [str(w.message) for w in record]
    assert any(m.startswith(f"Material tag {'a' * 28} is too long") for m in messages)
    assert any(
        m.startswith(f"Implicit complement material tag {'b' * 23} is too long")
        for m in messages
    )


def test_gmsh_object_conversion_warns_about_long_tags(tmp_path):
    gmsh.initialize()
    try:
        gmsh.open("tests/tagged_mesh.msh")
        with pytest.warns(UserWarning, match=f"Material tag {'a' * 28} is too long"):
            cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(
                material_tags=["a" * 28, "short"],
                filename=str(tmp_path / "dagmc.h5m"),
            )
    finally:
        gmsh.finalize()
