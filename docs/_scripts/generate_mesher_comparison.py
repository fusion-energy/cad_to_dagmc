#!/usr/bin/env python3
"""Rebuild the cad-to-dagmc-mesher comparison figure and benchmark data.

The geometry is the ``PartiallyEmbeddedSphere`` benchmark from
https://github.com/fusion-energy/model_benchmark_zoo (30 cm box, 10 cm sphere,
5 cm penetration). Its CadQuery construction is reproduced here so that this
figure generator has no runtime dependency on model_benchmark_zoo.

The script creates uniformly sized Gmsh meshes, one curvature-adaptive
cad-to-dagmc-mesher mesh, runs each mesh with the same fixed-source OpenMC
problem, reads timing from each statepoint with the OpenMC Python API, counts
unique triangles with dagmc_h5m_file_inspector, and writes a three-panel PNG.

Required packages: cad_to_dagmc, cadquery, dagmc_h5m_file_inspector, matplotlib,
numpy, and a DAGMC-enabled OpenMC installation. The included H1 test data is
used by default, so no external nuclear-data download is needed.
"""

from __future__ import annotations

import argparse
import csv
import math
import platform
import shutil
import statistics
from pathlib import Path

import cadquery as cq
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from cad_to_dagmc import CadToDagmc

GMESH_SIZES = (4.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.75)
MATERIAL_TAGS = ("box", "sphere")
MESHER_TOLERANCE = 0.2
MESHER_ANGULAR_TOLERANCE = 0.2
BOX_WIDTH = 30.0
SPHERE_RADIUS = 10.0
PENETRATION_DEPTH = 5.0
DEFAULT_PARTICLES = 50_000
DEFAULT_BATCHES = 5
DEFAULT_REPEATS = 3


def partially_embedded_sphere() -> cq.Assembly:
    """Return the benchmark's two-volume CadQuery assembly in centimetres."""
    sphere_centre_x = (
        BOX_WIDTH / 2 - PENETRATION_DEPTH + SPHERE_RADIUS
    )

    box = cq.Workplane("XY").box(BOX_WIDTH, BOX_WIDTH, BOX_WIDTH)
    sphere = (
        cq.Workplane("XY").moveTo(sphere_centre_x, 0).sphere(SPHERE_RADIUS)
    )

    assembly = cq.Assembly(name="partially_embedded_sphere")
    assembly.add(box.cut(sphere), name="box")
    assembly.add(sphere, name="sphere")
    return assembly


def cad_model() -> CadToDagmc:
    model = CadToDagmc()
    model.add_cadquery_object(
        partially_embedded_sphere(), material_tags=list(MATERIAL_TAGS)
    )
    return model


def create_meshes(work_dir: Path, force: bool) -> tuple[Path, list[tuple[float, Path]]]:
    """Create the adaptive reference mesh and uniformly sized Gmsh sweep."""
    work_dir.mkdir(parents=True, exist_ok=True)
    mesher_file = work_dir / "cad_to_dagmc_mesher.h5m"
    if force or not mesher_file.exists():
        cad_model().export_dagmc_h5m_file(
            filename=str(mesher_file),
            meshing_backend="cad-to-dagmc-mesher",
            tolerance=MESHER_TOLERANCE,
            angular_tolerance=MESHER_ANGULAR_TOLERANCE,
        )

    gmsh_meshes = []
    for size in GMESH_SIZES:
        filename = work_dir / f"gmsh_{size:g}.h5m"
        if force or not filename.exists():
            cad_model().export_dagmc_h5m_file(
                filename=str(filename),
                meshing_backend="gmsh",
                min_mesh_size=size,
                max_mesh_size=size,
            )
        gmsh_meshes.append((size, filename))
    return mesher_file, gmsh_meshes


