import bpy, json, os, sys, math
from mathutils import Vector

def main():
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    source=os.path.abspath("lam-default.glb")
    out_dir=os.path.abspath("artifacts/v313-rest-pose-comparison")
    for i,arg in enumerate(args[:-1]):
        if arg=="--input": source=os.path.abspath(args[i+1])
        elif arg=="--output-dir": out_dir=os.path.abspath(args[i+1])
    os.makedirs(out_dir,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    arm=next((o for o in bpy.context.scene.objects if o.type=="ARMATURE"),None)
    if arm is None: raise RuntimeError("No armature found")
    bpy.context.view_layer.update()
    bones=[]
    for b in arm.data.bones:
        head=arm.matrix_world @ b.head_local
        tail=arm.matrix_world @ b.tail_local
        pb=arm.pose.bones.get(b.name)
        phead=arm.matrix_world @ pb.head if pb else head
        ptail=arm.matrix_world @ pb.tail if pb else tail
        bones.append({"name":b.name,"parent":b.parent.name if b.parent else None,
          "rest_head":[round(float(v),5) for v in head],"rest_tail":[round(float(v),5) for v in tail],
          "pose_head":[round(float(v),5) for v in phead],"pose_tail":[round(float(v),5) for v in ptail],
          "rest_pose_head_delta":round(float((phead-head).length),6),
          "rest_pose_tail_delta":round(float((ptail-tail).length),6)})
    mesh_rows=[]
    for obj in (o for o in bpy.context.scene.objects if o.type=="MESH"):
        coords=[obj.matrix_world@v.co for v in obj.data.vertices]
        if not coords: continue
        lo=[min(p[i] for p in coords) for i in range(3)]; hi=[max(p[i] for p in coords) for i in range(3)]
        center=Vector([(lo[i]+hi[i])/2 for i in range(3)])
        groups={g.index:g.name for g in obj.vertex_groups}
        weight_sums={}
        for v in obj.data.vertices:
            for g in v.groups:
                n=groups.get(g.group)
                if n: weight_sums[n]=weight_sums.get(n,0.0)+float(g.weight)
        dominant=sorted(weight_sums.items(),key=lambda x:x[1],reverse=True)[:4]
        nearest=sorted([{"bone":b["name"],"distance":round(float((center-Vector(b["rest_head"])).length),5)} for b in bones],key=lambda x:x["distance"])[:3]
        mesh_rows.append({"mesh":obj.name,"center":[round(float(v),5) for v in center],
          "bounds_min":[round(float(v),5) for v in lo],"bounds_max":[round(float(v),5) for v in hi],
          "dominant_weight_groups":[{"bone":n,"weight_sum":round(w,5)} for n,w in dominant],
          "nearest_rest_bone_heads":nearest})
    report={"status":"READ_ONLY_DIAGNOSTIC","source":os.path.basename(source),
      "method":"Compare armature rest/pose bone endpoints and mesh bounds/weight groups. No geometry or weights modified.",
      "armature":arm.name,"bone_count":len(bones),"mesh_count":len(mesh_rows),
      "bones":bones,"meshes":mesh_rows}
    path=os.path.join(out_dir,"v313-rest-pose-comparison.json")
    with open(path,"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print("V313_REST_POSE_COMPARISON=DIAGNOSTIC_ONLY")
    print(json.dumps({"bone_count":len(bones),"mesh_count":len(mesh_rows),
      "bones_with_rest_pose_delta":[b["name"] for b in bones if b["rest_pose_head_delta"]>1e-4 or b["rest_pose_tail_delta"]>1e-4],
      "mesh_sample":mesh_rows[:8]},ensure_ascii=False))
if __name__=="__main__": main()
