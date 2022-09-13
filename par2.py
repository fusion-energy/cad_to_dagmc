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
num_points = 2000

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
    num_points=num_points,
)

### INBOARD BLANKET ###

# ib_cooling_channel = paramak.BlanketFP(
#     cc_thickness,
#     90 + inboard_angle_offset,
#     270 - inboard_angle_offset,
#     plasma=plasma,
#     offset_from_plasma=plasma_offset,
#     rotation_angle=rotation_angle,
#     name="inboard_cc",
#     color=cc_c,
#     num_points=num_points,
# )

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


reactor = paramak.Reactor(
    shapes_and_components=[
        # plasma,
        # ib_cooling_channel,
        ib_multiplier,
    ]
)

reactor.export_stp()