def mesh_triangles(filename: Path) -> list[np.ndarray]:
    """Return unique triangle coordinates using the inspector's public API."""
    import dagmc_h5m_file_inspector as inspector

    per_volume = inspector.get_triangle_conn_and_coords_by_volume(str(filename))
    unique: dict[tuple[tuple[float, float, float], ...], np.ndarray] = {}
    # A shared interface belongs to two volumes. Deduplicate it geometrically so
    # the reported count is the number of distinct tracking triangles.
    for volume_id in sorted(per_volume):
        connectivity, coordinates = per_volume[volume_id]
        for indices in connectivity:
            triangle = coordinates[indices]
            key = tuple(sorted(map(tuple, np.round(triangle, decimals=10))))
            unique[key] = triangle
    return list(unique.values())


def triangle_count(filename: Path) -> int:
    return len(mesh_triangles(filename))


def volume_accuracies(filename: Path) -> dict[str, float]:
    """Return per-material volume accuracy relative to the analytic geometry."""
    import dagmc_h5m_file_inspector as inspector

    cap_volume = (
        math.pi
        * PENETRATION_DEPTH**2
        * (3 * SPHERE_RADIUS - PENETRATION_DEPTH)
        / 3
    )
    exact = {
        "box": BOX_WIDTH**3 - cap_volume,
        "sphere": 4 / 3 * math.pi * SPHERE_RADIUS**3,
    }
    measured = inspector.get_volumes_by_cell_id_and_material_name(str(filename))
    by_material = {material: volume for (_, material), volume in measured.items()}
    accuracies = {
        material: 100 * (1 - abs(by_material[material] - volume) / volume)
        for material, volume in exact.items()
    }
    accuracies["overall"] = 100 * (
        1 - abs(sum(by_material.values()) - sum(exact.values())) / sum(exact.values())
    )
    return accuracies


def make_openmc_model(h5m_file: Path, particles: int, batches: int):
    """Construct the common fixed-source performance benchmark."""
    import openmc

    openmc.reset_auto_ids()
    materials = openmc.Materials()
    for name in MATERIAL_TAGS:
        material = openmc.Material(name=name)
        material.add_nuclide("H1", 1.0)
        material.set_density("g/cm3", 0.01)
        materials.append(material)

    dagmc_universe = openmc.DAGMCUniverse(filename=str(h5m_file.resolve()))
    geometry = openmc.Geometry(dagmc_universe.bounded_universe())

    source = openmc.IndependentSource()
    source.space = openmc.stats.Point((0.1, 0.1, 0.1))
    source.angle = openmc.stats.Isotropic()
    source.energy = openmc.stats.Discrete([14.0e6], [1.0])

    settings = openmc.Settings()
    settings.run_mode = "fixed source"
    settings.batches = batches
    settings.inactive = 0
    settings.particles = particles
    settings.source = source
    settings.photon_transport = False

    return openmc.Model(materials=materials, geometry=geometry, settings=settings)


def particles_per_second(
    h5m_file: Path,
    run_dir: Path,
    cross_sections: Path,
    particles: int,
    batches: int,
    repeats: int,
    threads: int,
) -> tuple[float, list[float]]:
    """Run OpenMC and derive throughput from each statepoint's simulation time."""
    import openmc

    openmc.config["cross_sections"] = str(cross_sections.resolve())
    samples = []
    for repeat in range(repeats):
        repeat_dir = run_dir / f"repeat_{repeat + 1}"
        if repeat_dir.exists():
            shutil.rmtree(repeat_dir)
        repeat_dir.mkdir(parents=True)
        statepoint_file = make_openmc_model(h5m_file, particles, batches).run(
            cwd=repeat_dir, threads=threads, output=False
        )
        with openmc.StatePoint(statepoint_file) as statepoint:
            simulation_seconds = float(statepoint.runtime["simulation"])
            histories = int(statepoint.n_particles) * int(statepoint.n_batches)
        samples.append(histories / simulation_seconds)
    return statistics.median(samples), samples


