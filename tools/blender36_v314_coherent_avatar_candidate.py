import bpy, os, sys, json, hashlib
from mathutils import Vector

EXPECTED_MORPHS = [
    "smile", "blink_left", "blink_right", "mouth_open", "jaw_open", "jaw_hinge",
    "brow_raise", "cheek_raise", "lip_press", "lip_fv", "lip_round", "tongue_tip"
]

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def material(name, color, rough=0.62, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.roughness = rough
    m.metallic = metallic
    return m

def uv(name, loc, scale, mat, segments=40, rings=28):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def capsule(name, a, b, radius_x, mat, radius_y=None):
    a, b = Vector(a), Vector(b)
    vec = b - a
    mid = (a + b) * 0.5
    obj = uv(name, mid, (radius_x, radius_y or radius_x, vec.length * 0.5 + radius_x), mat, 32, 20)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = vec.to_track_quat("Z", "Y")
    return obj

def fuse(objects, name, voxel=0.008, smooth_iterations=5):
    objects = [obj for obj in objects if obj and obj.name in bpy.data.objects]
    if not objects:
        raise RuntimeError("No objects to fuse for " + name)
    base = objects[0]
    base_material = next((m for obj in objects for m in obj.data.materials if m), None)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    remesh = obj.modifiers.new("Fuse anatomical volumes", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = voxel
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    if smooth_iterations:
        smooth = obj.modifiers.new("Soft transitions", "SMOOTH")
        smooth.factor = 0.35
        smooth.iterations = smooth_iterations
        bpy.ops.object.modifier_apply(modifier=smooth.name)
    obj.data.materials.clear()
    if base_material:
        obj.data.materials.append(base_material)
        for p in obj.data.polygons:
            p.material_index = 0
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj

def shape_key(obj, name, transform):
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    key = obj.shape_key_add(name=name, from_mix=False)
    basis = obj.data.shape_keys.key_blocks["Basis"]
    for i, vertex in enumerate(basis.data):
        key.data[i].co = transform(vertex.co.copy(), i)
    key.value = 0.0
    return key

def bounds(meshes):
    pts = [obj.matrix_world @ v.co for obj in meshes for v in obj.data.vertices]
    if not pts:
        return None
    lo = [min(float(v[i]) for v in pts) for i in range(3)]
    hi = [max(float(v[i]) for v in pts) for i in range(3)]
    return {
        "min": [round(v, 6) for v in lo],
        "max": [round(v, 6) for v in hi],
        "size": [round(hi[i] - lo[i], 6) for i in range(3)],
        "center": [round((lo[i] + hi[i]) / 2, 6) for i in range(3)]
    }

def camera(scene, name, location, target, ortho=1.9):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    data.type = "ORTHO"
    data.ortho_scale = ortho
    return obj

def render(scene, cam, path):
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def main():
    args = args_after_dashdash()
    out = os.path.abspath("artifacts/v314-coherent-avatar-candidate")
    for i, arg in enumerate(args[:-1]):
        if arg == "--output-dir":
            out = os.path.abspath(args[i + 1])
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    skin = material("Skin warm natural", (0.62, 0.365, 0.275), 0.58)
    shirt = material("Tee soft ivory", (0.88, 0.86, 0.81), 0.7)
    denim = material("Shorts deep denim", (0.08, 0.19, 0.34), 0.82)
    denim_light = material("Denim stitching", (0.32, 0.52, 0.69), 0.75)
    hair = material("Hair natural black", (0.018, 0.015, 0.02), 0.32)
    eye_white = material("Eye ivory", (0.94, 0.91, 0.85), 0.3)
    iris = material("Iris warm brown", (0.16, 0.065, 0.025), 0.3)
    pupil = material("Pupil dark", (0.012, 0.009, 0.008), 0.2)
    lip = material("Lips muted rose", (0.47, 0.15, 0.17), 0.42)
    sneaker = material("Sneaker ivory", (0.88, 0.88, 0.84), 0.65)
    sneaker_accent = material("Sneaker gray accent", (0.36, 0.41, 0.46), 0.62)
    sole = material("Rubber sole", (0.16, 0.17, 0.18), 0.75)
    belt_mat = material("Belt dark charcoal", (0.07, 0.07, 0.075), 0.5, 0.15)
    metal = material("Small silver details", (0.58, 0.60, 0.62), 0.3, 0.65)

    # Proportions are built directly in meter-like Blender units; no destructive global rescale.
    # T-shirt volume, blended into a continuous adult torso silhouette.
    trunk_parts = [
        uv("tee_waist_volume", (0, 0, 1.055), (0.148, 0.102, 0.142), shirt),
        uv("tee_torso_volume", (0, 0, 1.185), (0.177, 0.112, 0.168), shirt),
        uv("tee_shoulders_volume", (0, 0, 1.285), (0.173, 0.104, 0.082), shirt),
        uv("tee_sleeve.L", (-0.163, -0.004, 1.258), (0.052, 0.067, 0.057), shirt),
        uv("tee_sleeve.R", (0.163, -0.004, 1.258), (0.052, 0.067, 0.057), shirt)
    ]
    tee = fuse(trunk_parts, "Tee_Fitted_Continuous", 0.007, 5)

    # High-waist denim shorts with fuller hip silhouette and short hems.
    shorts_parts = [
        uv("shorts_hip_shell", (0, 0.002, 0.914), (0.202, 0.121, 0.125), denim),
        capsule("shorts_leg.L", (-0.096, 0.0, 0.89), (-0.103, 0.0, 0.735), 0.092, denim, 0.105),
        capsule("shorts_leg.R", (0.096, 0.0, 0.89), (0.103, 0.0, 0.735), 0.092, denim, 0.105)
    ]
    shorts = fuse(shorts_parts, "Denim_Shorts_Continuous", 0.006, 4)

    # Waistband/belt and button.
    bpy.ops.mesh.primitive_torus_add(major_radius=0.145, minor_radius=0.0045, major_segments=64, minor_segments=10, location=(0, 0, 0.978))
    belt = bpy.context.object
    belt.name = "Shorts_Waist_Belt"
    belt.data.materials.append(belt_mat)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=(0, -0.121, 0.981))
    button = bpy.context.object
    button.name = "Shorts_Silver_Button"
    button.scale = (0.012, 0.006, 0.012)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    button.data.materials.append(metal)

    # Adult legs: continuous fused thigh-to-calf surfaces, one object per side.
    leg_meshes = []
    for sign, side in [(-1, "L"), (1, "R")]:
        leg_parts = [
            capsule("thigh." + side, (sign * 0.102, 0.0, 0.765), (sign * 0.105, 0.0, 0.425), 0.092, skin, 0.088),
            uv("knee." + side, (sign * 0.105, 0.0, 0.425), (0.062, 0.066, 0.062), skin),
            capsule("calf." + side, (sign * 0.105, 0.0, 0.43), (sign * 0.108, 0.0, 0.13), 0.061, skin, 0.063)
        ]
        leg_meshes.append(fuse(leg_parts, "Leg_Continuous_" + side, 0.005, 5))

    # Shoes: soles, uppers, toe caps, and understated gray panels.
    for sign, side in [(-1, "L"), (1, "R")]:
        x = sign * 0.11
        uv("Sneaker_Sole." + side, (x, -0.038, 0.027), (0.072, 0.132, 0.020), sole, 36, 20)
        upper = uv("Sneaker_Upper." + side, (x, -0.045, 0.069), (0.065, 0.116, 0.047), sneaker, 36, 24)
        toe = uv("Sneaker_Toe." + side, (x, -0.115, 0.071), (0.054, 0.047, 0.030), sneaker, 32, 18)
        fuse([upper, toe], "Sneaker_Upper_Continuous." + side, 0.004, 3)
        uv("Sneaker_Accent." + side, (x + sign * 0.049, -0.015, 0.079), (0.005, 0.035, 0.012), sneaker_accent, 24, 16)
        for i in range(3):
            uv("Lace_" + side + "_" + str(i), (x, -0.067 + i * 0.023, 0.108), (0.007, 0.003, 0.0025), eye_white, 12, 8)

    # Arms hang naturally at the sides and overlap sleeves/torso at the shoulder.
    for sign, side in [(-1, "L"), (1, "R")]:
        arm_parts = [
            capsule("upper_arm." + side, (sign * 0.166, 0.002, 1.258), (sign * 0.232, -0.012, 0.985), 0.046, skin, 0.045),
            uv("elbow." + side, (sign * 0.232, -0.012, 0.985), (0.043, 0.044, 0.045), skin),
            capsule("forearm." + side, (sign * 0.232, -0.012, 0.985), (sign * 0.245, -0.036, 0.735), 0.034, skin, 0.036),
            uv("hand." + side, (sign * 0.246, -0.043, 0.672), (0.040, 0.031, 0.061), skin),
            capsule("thumb." + side, (sign * 0.218, -0.06, 0.684), (sign * 0.205, -0.07, 0.646), 0.014, skin, 0.014)
        ]
        for digit in range(4):
            x = sign * (0.224 + digit * 0.014)
            arm_parts.append(capsule("finger." + side + str(digit), (x, -0.05, 0.646), (x, -0.052, 0.612), 0.009, skin, 0.009))
        fuse(arm_parts, "Arm_Continuous_" + side, 0.0045, 4)

    # Neck, head, and face; front of face points to -Y.
    uv("Neck", (0, 0.004, 1.315), (0.050, 0.048, 0.085), skin, 36, 24)
    head = uv("Head_Face", (0, 0.0, 1.438), (0.112, 0.103, 0.145), skin, 64, 40)
    cheek_l = uv("Cheek.L", (-0.067, -0.080, 1.409), (0.018, 0.010, 0.013), skin, 32, 20)
    cheek_r = uv("Cheek.R", (0.067, -0.080, 1.409), (0.018, 0.010, 0.013), skin, 32, 20)
    chin = uv("Chin_Jaw", (0, -0.077, 1.356), (0.035, 0.014, 0.020), skin, 36, 24)
    ear_objects = []
    for sign, side in [(-1, "L"), (1, "R")]:
        ear_objects.append(uv("Ear." + side, (sign * 0.111, 0.0, 1.433), (0.017, 0.021, 0.030), skin, 28, 18))
        eye = uv("Eye_White." + side, (sign * 0.043, -0.092, 1.455), (0.016, 0.008, 0.0105), eye_white, 32, 20)
        uv("Iris." + side, (sign * 0.043, -0.099, 1.455), (0.0065, 0.0035, 0.0075), iris, 28, 18)
        uv("Pupil." + side, (sign * 0.043, -0.101, 1.455), (0.003, 0.0015, 0.0045), pupil, 20, 14)
        brow = capsule("Brow." + side, (sign * 0.064, -0.098, 1.481), (sign * 0.025, -0.101, 1.484), 0.006, hair, 0.005)
        if side == "L":
            shape_key(eye, "blink_left", lambda co, idx: Vector((co.x, co.y, co.z * 0.08)))
        else:
            shape_key(eye, "blink_right", lambda co, idx: Vector((co.x, co.y, co.z * 0.08)))
        shape_key(brow, "brow_raise", lambda co, idx: Vector((co.x, co.y, co.z + 0.009)))

    nose = uv("Nose", (0, -0.099, 1.433), (0.010, 0.014, 0.017), skin, 32, 20)
    head = fuse([head, cheek_l, cheek_r, chin, nose] + ear_objects, "Head_Face_Continuous", 0.0035, 2)
    mouth = uv("Mouth_Lips", (0, -0.099, 1.394), (0.034, 0.008, 0.006), lip, 36, 20)
    shape_key(mouth, "smile", lambda co, idx: Vector((co.x * 1.18, co.y, co.z + 0.11 * abs(co.x))))
    shape_key(mouth, "mouth_open", lambda co, idx: Vector((co.x, co.y - 0.001, co.z * 1.8)))
    shape_key(mouth, "jaw_open", lambda co, idx: Vector((co.x, co.y - 0.001, co.z * 1.5)))
    shape_key(mouth, "jaw_hinge", lambda co, idx: Vector((co.x, co.y - 0.002, co.z - 0.002)))
    shape_key(mouth, "lip_press", lambda co, idx: Vector((co.x, co.y, co.z * 0.25)))
    shape_key(mouth, "lip_fv", lambda co, idx: Vector((co.x * 0.72, co.y * 1.12, co.z)))
    shape_key(mouth, "lip_round", lambda co, idx: Vector((co.x * 0.62, co.y - 0.002, co.z)))
    tongue = uv("Tongue_Tip", (0, -0.105, 1.388), (0.015, 0.005, 0.004), lip, 24, 14)
    shape_key(tongue, "tongue_tip", lambda co, idx: Vector((co.x, co.y - 0.004, co.z + 0.003)))
    shape_key(head, "jaw_open", lambda co, idx: Vector((co.x, co.y - (0.002 if co.z < -0.045 and co.y < -0.025 else 0), co.z - (0.006 if co.z < -0.045 and co.y < -0.025 else 0))))
    shape_key(head, "jaw_hinge", lambda co, idx: Vector((co.x, co.y - (0.003 if co.z < -0.045 and co.y < -0.025 else 0), co.z - (0.004 if co.z < -0.045 and co.y < -0.025 else 0))))
    shape_key(head, "mouth_open", lambda co, idx: Vector((co.x, co.y - (0.002 if co.z < -0.035 and co.y < -0.025 else 0), co.z - (0.003 if co.z < -0.035 and co.y < -0.025 else 0))))
    shape_key(head, "cheek_raise", lambda co, idx: Vector((co.x, co.y, co.z + (0.004 if -0.045 < co.z < 0.0 and co.y < -0.03 else 0))))

    # Long natural black hair, rather than the helmet-like short cap of the first prototype.
    uv("Hair_Cap", (0, 0.025, 1.526), (0.120, 0.109, 0.066), hair, 48, 32)
    uv("Hair_Fringes", (0, -0.086, 1.502), (0.070, 0.020, 0.014), hair, 36, 20)
    uv("Hair_Back_Long", (0, 0.065, 1.315), (0.119, 0.080, 0.268), hair, 48, 32)
    for sign, side in [(-1, "L"), (1, "R")]:
        capsule("Hair_Front_Lock." + side, (sign * 0.092, -0.075, 1.478), (sign * 0.101, -0.054, 1.085), 0.018, hair, 0.021)
        capsule("Hair_Back_Lock." + side, (sign * 0.095, 0.072, 1.49), (sign * 0.118, 0.065, 1.075), 0.028, hair, 0.030)
        capsule("Hair_Tip." + side, (sign * 0.103, -0.009, 1.10), (sign * 0.098, -0.005, 1.055), 0.024, hair, 0.029)

    # Simple pocket/stitch details on shorts and tee, deliberately subtle at full-body view.
    for sign, side in [(-1, "L"), (1, "R")]:
        uv("Shorts_Pocket." + side, (sign * 0.09, -0.115, 0.912), (0.034, 0.003, 0.018), denim_light, 24, 16)
        uv("Tee_Hem_Stitch." + side, (sign * 0.09, -0.104, 1.003), (0.035, 0.002, 0.002), shirt, 20, 12)

    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("V314CandidateWorld")
    scene.world.color = (0.04, 0.045, 0.055)
    before = bounds(meshes)
    target = (0, 0, 0.80)
    dist = 3.5
    front = camera(scene, "FrontCamera", (0, -dist, 0.80), target, 1.82)
    render(scene, front, os.path.join(out, "lam-v314-front.png"))
    quarter = camera(scene, "ThreeQuarterCamera", (dist * 0.68, -dist * 0.75, 0.80), target, 1.82)
    render(scene, quarter, os.path.join(out, "lam-v314-three-quarter.png"))
    side = camera(scene, "SideCamera", (dist, 0, 0.80), target, 1.82)
    render(scene, side, os.path.join(out, "lam-v314-side.png"))

    glb = os.path.join(out, "lam-v314-coherent-avatar-candidate.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True)

    found = set()
    for obj in meshes:
        if obj.data.shape_keys:
            found.update(key.name for key in obj.data.shape_keys.key_blocks if key.name != "Basis")
    after_hash = None
    report = {
        "status": "EXPERIMENTAL_COHERENT_STATIC_CANDIDATE_NOT_APPROVED",
        "purpose": "Rebuild the current fragmented blockout as a connected, correctly sized, stylized adult female avatar candidate.",
        "blender_version": bpy.app.version_string,
        "mesh_count": len(meshes),
        "armature_count": sum(1 for obj in scene.objects if obj.type == "ARMATURE"),
        "materials": sorted({m.name for obj in meshes for m in obj.data.materials if m}),
        "morph_names_found": sorted(found),
        "missing_expected_morphs": sorted(set(EXPECTED_MORPHS) - found),
        "bounds_m": before,
        "render_files": ["lam-v314-front.png", "lam-v314-three-quarter.png", "lam-v314-side.png"],
        "candidate_glb": os.path.basename(glb),
        "candidate_bytes": os.path.getsize(glb),
        "warnings": [
            "Experimental procedural/stylized candidate, not photorealistic.",
            "This candidate has facial shape-key controls but no armature or skeletal animation.",
            "Review all three rendered views and browser playback before considering promotion.",
            "The current production/source GLB has not been modified."
        ]
    }
    with open(os.path.join(out, "lam-v314-candidate-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("V314_COHERENT_AVATAR_CANDIDATE=" + json.dumps(report, ensure_ascii=False))
    assert report["armature_count"] == 0
    assert report["mesh_count"] > 15
    assert report["missing_expected_morphs"] == [], report
    assert abs(before["size"][2] - 1.60) < 0.04, before
    assert os.path.getsize(glb) > 20000

if __name__ == "__main__":
    main()
