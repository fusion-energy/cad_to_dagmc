def make_dagmc_model():
    import paramak

    # all units in degrees
    inboard_angle_offset = 5
    outboard_angle_offset = 12

    # all units in cm
    plasma_offset = 10

    # Whether or not a TBR>1 can be achieved is highly dependent on VV thickness and material
    vv_thickness = 2
    first_wall_thickness = 1
    inboard_blanket_thickness = 100
    outboard_blanket_thickness = 120
    rotation_angle = 180
    num_points = 400

    # Cooling channel:
    cc_thickness = 2

    # Multiplier:
    mult_thickness = 1

    # Outer VV:
    outer_vv_thickness = 3

    # Colors:
    plasma_c = [0.94, 0.012, 1]
    tank_c = [0.01176, 0.988, 0.776]
    cc_c = tank_c
    mult_c = [1, 0, 0]
    vv_c = [0.4, 0.4, 0.4]
    outer_vv_c = vv_c

    plasma = paramak.Plasma(
        major_radius=330,
        minor_radius=113,
        triangularity=0.33,
        elongation=1.84,
        rotation_angle=rotation_angle,
        name="plasma",
        color=plasma_c,
    )

    ### INBOARD BLANKET ###

    ib_cooling_channel = paramak.BlanketFP(
        cc_thickness,
        90 + inboard_angle_offset,
        270 - inboard_angle_offset,
        plasma=plasma,
        offset_from_plasma=plasma_offset,
        rotation_angle=rotation_angle,
        name="inboard_cc",
        color=cc_c,
        num_points=num_points,
    )

    ib_multiplier = paramak.BlanketFP(
        mult_thickness,
        90 + inboard_angle_offset,
        270 - inboard_angle_offset,
        plasma=plasma,
        offset_from_plasma=plasma_offset + cc_thickness,
        rotation_angle=rotation_angle,
        name="inboard_multiplier",
        color=mult_c,
        num_points=num_points,
    )

    ib_outer_vv = paramak.BlanketFP(
        outer_vv_thickness,
        90 + inboard_angle_offset,
        270 - inboard_angle_offset,
        plasma=plasma,
        offset_from_plasma=plasma_offset + cc_thickness + mult_thickness,
        rotation_angle=rotation_angle,
        name="inboard_outer_vv",
        color=outer_vv_c,
        num_points=num_points,
    )

    ib_tank = paramak.BlanketFP(
        inboard_blanket_thickness,
        90 + inboard_angle_offset,
        270 - inboard_angle_offset,
        plasma=plasma,
        offset_from_plasma=plasma_offset
        + cc_thickness
        + mult_thickness
        + outer_vv_thickness,
        rotation_angle=rotation_angle,
        name="inboard_tank",
        color=tank_c,
        num_points=num_points,
    )

    ### OUTBOARD BLANKET ###

    ob_cooling_channel = paramak.BlanketFP(
        cc_thickness,
        -90 + outboard_angle_offset,
        90 - outboard_angle_offset,
        plasma=plasma,
        offset_from_plasma=plasma_offset,
        rotation_angle=rotation_angle,
        name="outboard_cc",
        color=cc_c,
        num_points=num_points,
    )

    ob_multiplier = paramak.BlanketFP(
        mult_thickness,
        -90 + outboard_angle_offset,
        90 - outboard_angle_offset,
        plasma=plasma,
        offset_from_plasma=plasma_offset + cc_thickness,
        rotation_angle=rotation_angle,
        name="outboard_multiplier",
        color=mult_c,
        num_points=num_points,
    )

    ob_outer_vv = paramak.BlanketFP(
        outer_vv_thickness,
        -90 + outboard_angle_offset,
        90 - outboard_angle_offset,
        plasma=plasma,
        offset_from_plasma=plasma_offset + cc_thickness + mult_thickness,
        rotation_angle=rotation_angle,
        name="outboard_outer_vv",
        color=outer_vv_c,
        num_points=num_points,
    )

    ob_tank = paramak.BlanketFP(
        outboard_blanket_thickness,
        -90 + outboard_angle_offset,
        90 - outboard_angle_offset,
        plasma=plasma,
        offset_from_plasma=plasma_offset
        + cc_thickness
        + mult_thickness
        + outer_vv_thickness,
        rotation_angle=rotation_angle,
        name="outboard_tank",
        color=tank_c,
        num_points=num_points,
    )

    vv = paramak.BlanketFP(
        vv_thickness,
        -90,
        270,
        plasma=plasma,
        offset_from_plasma=plasma_offset - vv_thickness - 1,
        rotation_angle=rotation_angle,
        name="vv",
        color=vv_c,
        num_points=num_points,
    )

    first_wall = paramak.BlanketFP(
        first_wall_thickness,
        -90,
        270,
        plasma=plasma,
        offset_from_plasma=plasma_offset - vv_thickness - first_wall_thickness,
        rotation_angle=rotation_angle,
        name="first_wall",
        color=[0.6, 0.6, 0.6],
        num_points=num_points,
    )

    reactor = paramak.Reactor(
        shapes_and_components=[
            plasma,
            vv,
            first_wall,
            ob_cooling_channel,
            ob_multiplier,
            ob_outer_vv,
            ob_tank,
            ib_cooling_channel,
            ib_multiplier,
            ib_outer_vv,
            ib_tank,
        ]
    )
    print("export_dagmc_h5m")
    reactor.export_dagmc_h5m(filename="dagmc.h5m", min_mesh_size=1, max_mesh_size=20)


