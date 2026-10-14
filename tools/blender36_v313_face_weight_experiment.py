import bpy, os, sys, json, hashlib
from mathutils import Vector

TARGETS = {"left_eye", "right_eye", "left_brow", "right_brow", "mouth"}
HEAD_BONE = "Lam_Joint_Head"

def main():
    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    source = os.path.abspath("lam-default.glb")
    out_dir = os.path.abspath("artifacts/v313-face-weight-experiment")
    for i, arg in enumerate(args[:-1]):
        if arg == "--input": source = os.path.abspath(args[i+1])
        elif arg == "--output-dir": out_dir = os.path.abspath(args[i+1])
    os.makedirs(out_dir, exist_ok=True)
    source_hash = hashlib.sha256(open(source, "rb").read()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if not armatures: raise RuntimeError("No armature found")
    arm = armatures[0]
    if HEAD_BONE not in arm.data.bones: raise RuntimeError("Expected head bone missing: " + HEAD_BONE)
    mesh_rows = []
    found = set()
    for obj in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        name = obj.name.lower()
        key = next((t for t in TARGETS if name == t or name.endswith("_" + t)), None)
        if key is None: continue
        found.add(key)
        # Isolated hypothesis only: assign each facial mesh's vertices fully to head bone.
        vg = obj.vertex_groups.get(HEAD_BONE) or obj.vertex_groups.new(name=HEAD_BONE)
        indices = [v.index for v in obj.data.vertices]
        if indices: vg.add(indices, 1.0, "REPLACE")
        for group in list(obj.vertex_groups):
            if group.name == HEAD_BONE: continue
            try: obj.vertex_groups.remove(group)
            except RuntimeError: pass
        mesh_rows.append({"mesh": obj.name, "vertices": len(indices), "weight_hypothesis": "100% Lam_Joint_Head"})
    missing = sorted(TARGETS - found)
    if missing: raise RuntimeError("Expected facial meshes not found: " + ", ".join(missing))
    # Render a diagnostic front view with a fixed camera and lights.
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768; scene.render.resolution_y = 768; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"; scene.render.film_transparent = False
    if scene.world is None: scene.world = bpy.data.worlds.new("V313_FaceWeight_World")
    scene.world.color = (0.06, 0.06, 0.06)
    cam_data = bpy.data.cameras.new("V313_FaceWeight_Camera")
    cam = bpy.data.objects.new("V313_FaceWeight_Camera", cam_data); scene.collection.objects.link(cam)
    cam.location = (0, -15, 1.75); target = Vector((0, 0, 1.75))
    cam.rotation_euler = (target - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 9.8; scene.camera = cam
    for name, loc, energy, size in [
        ("Key", (-4,-6,7), 850, 5), ("Fill", (4,-4,3), 450, 4)]:
        data = bpy.data.lights.new("V313_FaceWeight_"+name, "AREA")
        light = bpy.data.objects.new("V313_FaceWeight_"+name, data); scene.collection.objects.link(light)
        light.location = loc; data.energy = energy; data.size = size
    image_path = os.path.join(out_dir, "face-weight-candidate-front.png")
    scene.render.filepath = image_path
    bpy.ops.render.render(write_still=True)
    out_glb = os.path.join(out_dir, "lam-face-weight-experiment.glb")
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", export_morph=True, export_skins=True, export_animations=False)
    morphs = sorted(set(k.name for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys for k in o.data.shape_keys.key_blocks if k.name != "Basis"))
    digest = hashlib.sha256(open(out_glb, "rb").read()).hexdigest()
    source_unchanged = hashlib.sha256(open(source, "rb").read()).hexdigest() == source_hash
    report = {"status":"EXPERIMENT_ONLY_NOT_APPROVED", "source_sha256":source_hash, "source_unchanged":source_unchanged,
      "candidate_sha256":digest, "candidate_bytes":os.path.getsize(out_glb), "targets":mesh_rows, "missing_targets":missing,
      "morph_names_after_export":morphs, "morph_count":len(morphs),
      "warning":"This is a diagnostic candidate only. It tests facial weights, not whole-body geometry or production suitability."}
    with open(os.path.join(out_dir,"face-weight-experiment-report.json"),"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print("V313_FACE_WEIGHT_EXPERIMENT=NOT_APPROVED")
    print(json.dumps({"source_unchanged":source_unchanged,"target_count":len(mesh_rows),"morph_count":len(morphs),"candidate_sha256":digest},ensure_ascii=False))
    if not source_unchanged: raise RuntimeError("Source GLB unexpectedly changed")
    if len(morphs) < 12: raise RuntimeError("Candidate lost expected facial morphs")
if __name__ == "__main__": main()