def benchmark(
    meshes: list[tuple[str, float | None, Path]],
    work_dir: Path,
    results_file: Path,
    cross_sections: Path,
    particles: int,
    batches: int,
    repeats: int,
    threads: int,
    skip_transport: bool,
) -> list[dict[str, str]]:
    """Count triangles, run transport, and persist the measurements as CSV."""
    import openmc

    cached = {}
    if results_file.exists():
        with results_file.open(newline="") as stream:
            cached = {row["label"]: row for row in csv.DictReader(stream)}

    rows = []
    for label, size, mesh_file in meshes:
        count = triangle_count(mesh_file)
        accuracy = volume_accuracies(mesh_file)
        if skip_transport:
            if label not in cached:
                raise RuntimeError(
                    f"No cached transport result for {label!r}; rerun without "
                    "--skip-transport."
                )
            speed = float(cached[label]["particles_per_second"])
            samples_text = cached[label]["samples_particles_per_second"]
        else:
            speed, samples = particles_per_second(
                mesh_file,
                work_dir / "openmc" / label,
                cross_sections,
                particles,
                batches,
                repeats,
                threads,
            )
            samples_text = ";".join(f"{sample:.6g}" for sample in samples)
        rows.append(
            {
                "label": label,
                "backend": "gmsh" if size is not None else "cad-to-dagmc-mesher",
                "mesh_size_cm": "" if size is None else f"{size:g}",
                "triangles": str(count),
                "box_volume_accuracy_percent": f'{accuracy["box"]:.6f}',
                "sphere_volume_accuracy_percent": f'{accuracy["sphere"]:.6f}',
                "particles_per_second": f"{speed:.6g}",
                "samples_particles_per_second": samples_text,
                "particles_per_batch": str(particles),
                "batches": str(batches),
                "repeats": str(repeats),
                "threads": str(threads),
                "openmc": openmc.__version__,
                "python": platform.python_version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            }
        )

    results_file.parent.mkdir(parents=True, exist_ok=True)
    with results_file.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return rows


def draw_mesh(ax, triangles: list[np.ndarray], title: str) -> None:
    collection = Poly3DCollection(
        triangles,
        facecolor="#8ecae6",
        edgecolor="#174a66",
        linewidth=0.18,
        alpha=1.0,
    )
    ax.add_collection3d(collection)
    points = np.concatenate(triangles)
    lower = points.min(axis=0)
    upper = points.max(axis=0)
    spans = upper - lower
    padding = spans * 0.015
    ax.set_xlim(lower[0] - padding[0], upper[0] + padding[0])
    ax.set_ylim(lower[1] - padding[1], upper[1] + padding[1])
    ax.set_zlim(lower[2] - padding[2], upper[2] + padding[2])
    # Match the display box to the physical extents instead of placing this
    # long geometry in a cube, which leaves large empty bands around it.
    ax.set_box_aspect(spans, zoom=1.18)
    ax.view_init(elev=22, azim=-55)
    ax.set_axis_off()
    ax.set_title(title, fontsize=14, fontweight="bold", pad=2)