def run_neutronics_simulation():

    import openmc
    import openmc_data_downloader as odd
    import math

    # simplified material definitions have been used to keen this example minimal
    mat_plasma = openmc.Material(name="plasma")
    mat_plasma.add_element("H", 1, "ao")
    mat_plasma.set_density("g/cm3", 0.00001)

    mat_inboard_cc = openmc.Material(name="inboard_cc")
    mat_inboard_cc.add_element("Cu", 1, "ao")
    mat_inboard_cc.set_density("g/cm3", 8.96)

    mat_inboard_multiplier = openmc.Material(name="inboard_multiplier")
    mat_inboard_multiplier.add_element("Cu", 1, "ao")
    mat_inboard_multiplier.set_density("g/cm3", 8.96)

    mat_inboard_outer_vv = openmc.Material(name="inboard_outer_vv")
    mat_inboard_outer_vv.add_element("Cu", 1, "ao")
    mat_inboard_outer_vv.set_density("g/cm3", 8.96)

    mat_inboard_tank = openmc.Material(name="inboard_tank")
    mat_inboard_tank.add_element("Cu", 1, "ao")
    mat_inboard_tank.set_density("g/cm3", 8.96)

    mat_outboard_cc = openmc.Material(name="outboard_cc")
    mat_outboard_cc.add_element("Fe", 1, "ao")
    mat_outboard_cc.set_density("g/cm3", 8.96)

    mat_outboard_multiplier = openmc.Material(name="outboard_multiplier")
    mat_outboard_multiplier.add_element("Fe", 1, "ao")
    mat_outboard_multiplier.set_density("g/cm3", 8.96)

    mat_outboard_outer_vv = openmc.Material(name="outboard_outer_vv")
    mat_outboard_outer_vv.add_element("Fe", 1, "ao")
    mat_outboard_outer_vv.set_density("g/cm3", 8.96)

    mat_outboard_tank = openmc.Material(name="outboard_tank")
    mat_outboard_tank.add_element("Fe", 1, "ao")
    mat_outboard_tank.set_density("g/cm3", 8.96)

    mat_vv = openmc.Material(name="vv")
    mat_vv.add_element("W", 1, "ao")
    mat_vv.set_density("g/cm3", 19.3)

    mat_first_wall = openmc.Material(name="first_wall")
    mat_first_wall.add_element("Fe", 1, "ao")
    mat_first_wall.set_density("g/cm3", 7.7)

    materials = openmc.Materials(
        [
            mat_plasma,
            mat_inboard_cc,
            mat_inboard_multiplier,
            mat_inboard_outer_vv,
            mat_inboard_tank,
            mat_outboard_cc,
            mat_outboard_multiplier,
            mat_outboard_outer_vv,
            mat_outboard_tank,
            mat_vv,
            mat_first_wall,
        ]
    )

    # downloads the nuclear data and sets the openmc_cross_sections environmental variable
    odd.just_in_time_library_generator(libraries="ENDFB-7.1-NNDC", materials=materials)

    # makes use of the dagmc geometry
    dag_univ = openmc.DAGMCUniverse("dagmc.h5m")

    # creates an edge of universe boundary surface
    vac_surf = openmc.Sphere(r=10000, surface_id=9999, boundary_type="vacuum")

    # specifies the region as below the universe boundary
    region = -vac_surf

    # creates a cell from the region and fills the cell with the dagmc geometry
    containing_cell = openmc.Cell(cell_id=9999, region=region, fill=dag_univ)

    geometry = openmc.Geometry(root=[containing_cell])

    # creates a simple isotropic neutron source in the center with 14MeV neutrons
    my_source = openmc.Source()
    # the distribution of radius is just a single value at the plasma major radius
    radius = openmc.stats.Discrete([293.0], [1])
    # the distribution of source z values is just a single value
    z_values = openmc.stats.Discrete([0], [1])
    # the distribution of source azimuthal angles values is a uniform distribution between 0 and 0.5 Pi
    # these angles must be the same as the reflective angles
    angle = openmc.stats.Uniform(a=0.0, b=math.radians(90))
    # this makes the ring source using the three distributions and a radius
    my_source.space = openmc.stats.CylindricalIndependent(
        r=radius, phi=angle, z=z_values, origin=(0.0, 0.0, 0.0)
    )
    # sets the direction to isotropic
    my_source.angle = openmc.stats.Isotropic()
    # sets the energy distribution to a Muir distribution neutrons
    my_source.energy = openmc.stats.Muir(e0=14080000.0, m_rat=5.0, kt=20000.0)

    # specifies the simulation computational intensity
    settings = openmc.Settings()
    settings.batches = 10
    settings.particles = 10000
    settings.inactive = 0
    settings.run_mode = "fixed source"
    settings.source = my_source

    # adds a tally to record the heat deposited in entire geometry
    cell_tally = openmc.Tally(name="heating")
    cell_tally.scores = ["heating"]

    # creates a mesh that covers the geometry
    mesh = openmc.RegularMesh()
    mesh.dimension = [100, 100, 100]
    mesh.lower_left = [
        0,
        0,
        -350,
    ]  # x,y,z coordinates start at 0 as this is a sector model
    mesh.upper_right = [650, 650, 350]

    # makes a mesh tally using the previously created mesh and records heating on the mesh
    mesh_tally = openmc.Tally(name="heating_on_mesh")
    mesh_filter = openmc.MeshFilter(mesh)
    mesh_tally.filters = [mesh_filter]
    mesh_tally.scores = ["heating"]

    # groups the two tallies
    tallies = openmc.Tallies([cell_tally, mesh_tally])

    # builds the openmc model
    my_model = openmc.Model(
        materials=materials, geometry=geometry, settings=settings, tallies=tallies
    )

    # starts the simulation
    my_model.run()


make_dagmc_model()
run_neutronics_simulation()
