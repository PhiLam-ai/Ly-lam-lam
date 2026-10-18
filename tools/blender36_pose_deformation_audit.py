import bpy, json, math, os, sys, traceback
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def parse_args():
    a=args_after_dashdash(); c={"input":"lam-default.glb","output_dir":"artifacts/pose-deformation-audit"}
    i=0
    while i<len(a):
        if a[i]=="--input" and i+1<len(a): c["input"]=a[i+1]; i+=2
        elif a[i]=="--output-dir" and i+1<len(a): c["output_dir"]=a[i+1]; i+=2
        else: i+=1
    return c

def snapshot(meshes, depsgraph):
    data={}
    for obj in meshes:
        ev=obj.evaluated_get(depsgraph)
        data[obj.name]=[ev.matrix_world @ v.co for v in ev.data.vertices]
    return data

def max_displacement(before, after):
    maximum=0.0; moved=0; total=0
    for name, points in before.items():
        new=after.get(name, [])
        for a,b in zip(points,new):
            d=(b-a).length; maximum=max(maximum,d); total+=1
            if d>1e-5: moved+=1
    return {"max_vertex_displacement":round(maximum,8),"vertices_moved_over_1e-5":moved,"vertices_sampled":total}

def main():
    cfg=parse_args(); source=os.path.abspath(cfg["input"]); out=os.path.abspath(cfg["output_dir"])
    os.makedirs(out,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    scene=bpy.context.scene
    meshes=[o for o in scene.objects if o.type=="MESH"]
    rigs=[o for o in scene.objects if o.type=="ARMATURE"]
    if not rigs: raise RuntimeError("Cannot run pose test: no armature in GLB")
    rig=rigs[0]
    bones={b.name for b in rig.data.bones}
    depsgraph=bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    baseline=snapshot(meshes,depsgraph)
    tests=[]
    pose_tests=[
      ("left_shoulder_raise_45","Lam_Joint_LeftShoulder",math.radians(45)),
      ("right_shoulder_raise_45","Lam_Joint_RightShoulder",math.radians(-45)),
      ("left_elbow_bend_45","Lam_Joint_LeftElbow",math.radians(45)),
      ("right_elbow_bend_45","Lam_Joint_RightElbow",math.radians(-45)),
    ]
    for label,bone_name,angle in pose_tests:
        if bone_name not in bones:
            tests.append({"name":label,"bone":bone_name,"status":"MISSING_BONE"})
            continue
        pb=rig.pose.bones[bone_name]
        old_mode=pb.rotation_mode
        old_rot=pb.rotation_euler.copy()
        pb.rotation_mode="XYZ"
        # Use the local X axis for a first-pass structural deformation probe.
        pb.rotation_euler.x=old_rot.x+angle
        bpy.context.view_layer.update()
        depsgraph=bpy.context.evaluated_depsgraph_get()
        posed=snapshot(meshes,depsgraph)
        metric=max_displacement(baseline,posed)
        tests.append({"name":label,"bone":bone_name,"angle_degrees":round(math.degrees(angle)),"status":"MOVED" if metric["max_vertex_displacement"]>1e-5 else "NO_MEASURABLE_DEFORMATION",**metric})
        pb.rotation_euler=old_rot
        pb.rotation_mode=old_mode
        bpy.context.view_layer.update()
    report={"status":"POSE_TEST_RECORDED","purpose":"Automated local-axis deformation probe only; it does not establish anatomically correct deformation or visual acceptance.","input_file":os.path.basename(source),"armature":rig.name,"bone_count":len(rig.data.bones),"mesh_count":len(meshes),"tests":tests,"approval":"NOT_APPROVED_VISUAL_REVIEW_REQUIRED"}
    with open(os.path.join(out,"pose-deformation-audit.json"),"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print("POSE_DEFORMATION_AUDIT="+json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    try: main()
    except Exception: traceback.print_exc(); raise
