# Builds a 3D booster pack with a gentle looping sway and renders it to frames/
# Run: blender -b --python pack.py -- [test]
#   "test" renders only 3 frames for a quick check
import bpy, bmesh, math, random, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.join(HERE, "design.png")      # swap in your real artwork here
FRAMES = 150                                   # 5 seconds @ 30 fps, seamless loop
TEST = "test" in sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else False
RES = (1280, 960)

W, BODY, CRIMP = 2.0, 3.2, 0.18                # width, body height, crimp band
H = BODY + 2 * CRIMP
PUFF = 0.24                                    # how much the pack puffs out
TEETH, TOOTH_D = 36, 0.035

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        pass
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.fps = 30
sc.frame_start, sc.frame_end = 1, FRAMES
try:
    sc.eevee.use_raytracing = True
    sc.eevee.taa_render_samples = 64
except AttributeError:
    pass
sc.view_settings.view_transform = "Standard"


def hexrgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ---------------- pack mesh ----------------
def tri(x):
    f = x - math.floor(x)
    return 1 - abs(2 * f - 1)


def pack_side(sign, nx=288, ny=240):
    """Mot mat cua goi. sign=+1 mat truoc, -1 mat sau."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    grid = []
    for j in range(ny + 1):
        row = []
        y0 = -H / 2 + H * j / ny
        for i in range(nx + 1):
            x = -W / 2 + W * i / nx
            u = x / (W / 2)
            if abs(y0) <= BODY / 2:
                vb = y0 / (BODY / 2)
                z = PUFF * (1 - abs(u) ** 5) ** 0.4 * (1 - abs(vb) ** 7) ** 0.45
                y = y0
            else:
                # crimp band: flat, vertical ridges, serrated outer edge
                k = (abs(y0) - BODY / 2) / CRIMP
                z = 0.004 + 0.006 * (0.5 + 0.5 * math.sin(x * 2 * math.pi * 24))
                y = y0 - math.copysign(k * TOOTH_D * tri((x + W / 2) / W * TEETH), y0)
            # subtle wrinkles for realism
            z += 0.004 * math.sin(x * 9 + y0 * 5) * math.sin(y0 * 7 - x * 3) * (z > 0.02)
            v = bm.verts.new((x, y, sign * z))
            row.append((v, ((x + W / 2) / W if sign > 0 else 1 - (x + W / 2) / W, (y0 + H / 2) / H)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            if sign < 0:
                q.reverse()
            f = bm.faces.new([p[0] for p in q])
            f.smooth = True
            for loop, p in zip(f.loops, q):
                loop[uv].uv = p[1]
    me = bpy.data.meshes.new("side")
    bm.to_mesh(me)
    bm.free()
    return me


def foil_mat(name, img=None, tint="#1a2a9a"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    if img:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(img)
        tex.interpolation = "Cubic"
        nt.links.new(tex.outputs[0], b.inputs["Base Color"])
        # keep the artwork readable even in dark reflections
        nt.links.new(tex.outputs[0], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = 0.35
    else:
        b.inputs["Base Color"].default_value = (*hexrgb(tint), 1)
    b.inputs["Metallic"].default_value = 0.8
    b.inputs["Roughness"].default_value = 0.13
    b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Roughness"].default_value = 0.04
    # foil crinkle marks
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 14
    nz.inputs["Detail"].default_value = 6
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.06
    nt.links.new(nz.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m


rig = bpy.data.objects.new("PackRig", None)
sc.collection.objects.link(rig)
for sign, mat in ((1, foil_mat("Front", DESIGN)), (-1, foil_mat("Back"))):
    o = bpy.data.objects.new("Front" if sign > 0 else "Back", pack_side(sign))
    o.data.materials.append(mat)
    o.rotation_euler = (math.radians(90), 0, 0)   # local z -> faces the camera (-Y)
    o.parent = rig
    sc.collection.objects.link(o)
# check: Rx(90) maps (0,0,1) -> (0,-1,0), so local z points at the camera

# ---------------- gentle looping sway ----------------
for f in range(1, FRAMES + 1):
    t = 2 * math.pi * (f - 1) / FRAMES
    # rotate back and forth only, like Magic Eden pack videos, no bobbing
    rig.rotation_euler = (0,
                          math.radians(2.5) * math.sin(t),
                          math.radians(13) * math.sin(t))
    rig.location = (0, 0, 0)
    rig.keyframe_insert("rotation_euler", frame=f)
    rig.keyframe_insert("location", frame=f)

# ---------------- world: virtual softboxes for reflections ----------------
world = bpy.data.worlds.new("Studio")
sc.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Generated"], sep.inputs[0])


def band(axis_out, lo, hi, soft=0.08):
    """1 khi lo<d<hi (mem o mep)."""
    a = nt.nodes.new("ShaderNodeMapRange")
    a.interpolation_type = "SMOOTHSTEP"
    a.inputs["From Min"].default_value = lo - soft
    a.inputs["From Max"].default_value = lo + soft
    b = nt.nodes.new("ShaderNodeMapRange")
    b.interpolation_type = "SMOOTHSTEP"
    b.inputs["From Min"].default_value = hi + soft
    b.inputs["From Max"].default_value = hi - soft
    nt.links.new(axis_out, a.inputs["Value"])
    nt.links.new(axis_out, b.inputs["Value"])
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = "MULTIPLY"
    nt.links.new(a.outputs[0], m.inputs[0])
    nt.links.new(b.outputs[0], m.inputs[1])
    return m.outputs[0]


def mul(a, b):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = "MULTIPLY"
    nt.links.new(a, m.inputs[0])
    if isinstance(b, float):
        m.inputs[1].default_value = b
    else:
        nt.links.new(b, m.inputs[1])
    return m.outputs[0]


def add(a, b):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = "ADD"
    nt.links.new(a, m.inputs[0])
    nt.links.new(b, m.inputs[1])
    return m.outputs[0]


X, Y, Z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
front = band(Y, -1.1, -0.15, 0.15)                     # camera side
left = mul(mul(band(X, -0.85, -0.45), front), 2.5)     # left softbox (key light)
right = mul(mul(band(X, 0.35, 0.6), front), 1.2)       # right softbox
top = mul(band(Z, 0.55, 1.1, 0.1), 2.5)                # top light
rim = mul(mul(band(Y, 0.3, 1.1, 0.2), band(X, -0.3, 0.3)), 1.5)
light = add(add(left, right), add(top, rim))
col = nt.nodes.new("ShaderNodeMixRGB")
col.blend_type = "ADD"
col.inputs[0].default_value = 1
col.inputs[1].default_value = (*hexrgb("#0a1030"), 1)
cm = nt.nodes.new("ShaderNodeCombineColor")
nt.links.new(mul(light, 0.85), cm.inputs[0])
nt.links.new(mul(light, 0.92), cm.inputs[1])
nt.links.new(light, cm.inputs[2])
nt.links.new(cm.outputs[0], col.inputs[2])
bgn = nt.nodes.new("ShaderNodeBackground")
nt.links.new(col.outputs[0], bgn.inputs[0])
wo = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bgn.outputs[0], wo.inputs[0])

def area(name, loc, size, energy, color=(0.85, 0.9, 1)):
    l = bpy.data.lights.new(name, "AREA")
    l.shape = "RECTANGLE"
    l.size, l.size_y = size
    l.energy = energy
    l.color = color
    o = bpy.data.objects.new(name, l)
    o.location = loc
    sc.collection.objects.link(o)
    tr = o.constraints.new("TRACK_TO")
    tr.target = rig
    return o


area("KeyLeft", (-5, -7, 1.5), (0.5, 7), 230)
area("FillRight", (5, -7, -0.5), (0.4, 6), 140, (0.7, 0.8, 1))
area("Top", (0, -4, 6), (6, 0.8), 400)
area("RimBack", (0, 5, 3), (4, 4), 600, (0.5, 0.55, 1))

# ---------------- background: moving diagonal light beams ----------------
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 6, 0), rotation=(math.radians(90), 0, 0))
bgp = bpy.context.object
bgp.scale = (26, 20, 1)
m = bpy.data.materials.new("BGRays")
m.use_nodes = True
n2 = m.node_tree
n2.nodes.clear()
tc2 = n2.nodes.new("ShaderNodeTexCoord")
mp = n2.nodes.new("ShaderNodeMapping")
mp.inputs["Rotation"].default_value = (0, 0, math.radians(35))
wv = n2.nodes.new("ShaderNodeTexWave")
wv.inputs["Scale"].default_value = 1.3
wv.inputs["Distortion"].default_value = 4.0
wv.inputs["Detail"].default_value = 1.5
wv.inputs["Detail Scale"].default_value = 0.6
rp = n2.nodes.new("ShaderNodeValToRGB")
rp.color_ramp.elements[0].color = (*hexrgb("#02030f"), 1)
rp.color_ramp.elements[0].position = 0.15
rp.color_ramp.elements[1].position = 1.0
rp.color_ramp.elements[1].color = (*hexrgb("#3a2cff"), 1)
e = rp.color_ramp.elements.new(0.6)
e.color = (*hexrgb("#0b0f5c"), 1)
# dark vignette in the corners
gr = n2.nodes.new("ShaderNodeTexGradient")
gr.gradient_type = "SPHERICAL"
mp2 = n2.nodes.new("ShaderNodeMapping")
mp2.inputs["Scale"].default_value = (1.6, 2.0, 1)
mx = n2.nodes.new("ShaderNodeMixRGB")
mx.blend_type = "MULTIPLY"
mx.inputs[0].default_value = 1
vr = n2.nodes.new("ShaderNodeValToRGB")
vr.color_ramp.elements[0].color = (0.25, 0.25, 0.3, 1)
vr.color_ramp.elements[1].position = 0.6
vr.color_ramp.elements[1].color = (1.4, 1.4, 1.4, 1)
em = n2.nodes.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 0.8
o2 = n2.nodes.new("ShaderNodeOutputMaterial")
n2.links.new(tc2.outputs["Object"], mp.inputs[0])
n2.links.new(mp.outputs[0], wv.inputs[0])
n2.links.new(wv.outputs[0], rp.inputs[0])
n2.links.new(tc2.outputs["Object"], mp2.inputs[0])
n2.links.new(mp2.outputs[0], gr.inputs[0])
n2.links.new(gr.outputs[1], vr.inputs[0])
n2.links.new(rp.outputs[0], mx.inputs[1])
n2.links.new(vr.outputs[0], mx.inputs[2])
n2.links.new(mx.outputs[0], em.inputs[0])
n2.links.new(em.outputs[0], o2.inputs[0])
bgp.data.materials.append(m)
bgp.visible_diffuse = bgp.visible_glossy = False
# beams drift diagonally and loop (shift by one wave period)
for f, off in ((1, 0.0), (FRAMES + 1, 0.12)):
    mp.inputs["Location"].default_value = (off, 0, 0)
    mp.inputs["Location"].keyframe_insert("default_value", frame=f)
for fc in (m.node_tree.animation_data.action.fcurves if hasattr(m.node_tree.animation_data.action, "fcurves") else []):
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"

# ---------------- sparkle particles ----------------
random.seed(3)
dust = bpy.data.materials.new("Dust")
dust.use_nodes = True
dn = dust.node_tree
dn.nodes.clear()
de = dn.nodes.new("ShaderNodeEmission")
de.inputs["Color"].default_value = (0.75, 0.82, 1, 1)
de.inputs["Strength"].default_value = 1.5
do = dn.nodes.new("ShaderNodeOutputMaterial")
dn.links.new(de.outputs[0], do.inputs[0])
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
proto = bpy.context.object
proto.data.materials.append(dust)
proto.hide_render = True
proto.hide_viewport = True
for i in range(45):
    d = proto.copy()
    sc.collection.objects.link(d)
    d.hide_render = d.hide_viewport = False
    d.scale = [random.uniform(0.008, 0.02)] * 3
    x0, y0, z0 = random.uniform(-5, 5), random.uniform(0.5, 5), random.uniform(-3.5, 3.5)
    dx, dz = random.uniform(-0.3, 0.3), random.uniform(0.2, 0.6)
    for f in (1, FRAMES):
        s = (f - 1) / FRAMES
        d.location = (x0 + dx * s, y0, z0 + dz * s)
        d.keyframe_insert("location", frame=f)

# ---------------- camera ----------------
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.lens = 85
cam.location = (0, -16, 0)
cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = 16
cam.data.dof.aperture_fstop = 2.0
sc.collection.objects.link(cam)
sc.camera = cam

# ---------------- glow ----------------
try:
    ng = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    gl = ng.nodes.new("CompositorNodeGlare")
    go = ng.nodes.new("NodeGroupOutput")
    try:
        gl.inputs["Type"].default_value = "Bloom"
        gl.inputs["Threshold"].default_value = 1.2
        gl.inputs["Strength"].default_value = 0.25
        gl.inputs["Size"].default_value = 0.5
    except Exception:
        gl.glare_type = "BLOOM"
    ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
    ng.links.new(gl.outputs["Image"], go.inputs[0])
    sc.compositing_node_group = ng
    print("GLOW OK")
except Exception as ex:
    print("GLOW SKIP", ex)

# ---------------- render ----------------
out_dir = os.path.join(HERE, "frames")
os.makedirs(out_dir, exist_ok=True)
sc.render.image_settings.file_format = "PNG"
frames = [1, 38, 76, 106] if TEST else range(1, FRAMES + 1)
for f in frames:
    sc.frame_set(f)
    sc.render.filepath = os.path.join(out_dir, f"f_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    print("FRAME", f, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "pack_demo.blend"))
print("DONE")
