import bpy, json, os, hashlib
from mathutils import Vector

def bounds(coords):
    if not coords: return None
    mins=[min(p[i] for p in coords) for i in range(3)]
    maxs=[max(p[i] for p in coords) for i in range(3)]
    return {"min":[round(float(x),6) for x in mins],"max":[round(float(x),6) for x in maxs],
            "size":[round(float(maxs[i]-mins[i]),6) for i in range(3)]}

def main():
    source=os.path.abspath("lam-default.glb")
    out_dir=os.path.abspath("artifacts/v313-transform-bind-audit")
    import sys
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    for i,arg in enumerate(args[:-1]):
        if arg=="--input": source=os.path.abspath(args[i+1])
        elif arg=="--output-dir": out_dir=os.path.abspath(args[i+1])
    os.makedirs(out_dir,exist_ok=True)
    h=hashlib.sha256(open(source,"rb").read()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    armatures=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    meshes=[]
    for obj in (o for o in bpy.context.scene.objects if o.type=="MESH"):
        local=[v.co.copy() for v in obj.data.vertices]
        world=[obj.matrix_world@v.co for v in obj.data.vertices]
        mods=[]
        for m in obj.modifiers:
            if m.type=="ARMATURE":
                mods.append({"name":m.name,"object":m.object.name if m.object else None,
                             "use_vertex_groups":bool(m.use_vertex_groups),"use_bone_envelopes":bool(m.use_bone_envelopes),
                             "use_deform_preserve_volume":bool(m.use_deform_preserve_volume),
                             "show_viewport":bool(m.show_viewport),"show_render":bool(m.show_render)})
        meshes.append({"name":obj.name,"parent":obj.parent.name if obj.parent else None,
          "parent_type":obj.parent_type,"parent_bone":obj.parent_bone,
          "local_bounds":bounds(local),"world_bounds":bounds(world),
          "location":[round(float(x),6) for x in obj.location],
          "rotation_euler":[round(float(x),6) for x in obj.rotation_euler],
          "scale":[round(float(x),6) for x in obj.scale],
          "matrix_world":[[round(float(v),6) for v in row] for row in obj.matrix_world],
          "matrix_world_determinant":round(float(obj.matrix_world.to_3x3().determinant()),8),
          "vertex_count":len(obj.data.vertices),"shape_keys":list(obj.data.shape_keys.key_blocks.keys()) if obj.data.shape_keys else [],
          "armature_modifiers":mods})
    report={"status":"READ_ONLY_DIAGNOSTIC_NO_MODEL_CHANGES","source":os.path.basename(source),
      "source_sha256":h,"armatures":[{"name":a.name,"location":[round(float(x),6) for x in a.location],
       "rotation_euler":[round(float(x),6) for x in a.rotation_euler],"scale":[round(float(x),6) for x in a.scale],
       "matrix_world":[[round(float(v),6) for v in row] for row in a.matrix_world],
       "bone_count":len(a.data.bones),
       "bones":[{"name":b.name,"parent":b.parent.name if b.parent else None,
         "head_local":[round(float(x),6) for x in b.head_local],
         "tail_local":[round(float(x),6) for x in b.tail_local],
         "use_deform":bool(b.use_deform)} for b in a.data.bones]} for a in armatures],
      "mesh_count":len(meshes),"meshes":meshes,
      "method":"Compare object transforms, local/world bounds, armature modifier references and bone rest positions. Diagnostic only; no transforms or weights changed."}
    path=os.path.join(out_dir,"v313-transform-bind-audit.json")
    with open(path,"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print("V313_TRANSFORM_BIND_AUDIT=DIAGNOSTIC_ONLY")
    print(json.dumps({"source_sha256":h,"mesh_count":len(meshes),"armature_count":len(armatures),
      "non_identity_mesh_transforms":[m["name"] for m in meshes if any(abs(m["location"][i])>1e-5 or abs(m["rotation_euler"][i])>1e-5 or abs(m["scale"][i]-1)>1e-5 for i in range(3))],
      "mesh_count_with_shape_keys":sum(bool(m["shape_keys"]) for m in meshes),
      "armature_modifier_targets":sorted(set(mod.get("object") for m in meshes for mod in m["armature_modifiers"]))},ensure_ascii=False))
if __name__=="__main__": main()
