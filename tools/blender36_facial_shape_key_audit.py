import bpy, json, os, sys

def main():
    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    src = "lam-default.glb"
    out = "artifacts/facial-shape-key-audit.json"
    for i, arg in enumerate(args[:-1]):
        if arg == "--input": src = args[i+1]
        elif arg == "--output": out = args[i+1]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
    results = []
    for obj in (o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.shape_keys):
        keys = obj.data.shape_keys.key_blocks
        if len(keys) < 2: continue
        basis = keys[0]
        for key in list(keys)[1:]:
            moved = 0
            maximum = 0.0
            for a, b in zip(basis.data, key.data):
                delta = (b.co - a.co).length
                maximum = max(maximum, delta)
                if delta > 1e-6: moved += 1
            results.append({"mesh": obj.name, "key": key.name, "vertex_count": len(basis.data),
                            "vertices_changed": moved, "max_local_delta": round(maximum, 8),
                            "status": "HAS_GEOMETRIC_EFFECT" if moved else "NO_GEOMETRIC_EFFECT"})
    report = {"status":"RECORDED", "purpose":"Static shape-key geometry audit only; does not prove semantic correctness or good facial animation.",
              "mesh_count_with_shape_keys":len(set(x["mesh"] for x in results)), "key_results":results,
              "approval":"NOT_APPROVED_VISUAL_REVIEW_REQUIRED"}
    with open(os.path.abspath(out), "w", encoding="utf-8") as f: json.dump(report, f, ensure_ascii=False, indent=2)
    print("FACIAL_SHAPE_KEY_AUDIT=" + json.dumps(report, ensure_ascii=False))
if __name__ == "__main__": main()
