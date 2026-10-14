import bpy, json, math, os, sys
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def distance_to_segment(p, a, b):
    ab=b-a
    if ab.length_squared < 1e-12: return (p-a).length
    t=max(0.0,min(1.0,(p-a).dot(ab)/ab.length_squared))
    return (p-(a+t*ab)).length

def main():
    args=args_after_dashdash()
    source=os.path.abspath("lam-default.glb")
    out_dir=os.path.abspath("artifacts/v313-mesh-localization")
    for i,arg in enumerate(args[:-1]):
        if arg=="--input": source=os.path.abspath(args[i+1])
        elif arg=="--output-dir": out_dir=os.path.abspath(args[i+1])
    os.makedirs(out_dir,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    arm=next((o for o in bpy.context.scene.objects if o.type=="ARMATURE"),None)
    if arm is None: raise RuntimeError("No armature found")
    bones={b.name:(arm.matrix_world@b.head_local,arm.matrix_world@b.tail_local) for b in arm.data.bones}
    rows=[]
    for obj in (o for o in bpy.context.scene.objects if o.type=="MESH"):
        names={g.index:g.name for g in obj.vertex_groups}
        accum={}
        for v in obj.data.vertices:
            p=obj.matrix_world@v.co
            for g in v.groups:
                name=names.get(g.group)
                if name not in bones or g.weight<=1e-6: continue
                x=accum.setdefault(name,{"weight":0.0,"sum":Vector((0,0,0)),"memberships":0})
                x["weight"]+=float(g.weight); x["sum"]+=p*float(g.weight); x["memberships"]+=1
        for name,x in accum.items():
            center=x["sum"]/x["weight"]
            a,b=bones[name]
            rows.append({"mesh":obj.name,"bone":name,"weight_sum":round(x["weight"],5),
                         "weighted_memberships":x["memberships"],
                         "centroid_world":[round(float(q),5) for q in center],
                         "distance_to_bone_segment":round(float(distance_to_segment(center,a,b)),5)})
    rows.sort(key=lambda r:r["distance_to_bone_segment"],reverse=True)
    report={"status":"DIAGNOSTIC_ONLY_NO_MODEL_CHANGES","source":os.path.basename(source),
            "mesh_count":sum(1 for o in bpy.context.scene.objects if o.type=="MESH"),
            "bone_count":len(bones),"method":"Per-mesh, per-bone weighted centroid distance. Heuristic for locating suspicious assignments, not proof of a skinning error.",
            "worst_mesh_bone_pairs":rows[:60],
            "hips_group_contributors":sorted([r for r in rows if r["bone"]=="Lam_Joint_Hips"],key=lambda r:r["distance_to_bone_segment"],reverse=True)}
    path=os.path.join(out_dir,"v313-mesh-localization.json")
    with open(path,"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print("V313_MESH_LOCALIZATION=DIAGNOSTIC_ONLY")
    print(json.dumps({"mesh_count":report["mesh_count"],"bone_count":report["bone_count"],
        "worst_mesh_bone_pairs":report["worst_mesh_bone_pairs"][:10],
        "hips_group_contributors":report["hips_group_contributors"][:10]},ensure_ascii=False))
if __name__=="__main__": main()
