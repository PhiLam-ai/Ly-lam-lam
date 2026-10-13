import bpy
import json
import math
import os
import sys
import traceback
from collections import deque
from mathutils import Vector

def output_dir_from_args():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.getcwd()
    for i, arg in enumerate(args[:-1]):
        if arg == "--output-dir":
            out = args[i + 1]
    os.makedirs(out, exist_ok=True)
    return out

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

def make_material(name, color, roughness=0.72):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def add_ellipsoid(name, location, scale, material, rotation_y=0.0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler[1] = rotation_y
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj

def connected_component_count(mesh):
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen = set()
    components = 0
    for start in range(len(mesh.vertices)):
        if start in seen:
            continue
        components += 1
        queue = deque([start])
        seen.add(start)
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
    return components

def main():
    out = output_dir_from_args()
    clear_scene()

    skin = make_material("Lam_BaseBody_Skin", (0.62, 0.38, 0.29))
    cloth = make_material("Lam_BaseBody_Blockout", (0.16, 0.22, 0.30))
    floor_mat = make_material("Preview_Floor", (0.12, 0.14, 0.18))

    parts = []
    # Proportional blockout for a 1.60 m adult female character.
    # These overlapping ellipsoids are fused by voxel remeshing below.
    parts.append(add_ellipsoid("Pelvis", (0.0, 0.008, 0.79), (0.225, 0.145, 0.16), skin))
    parts.append(add_ellipsoid("Abdomen", (0.0, 0.0, 0.985), (0.132, 0.112, 0.195), skin))
    parts.append(add_ellipsoid("Chest", (0.0, 0.0, 1.17), (0.184, 0.13, 0.19), skin))
    parts.append(add_ellipsoid("Neck", (0.0, 0.0, 1.375), (0.055, 0.058, 0.082), skin))
    parts.append(add_ellipsoid("Head_Blockout", (0.0, -0.006, 1.485), (0.098, 0.094, 0.125), skin))

    for side in (-1, 1):
        x = side * 0.105
        parts.append(add_ellipsoid("Thigh", (side * 0.112, 0.006, 0.545), (0.102, 0.101, 0.285), skin, rotation_y=side * -0.025))
        parts.append(add_ellipsoid("Calf", (side * 0.112, 0.006, 0.255), (0.064, 0.069, 0.19), skin, rotation_y=side * 0.02))
        parts.append(add_ellipsoid("Foot", (side * 0.112, -0.088, 0.085), (0.064, 0.15, 0.055), skin))
        parts.append(add_ellipsoid("Shoulder", (side * 0.184, 0.0, 1.205), (0.075, 0.082, 0.09), skin))
        parts.append(add_ellipsoid("UpperArm", (side * 0.247, 0.0, 1.055), (0.059, 0.061, 0.17), skin, rotation_y=side * 0.28))
        parts.append(add_ellipsoid("Forearm", (side * 0.295, -0.002, 0.895), (0.047, 0.05, 0.14), skin, rotation_y=side * 0.18))
        parts.append(add_ellipsoid("Hand_Blockout", (side * 0.315, -0.018, 0.765), (0.044, 0.034, 0.055), skin))

    # Join all overlapping body pieces, then voxel-remesh into one continuous surface.
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = "LLL_STEP1_Unified_BaseBody"
    body.data.name = "LLL_STEP1_Unified_BaseBody_Mesh"
    body.data.remesh_mode = "VOXEL"
    body.data.remesh_voxel_size = 0.009
    bpy.ops.object.voxel_remesh()

    # Reduce the visible seams between the primitive blockout parts.
    # Apply modifiers so exported GLB geometry matches the saved Blender mesh.
    smooth = body.modifiers.new("Step1_Surface_Blend", "SMOOTH")
    smooth.factor = 0.85
    smooth.iterations = 6
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=smooth.name)

    subdivision = body.modifiers.new("Step1_Surface_Refine", "SUBSURF")
    subdivision.subdivision_type = "CATMULL_CLARK"
    subdivision.levels = 1
    subdivision.render_levels = 1
    bpy.ops.object.modifier_apply(modifier=subdivision.name)

    for polygon in body.data.polygons:
        polygon.use_smooth = True
    body.data.materials.clear()
    body.data.materials.append(skin)
    body["stage"] = "STEP1_BASE_BODY_BLOCKOUT"
    body["target_height_m"] = 1.60
    body["note"] = "Base body with early face, hair and clothing blockout; final sculpting and rigging are later steps."

    # STEP 2 visual blockout: add hair silhouette, facial landmarks and simple clothing layers.
    # These remain separate objects so later sculpting and rigging can replace them cleanly.
    hair_mat = make_material("Lam_Hair_Black", (0.035, 0.022, 0.018), 0.42)
    eye_mat = make_material("Lam_Eyes_DarkBrown", (0.075, 0.032, 0.018), 0.3)
    white_mat = make_material("Lam_Eye_White", (0.82, 0.74, 0.65), 0.38)
    lip_mat = make_material("Lam_Lips_Rose", (0.42, 0.12, 0.12), 0.48)
    top_mat = make_material("Lam_Top_DeepTeal", (0.035, 0.24, 0.25), 0.62)
    skirt_mat = make_material("Lam_Skirt_DarkTeal", (0.025, 0.12, 0.15), 0.68)

    avatar_details = []
    # Hair cap, rear volume and long side locks; silhouette only, not strand-level hair.
    avatar_details.append(add_ellipsoid("Hair_Cap_Blockout", (0.0, 0.003, 1.565), (0.105, 0.101, 0.067), hair_mat))
    avatar_details.append(add_ellipsoid("Hair_Back_Volume", (0.0, 0.055, 1.445), (0.096, 0.055, 0.155), hair_mat))
    for side in (-1, 1):
        avatar_details.append(add_ellipsoid("Hair_Side_Lock", (side * 0.086, 0.005, 1.435), (0.032, 0.046, 0.155), hair_mat, rotation_y=side * -0.08))
        # Eye whites and irises face the negative-Y direction.
        avatar_details.append(add_ellipsoid("Eye_White", (side * 0.036, -0.089, 1.505), (0.021, 0.009, 0.012), white_mat))
        avatar_details.append(add_ellipsoid("Eye_Iris", (side * 0.036, -0.098, 1.505), (0.009, 0.005, 0.009), eye_mat))
        avatar_details.append(add_ellipsoid("Brow_Blockout", (side * 0.036, -0.087, 1.526), (0.024, 0.008, 0.006), hair_mat, rotation_y=side * 0.08))
        avatar_details.append(add_ellipsoid("Ear_Blockout", (side * 0.099, -0.002, 1.475), (0.014, 0.023, 0.027), skin))
    avatar_details.append(add_ellipsoid("Nose_Blockout", (0.0, -0.099, 1.485), (0.012, 0.018, 0.027), skin))
    avatar_details.append(add_ellipsoid("Mouth_Blockout", (0.0, -0.091, 1.455), (0.022, 0.007, 0.006), lip_mat))
    # Tunic-like top overlaps the waist to remove the exposed gap in this early blockout.
    # These smooth shells are temporary; tailored garment meshes will replace them later.
    avatar_details.append(add_ellipsoid("Top_Blockout", (0.0, 0.006, 1.075), (0.205, 0.158, 0.315), top_mat))
    avatar_details.append(add_ellipsoid("Skirt_Blockout", (0.0, 0.012, 0.785), (0.238, 0.158, 0.205), skirt_mat))
    # Simple necklace cue matching Lam’s distinctive accessory reference.
    bpy.ops.mesh.primitive_torus_add(major_radius=0.047, minor_radius=0.0035, major_segments=32, minor_segments=8, location=(0.0, -0.048, 1.355))
    necklace = bpy.context.object
    necklace.name = "Lam_Necklace_Blockout"
    necklace.data.materials.append(make_material("Lam_Necklace_WarmGold", (0.68, 0.43, 0.16), 0.35))
    for polygon in necklace.data.polygons:
        polygon.use_smooth = True
    avatar_details.append(necklace)

    # Render setup: front three-quarter orthographic preview.
    bpy.ops.mesh.primitive_plane_add(size=5.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.object
    floor.name = "Preview_Floor"
    floor.data.materials.append(floor_mat)

    bpy.ops.object.camera_add(location=(2.5, -4.8, 1.05))
    camera = bpy.context.object
    camera.name = "Step1_Preview_Camera"
    direction = Vector((0.0, 0.0, 0.80)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.95
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    render_path = os.path.join(out, "lam-step1-body-preview.png")
    scene.render.filepath = render_path

    bpy.ops.render.render(write_still=True)

    # Export body plus visual-detail objects; exclude camera and preview floor.
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    for detail in avatar_details:
        detail.select_set(True)
    bpy.context.view_layer.objects.active = body
    glb_path = os.path.join(out, "lam-step1-base-body.glb")
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", use_selection=True)

    mesh = body.data
    mesh.calc_loop_triangles()
    z_values = [body.matrix_world @ vertex.co for vertex in mesh.vertices]
    z_min = min(v.z for v in z_values) if z_values else 0.0
    z_max = max(v.z for v in z_values) if z_values else 0.0
    components = connected_component_count(mesh)
    render_ok = os.path.isfile(render_path) and os.path.getsize(render_path) > 1000
    glb_ok = os.path.isfile(glb_path) and os.path.getsize(glb_path) > 10000
    geometry_ok = len(mesh.vertices) > 1000 and len(mesh.polygons) > 1000 and components == 1
    height_ok = z_min >= -0.02 and 1.45 <= (z_max - z_min) <= 1.75

    report = {
        "stage": "STEP1_BASE_BODY",
        "status": "PASS" if render_ok and glb_ok and geometry_ok and height_ok else "FAIL",
        "blender_version": bpy.app.version_string,
        "body_object": body.name,
        "body_mesh_vertices": len(mesh.vertices),
        "body_mesh_faces": len(mesh.polygons),
        "body_mesh_edges": len(mesh.edges),
        "body_connected_components": components,
        "height_m": round(z_max - z_min, 4),
        "z_min_m": round(z_min, 4),
        "z_max_m": round(z_max, 4),
        "render_png": os.path.basename(render_path),
        "render_bytes": os.path.getsize(render_path) if render_ok else 0,
        "glb": os.path.basename(glb_path),
        "glb_bytes": os.path.getsize(glb_path) if glb_ok else 0,
        "checks": {
            "render_created": render_ok,
            "glb_created": glb_ok,
            "single_unified_mesh": geometry_ok,
            "target_height_range": height_ok
        },
        "facial_morphs": morph_report,
        "facial_morphs_passed": sum(1 for item in morph_report.values() if item["status"] == "PASS"),
        "facial_morphs_total": len(morph_report),
        "scope_note": "Early visual avatar blockout with an initial geometric facial-shape-key pass. These morphs are functional prototypes; production facial sculpt, body rigging and animation remain separate work."
    }
    with open(os.path.join(out, "lam-step1-body-report.json"), "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2)
    print("LAM_STEP1_BODY_REPORT=" + json.dumps(report, ensure_ascii=False))
    if report["status"] != "PASS":
        raise RuntimeError("Step 1 base-body validation failed; inspect lam-step1-body-report.json.")

    # Save a Blender project artifact for inspection and later stages.
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "lam-step1-base-body.blend"))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
