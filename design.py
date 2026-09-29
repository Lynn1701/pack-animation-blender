# Draws the flat front artwork of the pack (a placeholder design) -> design.png
# Run: blender -b --python design.py
#   Optional: PACK_FONT=/path/to/font.ttf blender -b --python design.py
import bpy, math, random, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "design.png")
W, H = 2.0, 3.56          # pack face size (Blender units)
PX_W = 1024

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        pass
sc.render.resolution_x = PX_W
sc.render.resolution_y = int(PX_W * H / W)
sc.view_settings.view_transform = "Standard"
sc.world = bpy.data.worlds.new("W")
sc.world.color = (0, 0, 0)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = H
cam.location = (0, 0, 10)
sc.collection.objects.link(cam)
sc.camera = cam


def emit_mat(name, rgb, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def hexrgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def link(o):
    sc.collection.objects.link(o)
    return o


# ---- background: sapphire blue gradient ----
bpy.ops.mesh.primitive_plane_add(size=1)
bg = bpy.context.object
bg.scale = (W, H, 1)
m = bpy.data.materials.new("BG")
m.use_nodes = True
nt = m.node_tree
nt.nodes.clear()
tc = nt.nodes.new("ShaderNodeTexCoord")
mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (1.1, 0.62, 1)
gr = nt.nodes.new("ShaderNodeTexGradient")
gr.gradient_type = "SPHERICAL"
cr = nt.nodes.new("ShaderNodeValToRGB")
cr.color_ramp.elements[0].color = (*hexrgb("#1a2fb8"), 1)
cr.color_ramp.elements[1].position = 0.85
cr.color_ramp.elements[1].color = (*hexrgb("#4f7dff"), 1)
em = nt.nodes.new("ShaderNodeEmission")
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(tc.outputs["Object"], mp.inputs[0])
nt.links.new(mp.outputs[0], gr.inputs[0])
nt.links.new(gr.outputs[1], cr.inputs[0])
nt.links.new(cr.outputs[0], em.inputs[0])
nt.links.new(em.outputs[0], out.inputs[0])
bg.data.materials.append(m)

# ---- top/bottom crimp bands (darker, vertical ridges) ----
CRIMP = 0.18
crimp_m = emit_mat("Crimp", hexrgb("#1528a0"))
line_m = emit_mat("CrimpLine", hexrgb("#3050d8"))
for s in (1, -1):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, s * (H / 2 - CRIMP / 2), 0.01))
    o = bpy.context.object
    o.scale = (W, CRIMP, 1)
    o.data.materials.append(crimp_m)
    for i in range(48):
        x = -W / 2 + (i + 0.5) * W / 48
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x, s * (H / 2 - CRIMP / 2), 0.02))
        l = bpy.context.object
        l.scale = (0.012, CRIMP, 1)
        l.data.materials.append(line_m)

# ---- "circuit" rings ----
ring_m = emit_mat("Ring", hexrgb("#a9c8ff"))
ring_dim = emit_mat("RingDim", hexrgb("#6f95f0"))
for r, mat, th in ((0.62, ring_m, 0.022), (0.78, ring_dim, 0.012), (0.95, ring_dim, 0.008)):
    bpy.ops.mesh.primitive_circle_add(vertices=128, radius=r, location=(0, 0.15, 0.03))
    c = bpy.context.object
    bpy.ops.object.convert(target="CURVE")
    c.data.bevel_depth = th
    c.data.materials.append(mat)
for x in (-0.55, 0.55):
    for sy in (1, -1):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x, 0.15 + sy * 0.95, 0.03))
        l = bpy.context.object
        l.scale = (0.012, 0.9, 1)
        l.data.materials.append(ring_dim)

# ---- emblem: disc + sapphire gem ----
bpy.ops.mesh.primitive_circle_add(vertices=128, radius=0.52, fill_type="NGON", location=(0, 0.15, 0.05))
bpy.context.object.data.materials.append(emit_mat("Disc", hexrgb("#0d1650")))
bpy.ops.mesh.primitive_circle_add(vertices=128, radius=0.47, fill_type="NGON", location=(0, 0.15, 0.06))
bpy.context.object.data.materials.append(emit_mat("Disc2", hexrgb("#dce8ff")))
gem = [("#1c3fcf", 0.34, 0), ("#3a68ff", 0.22, 0), ("#9cc0ff", 0.1, 0)]
for i, (col, r, _) in enumerate(gem):
    bpy.ops.mesh.primitive_circle_add(vertices=6, radius=r, fill_type="NGON",
                                      location=(0, 0.15, 0.07 + i * 0.01), rotation=(0, 0, math.pi / 6))
    bpy.context.object.data.materials.append(emit_mat(f"Gem{i}", hexrgb(col)))
facet_m = emit_mat("Facet", hexrgb("#bcd4ff"))
for k in range(6):
    a = math.pi / 6 + k * math.pi / 3 + math.pi / 2
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.17 * math.cos(a), 0.15 + 0.17 * math.sin(a), 0.1),
                                     rotation=(0, 0, a))
    f = bpy.context.object
    f.scale = (0.24, 0.008, 1)
    f.data.materials.append(facet_m)

# ---- text ----
FONT = os.environ.get("PACK_FONT", "/System/Library/Fonts/Supplemental/Futura.ttc")  # any .ttf/.otf works
font = bpy.data.fonts.load(FONT)


def text(body, y, size, mat, z=0.2, bold=0.0):
    bpy.ops.object.text_add(location=(0, y, z))
    t = bpy.context.object
    t.data.body = body
    t.data.font = font
    t.data.size = size
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    t.data.offset = bold
    t.data.space_character = 1.15
    t.data.materials.append(mat)
    return t


white = emit_mat("White", (1, 1, 1))
text("NOVA  TCG", 1.28, 0.17, white, bold=0.004)

# rounded "SAPPHIRE" label
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.92, 0.15))
box = bpy.context.object
box.scale = (1.45, 0.34, 1)
bpy.ops.object.transform_apply(scale=True)
bev = box.modifiers.new("b", "BEVEL")
bev.affect = "VERTICES"
bev.width = 0.08
bev.segments = 8
box.data.materials.append(emit_mat("Box", hexrgb("#0b1240")))
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.92, 0.14))
box2 = bpy.context.object
box2.scale = (1.51, 0.40, 1)
bpy.ops.object.transform_apply(scale=True)
b2 = box2.modifiers.new("b", "BEVEL")
b2.affect = "VERTICES"
b2.width = 0.1
b2.segments = 8
box2.data.materials.append(emit_mat("BoxEdge", hexrgb("#e8f0ff")))
text("SAPPHIRE", -0.92, 0.25, white, bold=0.006)
text("PACK", -1.3, 0.16, white, bold=0.004)

# ---- sparkles ----
random.seed(7)
spark = emit_mat("Spark", hexrgb("#d6e6ff"))
for i in range(26):
    x = random.uniform(-0.9, 0.9)
    y = random.uniform(-1.55, 1.55)
    if abs(x) < 0.8 and -1.2 < y < 1.15:
        continue
    s = random.uniform(0.02, 0.05)
    for rot in (0, math.pi / 2):
        bpy.ops.mesh.primitive_circle_add(vertices=4, radius=1, fill_type="NGON", location=(x, y, 0.25),
                                          rotation=(0, 0, rot))
        o = bpy.context.object
        o.scale = (s, s * 0.22, 1)
        o.data.materials.append(spark)

sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("WROTE", OUT)
