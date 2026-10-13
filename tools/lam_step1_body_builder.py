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
    parts.append(add_ellipsoid("Pelvis", (0.0, 0.0, 0.79), (0.205, 0.135, 0.155), skin))
    parts.append(add_ellipsoid("Abdomen", (0.0, 0.0, 0.98), (0.145, 0.115, 0.205), skin))
    parts.append(add_ellipsoid("Chest", (0.0, 0.0, 1.17), (0.205, 0.135, 0.205), skin))
    parts.append(add_ellipsoid("Neck", (0.0, 0.0, 1.375), (0.065, 0.065, 0.085), skin))
    parts.append(add_ellipsoid("Head_Blockout", (0.0, 0.0, 1.485), (0.105, 0.095, 0.125), skin))

    for side in (-1, 1):
        x = side * 0.105
        parts.append(add_ellipsoid("Thigh", (x, 0.0, 0.545), (0.096, 0.096, 0.285), skin, rotation_y=side * -0.025))
        parts.append(add_ellipsoid("Calf", (x, 0.0, 0.255), (0.068, 0.073, 0.195), skin, rotation_y=side * 0.02))
        parts.append(add_ellipsoid("Foot", (x, -0.085, 0.085), (0.071, 0.155, 0.065), skin))
        parts.append(add_ellipsoid("Shoulder", (side * 0.205, 0.0, 1.205), (0.095, 0.092, 0.105), skin))
        parts.append(add_ellipsoid("UpperArm", (side * 0.275, 0.0, 1.055), (0.071, 0.071, 0.175), skin, rotation_y=side * 0.32))
        parts.append(add_ellipsoid("Forearm", (side * 0.335, -0.002, 0.895), (0.057, 0.059, 0.145), skin, rotation_y=side * 0.20))
        parts.append(add_ellipsoid("Hand_Blockout", (side * 0.365, -0.012, 0.765), (0.052, 0.043, 0.066), skin))

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
    body["note"] = "Base body geometry only; facial features, hair, clothing and rigging are later steps."

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

    # Export the unified body only; exclude camera and preview floor.
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
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
        "body_mesh_faces": len(mesh.polygons),\n        "body_mesh_edges": len(mesh.edges),
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
        "scope_note": "This is a base-body blockout for Step 1, not the finished Lam avatar. Face details, hair, clothes, rigging and animation are not included."
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
