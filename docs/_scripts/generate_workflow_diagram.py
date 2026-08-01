"""Generates the workflow diagram shown on the documentation home page.

Writes a light and a dark variant into ``docs/_static``. Run it after changing
the inputs, meshing backends, h5m writers or output files:

    python docs/_scripts/generate_workflow_diagram.py

The layout is set out by hand (rather than by an automatic graph layout) so the
five stages line up in columns and the arrows stay easy to follow. The canvas is
26 x 14 data units drawn at 13 x 7 inches, so one inch is always two units and
the box widths below can be checked against the text they hold.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "_static"

XLIM = (0.0, 26.0)
YLIM = (0.0, 14.0)
FIGSIZE = (13.0, 7.0)

# Column centres and half widths, one entry per stage.
COLUMNS = {
    "input": (2.15, 1.95),
    "tagging": (6.95, 1.95),
    "meshing": (12.25, 2.45),
    "writer": (18.30, 1.40),
    "output": (23.30, 2.50),
}

# Fill, border and text colour for each stage.
THEMES = {
    "light": {
        "input": ("#e0f2fe", "#0284c7", "#0c4a6e"),
        "tagging": ("#fef3c7", "#b45309", "#78350f"),
        "meshing": ("#f3e8ff", "#9333ea", "#581c87"),
        "writer": ("#fce7f3", "#db2777", "#831843"),
        "output": ("#dcfce7", "#16a34a", "#14532d"),
        "arrow": "#64748b",
        "muted": "#64748b",
        "divider": "#cbd5e1",
    },
    "dark": {
        "input": ("#0b2b3f", "#38bdf8", "#bae6fd"),
        "tagging": ("#3a2a08", "#fbbf24", "#fde68a"),
        "meshing": ("#2b1a40", "#c084fc", "#e9d5ff"),
        "writer": ("#3b1028", "#f472b6", "#fbcfe8"),
        "output": ("#0e2e1c", "#4ade80", "#bbf7d0"),
        "arrow": "#94a3b8",
        "muted": "#94a3b8",
        "divider": "#475569",
    },
}

TITLE_SIZE = 12.0
SUB_SIZE = 9.5
MONO_SIZE = 9.0
HEADER_SIZE = 11.5
CAPTION_SIZE = 9.5


def draw_box(ax, theme, stage, y, height, title, subs=(), dashed=False):
    """Draws a rounded box centred on its column and returns its x extent."""
    fill, edge, text_colour = theme[stage]
    x_centre, half_width = COLUMNS[stage]

    if dashed:
        fill, edge, text_colour = "none", theme["divider"], theme["muted"]

    ax.add_patch(
        FancyBboxPatch(
            (x_centre - half_width, y - height / 2),
            2 * half_width,
            height,
            boxstyle="round,pad=0,rounding_size=0.28",
            facecolor=fill,
            edgecolor=edge,
            linewidth=1.8,
            linestyle="--" if dashed else "-",
            zorder=3,
        )
    )

    # Stack the title and any sub lines as a block centred in the box.
    line_heights = [0.55] + [0.42] * len(subs)
    cursor = y + sum(line_heights) / 2
    for index, line_height in enumerate(line_heights):
        cursor -= line_height / 2
        if index == 0:
            ax.text(
                x_centre,
                cursor,
                title,
                ha="center",
                va="center",
                fontsize=TITLE_SIZE,
                fontweight="bold",
                color=text_colour,
                zorder=4,
            )
        else:
            label, mono = subs[index - 1]
            ax.text(
                x_centre,
                cursor,
                label,
                ha="center",
                va="center",
                fontsize=MONO_SIZE if mono else SUB_SIZE,
                color=text_colour,
                family="monospace" if mono else None,
                zorder=4,
            )
        cursor -= line_height / 2

    return x_centre - half_width, x_centre + half_width


def draw_arrow(ax, theme, start, end, rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=16,
            linewidth=1.9,
            color=theme["arrow"],
            shrinkA=0,
            shrinkB=0,
            connectionstyle=f"arc3,rad={rad}",
            zorder=2,
        )
    )


def draw_headers(ax, theme):
    headers = [
        ("input", "INPUT"),
        ("tagging", "MATERIAL TAGS"),
        ("meshing", "MESHING BACKEND"),
        ("writer", "H5M WRITER"),
        ("output", "OUTPUT FILES"),
    ]
    for stage, label in headers:
        x_centre, half_width = COLUMNS[stage]
        _, edge, text_colour = theme[stage]
        ax.text(
            x_centre,
            13.35,
            label,
            ha="center",
            va="center",
            fontsize=HEADER_SIZE,
            fontweight="bold",
            color=text_colour,
        )
        ax.plot(
            [x_centre - half_width, x_centre + half_width],
            [12.95, 12.95],
            color=edge,
            linewidth=2.4,
            solid_capstyle="round",
        )


def build_figure(theme_name):
    theme = THEMES[theme_name]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.axis("off")

    draw_headers(ax, theme)

    # Stage 1, the CAD inputs.
    _, cad_right = draw_box(
        ax,
        theme,
        "input",
        10.7,
        1.6,
        "CadQuery object",
        [("solids or assemblies", False), ("add_cadquery_object()", True)],
    )
    _, step_right = draw_box(
        ax, theme, "input", 8.6, 1.4, "STEP file", [("add_stp_file()", True)]
    )

    # Stage 2, the material tags.
    tags_left, tags_right = draw_box(
        ax,
        theme,
        "tagging",
        9.7,
        3.3,
        "material_tags",
        [
            ("one name per volume", False),
            ('["mat1", "mat2"]', True),
            ('"assembly_names"', True),
            ('"assembly_materials"', True),
        ],
    )

    # Stage 3, the meshing backends.
    mesher_left, mesher_right = draw_box(
        ax,
        theme,
        "meshing",
        11.3,
        1.5,
        "cad-to-dagmc-mesher",
        [("default, surface and tets", False)],
    )
    gmsh_left, gmsh_right = draw_box(
        ax, theme, "meshing", 9.0, 1.5, "gmsh", [("full mesh size control", False)]
    )
    cq_left, cq_right = draw_box(
        ax,
        theme,
        "meshing",
        6.7,
        1.5,
        "cadquery",
        [("tessellation, surface only", False)],
    )

    # Stage 4, the h5m writers.
    writer_left, writer_right = draw_box(
        ax, theme, "writer", 8.5, 1.3, "h5py", [("or pymoab", False)]
    )

    # Stage 5, the output files.
    vtk_left, _ = draw_box(
        ax,
        theme,
        "output",
        11.3,
        1.9,
        "Unstructured mesh",
        [("umesh.vtk, tetrahedra", False), ("export_unstructured_mesh_file()", True)],
    )
    h5m_left, _ = draw_box(
        ax,
        theme,
        "output",
        8.5,
        1.9,
        "DAGMC geometry",
        [("dagmc.h5m, triangles", False), ("export_dagmc_h5m_file()", True)],
    )
    msh_left, _ = draw_box(
        ax,
        theme,
        "output",
        5.5,
        1.9,
        "GMSH mesh",
        [("mesh.msh, 2D or 3D", False), ("export_gmsh_mesh_file()", True)],
    )

    # Inputs feed the material tags.
    draw_arrow(ax, theme, (cad_right, 10.7), (tags_left, 10.5))
    draw_arrow(ax, theme, (step_right, 8.6), (tags_left, 9.0))

    # Tagged geometry goes to whichever meshing backend is selected.
    draw_arrow(ax, theme, (tags_right, 10.8), (mesher_left, 11.3))
    draw_arrow(ax, theme, (tags_right, 9.7), (gmsh_left, 9.0))
    draw_arrow(ax, theme, (tags_right, 8.6), (cq_left, 6.9))

    # Every backend writes the surface mesh through an h5m writer.
    draw_arrow(ax, theme, (mesher_right, 10.8), (writer_left, 8.95))
    draw_arrow(ax, theme, (gmsh_right, 9.0), (writer_left, 8.5))
    draw_arrow(ax, theme, (cq_right, 7.0), (writer_left, 8.05))
    draw_arrow(ax, theme, (writer_right, 8.5), (h5m_left, 8.5))

    # Both volume meshers write their tetrahedra straight to a vtk file.
    draw_arrow(ax, theme, (mesher_right, 11.6), (vtk_left, 11.7))
    draw_arrow(ax, theme, (gmsh_right, 9.5), (vtk_left, 11.0))

    # Only gmsh writes its own native mesh format.
    draw_arrow(ax, theme, (gmsh_right, 8.35), (msh_left, 5.7))

    # An already meshed input skips the meshing stage, shown as its own row.
    ax.plot(
        [0.2, 25.8],
        [3.95, 3.95],
        color=theme["divider"],
        linewidth=1.2,
        linestyle=(0, (6, 6)),
    )
    ax.text(
        0.2,
        3.4,
        "A GMSH mesh input is already meshed, so it skips the meshing stage",
        ha="left",
        va="center",
        fontsize=CAPTION_SIZE,
        style="italic",
        color=theme["muted"],
    )

    _, msh_in_right = draw_box(
        ax, theme, "input", 2.15, 1.5, "GMSH mesh", [("file or gmsh object", False)]
    )
    groups_left, groups_right = draw_box(
        ax,
        theme,
        "tagging",
        2.15,
        1.5,
        "physical groups",
        [("or an explicit list", False)],
    )
    skip_left, skip_right = draw_box(
        ax, theme, "meshing", 2.15, 1.5, "no meshing needed", dashed=True
    )
    writer2_left, writer2_right = draw_box(
        ax, theme, "writer", 2.15, 1.5, "h5py", [("or pymoab", False)]
    )
    h5m2_left, _ = draw_box(
        ax, theme, "output", 2.15, 1.5, "DAGMC geometry", [("dagmc.h5m", False)]
    )

    draw_arrow(ax, theme, (msh_in_right, 2.15), (groups_left, 2.15))
    draw_arrow(ax, theme, (groups_right, 2.15), (skip_left, 2.15))
    draw_arrow(ax, theme, (skip_right, 2.15), (writer2_left, 2.15))
    draw_arrow(ax, theme, (writer2_right, 2.15), (h5m2_left, 2.15))

    ax.text(
        13.0,
        0.7,
        "export_gmsh_file_to_dagmc_h5m_file()   or   "
        "export_gmsh_object_to_dagmc_h5m_file()",
        ha="center",
        va="center",
        fontsize=MONO_SIZE,
        family="monospace",
        color=theme["muted"],
    )

    return fig


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for theme_name in THEMES:
        figure = build_figure(theme_name)
        filename = OUTPUT_DIR / f"workflow_{theme_name}.png"
        figure.savefig(
            filename,
            dpi=200,
            transparent=True,
            pil_kwargs={"optimize": True},
        )
        plt.close(figure)
        print(f"written {filename}")


if __name__ == "__main__":
    main()