def make_figure(
    output_file: Path,
    gmsh_display_file: Path,
    mesher_file: Path,
    rows: list[dict[str, str]],
) -> None:
    """Render the requested FEM, neutronics, and throughput panels."""
    figure = plt.figure(figsize=(17, 5.2), constrained_layout=True)
    grid = figure.add_gridspec(1, 3, width_ratios=(1, 1, 1.15))

    gmsh_triangles = mesh_triangles(gmsh_display_file)
    mesher_triangles = mesh_triangles(mesher_file)
    gmsh_accuracy = volume_accuracies(gmsh_display_file)
    mesher_accuracy = volume_accuracies(mesher_file)
    draw_mesh(
        figure.add_subplot(grid[0], projection="3d"),
        gmsh_triangles,
        f"FEM mesh\n{len(gmsh_triangles):,} triangles\n"
        f'Volume accuracy: {gmsh_accuracy["overall"]:.2f}%',
    )
    draw_mesh(
        figure.add_subplot(grid[1], projection="3d"),
        mesher_triangles,
        f"Neutronics mesh\n{len(mesher_triangles):,} triangles\n"
        f'Volume accuracy: {mesher_accuracy["overall"]:.2f}%',
    )

    ax = figure.add_subplot(grid[2])
    gmsh_rows = sorted(
        (row for row in rows if row["backend"] == "gmsh"),
        key=lambda row: int(row["triangles"]),
    )
    counts = np.asarray([int(row["triangles"]) for row in gmsh_rows])
    speeds = np.asarray(
        [float(row["particles_per_second"]) for row in gmsh_rows]
    )
    # Timing measurements contain normal run-to-run noise. A quadratic fit in
    # log(triangle count) communicates the measured scaling trend without
    # implying that the small fluctuations between individual runs are a
    # meaningful property of the mesh.
    coefficients = np.polyfit(np.log10(counts), speeds, deg=2)
    smooth_counts = np.geomspace(counts.min(), counts.max(), 300)
    smooth_speeds = np.polyval(coefficients, np.log10(smooth_counts))
    ax.plot(smooth_counts, smooth_speeds, color="#16697a", linewidth=2.5)
    ax.set_title("Tracking performance", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of triangles", fontsize=14, labelpad=8)
    ax.set_ylabel("Simulation speed (particles/s)", fontsize=14, labelpad=8)
    ax.tick_params(axis="both", which="major", labelsize=12)
    ax.grid(alpha=0.25)
    ax.ticklabel_format(axis="both", style="sci", scilimits=(0, 0))
    ax.xaxis.get_offset_text().set_fontsize(12)
    ax.yaxis.get_offset_text().set_fontsize(12)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_file, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    docs_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=docs_dir / "_static" / "mesher_comparison.png",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=docs_dir / "_static" / "mesher_comparison_data.csv",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=docs_dir / "_benchmark_work" / "mesher_comparison",
    )
    parser.add_argument(
        "--cross-sections",
        type=Path,
        default=None,
        help="Optional cross_sections.xml; defaults to the repository's H1 data.",
    )
    parser.add_argument("--particles", type=int, default=DEFAULT_PARTICLES)
    parser.add_argument("--batches", type=int, default=DEFAULT_BATCHES)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--force-mesh", action="store_true")
    parser.add_argument(
        "--skip-transport",
        action="store_true",
        help="Reuse the CSV timing data while rebuilding meshes/the figure.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.cross_sections is None:
        nuclear_data = Path(__file__).resolve().parents[2] / "tests" / "ENDFB-7.1-NNDC_H1.h5"
        if not nuclear_data.is_file():
            raise FileNotFoundError(f"Bundled H1 data not found: {nuclear_data}")
        args.cross_sections = args.work_dir / "cross_sections.xml"
        args.cross_sections.parent.mkdir(parents=True, exist_ok=True)
        args.cross_sections.write_text(
            "<?xml version='1.0' encoding='UTF-8'?>\n"
            "<cross_sections>\n"
            f'  <library materials="H1" path="{nuclear_data.resolve()}" '
            'type="neutron"/>\n'
            "</cross_sections>\n"
        )
    elif not args.cross_sections.is_file():
        raise FileNotFoundError(f"Cross-sections file not found: {args.cross_sections}")

    mesher_file, gmsh_meshes = create_meshes(args.work_dir, args.force_mesh)
    all_meshes = [("cad_to_dagmc_mesher", None, mesher_file)] + [
        (f"gmsh_{size:g}", size, filename) for size, filename in gmsh_meshes
    ]
    rows = benchmark(
        all_meshes,
        args.work_dir,
        args.results,
        args.cross_sections,
        args.particles,
        args.batches,
        args.repeats,
        args.threads,
        args.skip_transport,
    )
    display_file = min(gmsh_meshes, key=lambda item: abs(item[0] - 2.0))[1]
    make_figure(args.output, display_file, mesher_file, rows)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.results}")


if __name__ == "__main__":
    main()
