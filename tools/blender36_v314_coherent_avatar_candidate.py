import bpy, os, sys, json, hashlib, struct
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


def build_rest_pose_rig(meshes):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.armature_add(location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = "Lam_Humanoid_Root"
    rig.data.name = "Lam_Humanoid_Rig"
    bpy.ops.object.mode_set(mode="EDIT")
    for old in list(rig.data.edit_bones):
        rig.data.edit_bones.remove(old)

    bone_specs = {
        "Lam_Joint_Hips": ((0, 0, 0.76), (0, 0, 0.93), None),
        "Lam_Joint_Spine": ((0, 0, 0.93), (0, 0, 1.105), "Lam_Joint_Hips"),
        "Lam_Joint_Chest": ((0, 0, 1.105), (0, 0, 1.285), "Lam_Joint_Spine"),
        "Lam_Joint_Neck": ((0, 0, 1.285), (0, 0, 1.355), "Lam_Joint_Chest"),
        "Lam_Joint_Head": ((0, 0, 1.355), (0, 0, 1.565), "Lam_Joint_Neck"),
        "Lam_Joint_LeftShoulder": ((-0.145, 0, 1.278), (-0.232, -0.012, 0.985), "Lam_Joint_Chest"),
        "Lam_Joint_LeftElbow": ((-0.232, -0.012, 0.985), (-0.245, -0.036, 0.735), "Lam_Joint_LeftShoulder"),
        "Lam_Joint_LeftWrist": ((-0.245, -0.036, 0.735), (-0.246, -0.043, 0.65), "Lam_Joint_LeftElbow"),
        "Lam_Joint_RightShoulder": ((0.145, 0, 1.278), (0.232, -0.012, 0.985), "Lam_Joint_Chest"),
        "Lam_Joint_RightElbow": ((0.232, -0.012, 0.985), (0.245, -0.036, 0.735), "Lam_Joint_RightShoulder"),
        "Lam_Joint_RightWrist": ((0.245, -0.036, 0.735), (0.246, -0.043, 0.65), "Lam_Joint_RightElbow"),
        "Lam_Joint_LeftHip": ((-0.102, 0, 0.88), (-0.105, 0, 0.425), "Lam_Joint_Hips"),
        "Lam_Joint_LeftKnee": ((-0.105, 0, 0.425), (-0.108, 0, 0.13), "Lam_Joint_LeftHip"),
        "Lam_Joint_LeftAnkle": ((-0.108, 0, 0.13), (-0.108, 0, 0.045), "Lam_Joint_LeftKnee"),
        "Lam_Joint_RightHip": ((0.102, 0, 0.88), (0.105, 0, 0.425), "Lam_Joint_Hips"),
        "Lam_Joint_RightKnee": ((0.105, 0, 0.425), (0.108, 0, 0.13), "Lam_Joint_RightHip"),
        "Lam_Joint_RightAnkle": ((0.108, 0, 0.13), (0.108, 0, 0.045), "Lam_Joint_RightKnee")
    }
    edit_bones = {}
    for name, (head_pos, tail_pos, parent_name) in bone_specs.items():
        bone = rig.data.edit_bones.new(name)
        bone.head = head_pos
        bone.tail = tail_pos
        edit_bones[name] = bone
    for name, (_, _, parent_name) in bone_specs.items():
        if parent_name:
            bone = edit_bones[name]
            bone.parent = edit_bones[parent_name]
            if (bone.head - bone.parent.tail).length < 1e-5:
                bone.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    rig.display_type = "WIRE"

    all_bone_names = list(bone_specs)
    for obj in meshes:
        original_world = obj.matrix_world.copy()
        groups = {name: obj.vertex_groups.new(name=name) for name in all_bone_names}
        name = obj.name
        for index, vertex in enumerate(obj.data.vertices):
            world = original_world @ vertex.co
            x, z = float(world.x), float(world.z)
            weights = {}

            def mix(a, b, t):
                t = max(0.0, min(1.0, t))
                weights[a] = weights.get(a, 0.0) + (1.0 - t)
                weights[b] = weights.get(b, 0.0) + t

            if name == "Tee_Fitted_Continuous":
                if z < 1.02:
                    mix("Lam_Joint_Hips", "Lam_Joint_Spine", (z - 0.93) / 0.09)
                elif z < 1.19:
                    mix("Lam_Joint_Spine", "Lam_Joint_Chest", (z - 1.02) / 0.17)
                else:
                    weights["Lam_Joint_Chest"] = 1.0
            elif name == "Denim_Shorts_Continuous":
                side = "Lam_Joint_LeftHip" if x < 0 else "Lam_Joint_RightHip"
                if z > 0.965:
                    weights["Lam_Joint_Hips"] = 0.7
                    weights[side] = 0.3
                else:
                    weights["Lam_Joint_Hips"] = 0.35
                    weights[side] = 0.65
            elif name.startswith("Leg_Continuous_"):
                side = "Left" if name.endswith("_L") else "Right"
                hip, knee, ankle = (f"Lam_Joint_{side}Hip", f"Lam_Joint_{side}Knee", f"Lam_Joint_{side}Ankle")
                if z >= 0.62:
                    weights[hip] = 1.0
                elif z >= 0.34:
                    mix(hip, knee, (0.62 - z) / 0.28)
                else:
                    mix(knee, ankle, (0.34 - z) / 0.21)
            elif name.startswith("Arm_Continuous_"):
                side = "Left" if name.endswith("_L") else "Right"
                shoulder, elbow, wrist = (f"Lam_Joint_{side}Shoulder", f"Lam_Joint_{side}Elbow", f"Lam_Joint_{side}Wrist")
                if z >= 1.02:
                    weights[shoulder] = 1.0
                elif z >= 0.75:
                    mix(shoulder, elbow, (1.02 - z) / 0.27)
                elif z >= 0.66:
                    mix(elbow, wrist, (0.75 - z) / 0.09)
                else:
                    weights[wrist] = 1.0
            elif name.startswith(("Sneaker_", "Lace_")):
                side = "Left" if (".L" in name or "_L_" in name) else "Right"
                weights[f"Lam_Joint_{side}Ankle"] = 1.0
            elif name.startswith("Shorts_Pocket."):
                side = "Left" if name.endswith(".L") else "Right"
                weights[f"Lam_Joint_{side}Hip"] = 1.0
            elif name.startswith("Tee_Hem_Stitch."):
                weights["Lam_Joint_Spine"] = 1.0
            elif name.startswith(("Hair_", "Head_Face_", "Eye_", "Iris.", "Pupil.", "Brow.", "Mouth_", "Tongue_Tip", "Shorts_Silver_Button")):
                weights["Lam_Joint_Head" if not name.startswith("Shorts_Silver_Button") else "Lam_Joint_Hips"] = 1.0
            elif name == "Neck":
                weights["Lam_Joint_Neck"] = 1.0
            elif name == "Shorts_Waist_Belt":
                weights["Lam_Joint_Hips"] = 1.0
            else:
                weights["Lam_Joint_Chest" if z > 1.1 else "Lam_Joint_Hips"] = 1.0

            total = sum(weights.values())
            if total <= 0:
                weights = {"Lam_Joint_Hips": 1.0}
                total = 1.0
            for bone_name, weight in weights.items():
                if weight > 0:
                    groups[bone_name].add([index], weight / total, "REPLACE")

        obj.parent = rig
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
        obj.matrix_world = original_world
        modifier = obj.modifiers.new("Lam_RestPose_Skin", "ARMATURE")
        modifier.object = rig
        modifier.use_vertex_groups = True
        modifier.use_deform_preserve_volume = True

    bpy.context.view_layer.update()
    return rig


def create_idle_animation(rig):
    scene = bpy.context.scene
    action = bpy.data.actions.new("Lam_Idle_GentleSway")
    rig.animation_data_create()
    rig.animation_data.action = action
    scene.frame_start = 1
    scene.frame_end = 49
    scene.render.fps = 24

    chest = rig.pose.bones.get("Lam_Joint_Chest")
    head = rig.pose.bones.get("Lam_Joint_Head")
    if chest is None or head is None:
        raise RuntimeError("Required Chest/Head bones are missing for the idle clip.")

    chest.rotation_mode = "XYZ"
    head.rotation_mode = "XYZ"
    keys = [
        (1, 0.0, 0.0),
        (13, 0.018, 0.012),
        (25, 0.0, 0.0),
        (37, -0.018, -0.012),
        (49, 0.0, 0.0),
    ]
    for frame, chest_y, head_x in keys:
        scene.frame_set(frame)
        chest.rotation_euler = (0.0, chest_y, 0.0)
        chest.keyframe_insert(data_path="rotation_euler", frame=frame, group=chest.name)
        head.rotation_euler = (head_x, 0.0, 0.0)
        head.keyframe_insert(data_path="rotation_euler", frame=frame, group=head.name)
    scene.frame_set(1)
    return action

def evaluated_world_vertices(obj, scene, frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()

def measure_animation_deformation(meshes, scene):
    tee = next((obj for obj in meshes if obj.name == "Tee_Fitted_Continuous"), None)
    if tee is None:
        raise RuntimeError("Tee_Fitted_Continuous was not found to verify skeletal deformation.")
    at_rest = evaluated_world_vertices(tee, scene, 1)
    at_motion = evaluated_world_vertices(tee, scene, 13)
    if len(at_rest) != len(at_motion) or not at_rest:
        raise RuntimeError("Cannot compare evaluated torso vertices at the two animation frames.")
    return max((at_motion[i] - at_rest[i]).length for i in range(len(at_rest)))

def read_glb_json(glb_path):
    with open(glb_path, "rb") as f:
        data = f.read()
    if len(data) < 20:
        raise RuntimeError("Exported GLB is too short to contain the JSON chunk.")
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total_length != len(data):
        raise RuntimeError("Exported GLB header is invalid.")
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A or 20 + chunk_length > len(data):
        raise RuntimeError("Exported GLB does not start with a valid JSON chunk.")
    return json.loads(data[20:20 + chunk_length].decode("utf-8").rstrip("\\x00 \\t\\r\\n"))

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
        uv("tee_waist_volume", (0, 0, 1.055), (0.132, 0.092, 0.142), shirt),
        uv("tee_torso_volume", (0, 0, 1.185), (0.158, 0.100, 0.168), shirt),
        uv("tee_shoulders_volume", (0, 0, 1.285), (0.153, 0.092, 0.082), shirt),
        capsule("tee_sleeve.L", (-0.115, -0.002, 1.286), (-0.194, -0.008, 1.232), 0.041, shirt, 0.052),
        capsule("tee_sleeve.R", (0.115, -0.002, 1.286), (0.194, -0.008, 1.232), 0.041, shirt, 0.052)
    ]
    tee = fuse(trunk_parts, "Tee_Fitted_Continuous", 0.007, 5)

    # High-waist denim shorts with fuller hip silhouette and short hems.
    shorts_parts = [
        uv("shorts_hip_shell", (0, 0.002, 0.914), (0.188, 0.112, 0.113), denim),
        capsule("shorts_leg.L", (-0.091, 0.0, 0.89), (-0.098, 0.0, 0.748), 0.079, denim, 0.092),
        capsule("shorts_leg.R", (0.091, 0.0, 0.89), (0.098, 0.0, 0.748), 0.079, denim, 0.092)
    ]
    shorts = fuse(shorts_parts, "Denim_Shorts_Continuous", 0.006, 4)

    # Keep the shorts waist clean and fitted; no floating belt/button geometry.

    # Adult legs: continuous fused thigh-to-calf surfaces, one object per side.
    leg_meshes = []
    for sign, side in [(-1, "L"), (1, "R")]:
        leg_parts = [
            capsule("thigh." + side, (sign * 0.098, 0.0, 0.765), (sign * 0.103, 0.0, 0.425), 0.084, skin, 0.080),
            uv("knee." + side, (sign * 0.103, 0.0, 0.425), (0.056, 0.058, 0.056), skin),
            capsule("calf." + side, (sign * 0.103, 0.0, 0.43), (sign * 0.108, 0.0, 0.13), 0.056, skin, 0.058)
        ]
        leg_meshes.append(fuse(leg_parts, "Leg_Continuous_" + side, 0.0045, 8))

    # Shoes: soles, uppers, toe caps, and understated gray panels.
    for sign, side in [(-1, "L"), (1, "R")]:
        x = sign * 0.11
        uv("Sneaker_Sole." + side, (x, -0.038, 0.020), (0.060, 0.112, 0.020), sole, 36, 20)
        upper = uv("Sneaker_Upper." + side, (x, -0.045, 0.064), (0.054, 0.100, 0.040), sneaker, 36, 24)
        toe = uv("Sneaker_Toe." + side, (x, -0.105, 0.064), (0.046, 0.040, 0.026), sneaker, 32, 18)
        fuse([upper, toe], "Sneaker_Upper_Continuous." + side, 0.004, 3)
        uv("Sneaker_Accent." + side, (x + sign * 0.048, -0.015, 0.075), (0.004, 0.029, 0.009), sneaker_accent, 24, 16)
        for i in range(3):
            uv("Lace_" + side + "_" + str(i), (x, -0.067 + i * 0.023, 0.108), (0.007, 0.003, 0.0025), eye_white, 12, 8)

    # Arms hang naturally at the sides and overlap sleeves/torso at the shoulder.
    for sign, side in [(-1, "L"), (1, "R")]:
        arm_parts = [
            capsule("upper_arm." + side, (sign * 0.166, 0.002, 1.258), (sign * 0.232, -0.012, 0.985), 0.041, skin, 0.041),
            uv("elbow." + side, (sign * 0.232, -0.012, 0.985), (0.036, 0.037, 0.038), skin),
            capsule("forearm." + side, (sign * 0.232, -0.012, 0.985), (sign * 0.245, -0.036, 0.735), 0.032, skin, 0.033),
            uv("hand." + side, (sign * 0.246, -0.043, 0.672), (0.040, 0.031, 0.061), skin),
            capsule("thumb." + side, (sign * 0.218, -0.06, 0.684), (sign * 0.205, -0.07, 0.646), 0.014, skin, 0.014)
        ]
        for digit in range(4):
            x = sign * (0.224 + digit * 0.014)
            arm_parts.append(capsule("finger." + side + str(digit), (x, -0.05, 0.646), (x, -0.052, 0.612), 0.009, skin, 0.009))
        fuse(arm_parts, "Arm_Continuous_" + side, 0.004, 7)

    # Neck, head, and face; front of face points to -Y.
    uv("Neck", (0, 0.004, 1.315), (0.050, 0.048, 0.085), skin, 36, 24)
    head = uv("Head_Face", (0, 0.0, 1.438), (0.116, 0.097, 0.151), skin, 64, 40)
    cheek_l = uv("Cheek.L", (-0.067, -0.079, 1.409), (0.013, 0.007, 0.010), skin, 32, 20)
    cheek_r = uv("Cheek.R", (0.067, -0.079, 1.409), (0.013, 0.007, 0.010), skin, 32, 20)
    chin = uv("Chin_Jaw", (0, -0.075, 1.356), (0.030, 0.010, 0.016), skin, 36, 24)
    ear_objects = []
    for sign, side in [(-1, "L"), (1, "R")]:
        ear_objects.append(uv("Ear." + side, (sign * 0.113, 0.0, 1.433), (0.014, 0.018, 0.025), skin, 28, 18))
        eye = uv("Eye_White." + side, (sign * 0.043, -0.096, 1.455), (0.018, 0.008, 0.011), eye_white, 32, 20)
        uv("Iris." + side, (sign * 0.043, -0.103, 1.455), (0.007, 0.0035, 0.008), iris, 28, 18)
        uv("Pupil." + side, (sign * 0.043, -0.105, 1.455), (0.0035, 0.0015, 0.0045), pupil, 20, 14)
        brow = capsule("Brow." + side, (sign * 0.064, -0.096, 1.481), (sign * 0.025, -0.098, 1.484), 0.0035, hair, 0.003)
        if side == "L":
            shape_key(eye, "blink_left", lambda co, idx: Vector((co.x, co.y, co.z * 0.08)))
        else:
            shape_key(eye, "blink_right", lambda co, idx: Vector((co.x, co.y, co.z * 0.08)))
        shape_key(brow, "brow_raise", lambda co, idx: Vector((co.x, co.y, co.z + 0.009)))

    nose = uv("Nose", (0, -0.092, 1.433), (0.008, 0.010, 0.013), skin, 32, 20)
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
    uv("Hair_Cap", (0, 0.025, 1.515), (0.120, 0.107, 0.083), hair, 48, 32)
    capsule("Hair_Fringes.Center", (0, -0.084, 1.548), (0, -0.101, 1.497), 0.011, hair, 0.008)
    capsule("Hair_Fringes.Left", (-0.037, -0.078, 1.543), (-0.050, -0.098, 1.497), 0.010, hair, 0.008)
    capsule("Hair_Fringes.Right", (0.037, -0.078, 1.543), (0.050, -0.098, 1.497), 0.010, hair, 0.008)
    uv("Hair_Back_Long", (0, 0.065, 1.315), (0.119, 0.080, 0.268), hair, 48, 32)
    for sign, side in [(-1, "L"), (1, "R")]:
        capsule("Hair_Front_Lock." + side, (sign * 0.092, -0.075, 1.478), (sign * 0.101, -0.054, 1.085), 0.015, hair, 0.019)
        capsule("Hair_Back_Lock." + side, (sign * 0.095, 0.072, 1.49), (sign * 0.118, 0.065, 1.075), 0.028, hair, 0.030)
        capsule("Hair_Tip." + side, (sign * 0.103, -0.009, 1.10), (sign * 0.098, -0.005, 1.055), 0.024, hair, 0.029)

    # Simple pocket/stitch details on shorts and tee, deliberately subtle at full-body view.
    for sign, side in [(-1, "L"), (1, "R")]:
        pass # Flat pocket patches are deferred to keep the experimental silhouette clean.
        pass # Hem stays visually clean in the low-resolution prototype.

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

    rig = build_rest_pose_rig(meshes)
    action = create_idle_animation(rig)
    max_tee_deformation = measure_animation_deformation(meshes, scene)
    if max_tee_deformation <= 0.0001:
        raise RuntimeError("Idle animation is present but evaluated torso deformation is below tolerance.")
    scene.frame_set(1)
    bpy.context.view_layer.update()
    rig_front = camera(scene, "RiggedFrontCamera", (0, -dist, 0.80), target, 1.82)
    render(scene, rig_front, os.path.join(out, "lam-v314-rigged-front.png"))
    rig_quarter = camera(scene, "RiggedThreeQuarterCamera", (dist * 0.68, -dist * 0.75, 0.80), target, 1.82)
    render(scene, rig_quarter, os.path.join(out, "lam-v314-rigged-three-quarter.png"))

    glb = os.path.join(out, "lam-v314-coherent-avatar-candidate.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True)
    glb_doc = read_glb_json(glb)
    glb_animation_names = [item.get("name", "") for item in glb_doc.get("animations", [])]
    glb_skin_count = len(glb_doc.get("skins", []))
    if "Lam_Idle_GentleSway" not in glb_animation_names:
        raise RuntimeError("The exported GLB does not contain the Lam_Idle_GentleSway animation clip.")
    if glb_skin_count != 1:
        raise RuntimeError("Expected one exported glTF skin/armature; got " + str(glb_skin_count))

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
        "armature_bone_count": len(rig.data.bones),
        "animation_clip_names": [item.name for item in bpy.data.actions],
        "animation_clip_count": len(bpy.data.actions),
        "max_tee_deformation_m_frame_1_to_13": round(max_tee_deformation, 8),
        "glb_animation_names": glb_animation_names,
        "glb_skin_count": glb_skin_count,
        "materials": sorted({m.name for obj in meshes for m in obj.data.materials if m}),
        "morph_names_found": sorted(found),
        "missing_expected_morphs": sorted(set(EXPECTED_MORPHS) - found),
        "bounds_m": before,
        "render_files": ["lam-v314-front.png", "lam-v314-three-quarter.png", "lam-v314-side.png", "lam-v314-rigged-front.png", "lam-v314-rigged-three-quarter.png"],
        "candidate_glb": os.path.basename(glb),
        "candidate_bytes": os.path.getsize(glb),
        "warnings": [
            "Experimental procedural/stylized candidate, not photorealistic.",
            "A basic 17-bone rest-pose rig is included; animation clips have not yet been created or approved.",
            "Review all three rendered views and browser playback before considering promotion.",
            "The current production/source GLB has not been modified."
        ]
    }
    with open(os.path.join(out, "lam-v314-candidate-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("V314_COHERENT_AVATAR_CANDIDATE=" + json.dumps(report, ensure_ascii=False))
    assert report["armature_count"] == 1
    assert report["armature_bone_count"] == 17
    assert report["animation_clip_count"] == 1, report
    assert "Lam_Idle_GentleSway" in report["glb_animation_names"], report
    assert report["glb_skin_count"] == 1, report
    assert report["max_tee_deformation_m_frame_1_to_13"] > 0.0001, report
    assert report["mesh_count"] > 15
    assert report["missing_expected_morphs"] == [], report
    assert abs(before["size"][2] - 1.60) < 0.04, before
    assert os.path.getsize(glb) > 20000

if __name__ == "__main__":
    main()
