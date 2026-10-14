import bpy, os, sys, json, hashlib
from mathutils import Vector

def main():
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    source=os.path.abspath("lam-default.glb")
    out_dir=os.path.abspath("artifacts/v313-pose-reset-experiment")
    for i,arg in enumerate(args[:-1]):
        if arg=="--input": source=os.path.abspath(args[i+1])
        elif arg=="--output-dir": out_dir=os.path.abspath(args[i+1])
    os.makedirs(out_dir,exist_ok=True)
    source_hash=hashlib.sha256(open(source,"rb").read()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    arms=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    if not arms: raise RuntimeError("No armature found")
    arm=arms[0]
    before=[]
    for p in arm.pose.bones:
        before.append({"bone":p.name,"location":[float(x) for x in p.location],
          "rotation_mode":p.rotation_mode,"rotation_euler":[float(x) for x in p.rotation_euler],
          "rotation_quaternion":[float(x) for x in p.rotation_quaternion],
          "rotation_axis_angle":[float(x) for x in p.rotation_axis_angle],
          "scale":[float(x) for x in p.scale]})
    # Reversible experiment only: reset pose channels on in-memory imported copy.
    for p in arm.pose.bones:
        p.location=(0.0,0.0,0.0)
        p.rotation_mode="QUATERNION"
        p.rotation_quaternion=(1.0,0.0,0.0,0.0)
        p.scale=(1.0,1.0,1.0)
    bpy.context.view_layer.update()
    after=[]
    for p in arm.pose.bones:
        after.append({"bone":p.name,"location":[float(x) for x in p.location],
          "rotation_quaternion":[float(x) for x in p.rotation_quaternion],"scale":[float(x) for x in p.scale]})
    # Set render camera and lights for front evidence.
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=768; scene.render.resolution_y=768; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    if scene.world is None: scene.world=bpy.data.worlds.new("V313_ResetPose_World")
    scene.world.color=(0.06,0.06,0.06)
    # Use orthographic camera looking from front (-Y) toward model center.
    cam_data=bpy.data.cameras.new("V313_ResetPose_Camera"); cam=bpy.data.objects.new("V313_ResetPose_Camera",cam_data); scene.collection.objects.link(cam)
    cam.location=(0,-15,1.75); target=Vector((0,0,1.75)); direction=target-Vector(cam.location); cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler(); cam.data.type="ORTHO"; cam.data.ortho_scale=9.8; scene.camera=cam
    ld=bpy.data.lights.new("V313_ResetPose_Key","AREA"); lo=bpy.data.objects.new("V313_ResetPose_Key",ld); scene.collection.objects.link(lo); lo.location=(-4,-6,7); ld.energy=850; ld.size=5
    ld2=bpy.data.lights.new("V313_ResetPose_Fill","AREA"); lo2=bpy.data.objects.new("V313_ResetPose_Fill",ld2); scene.collection.objects.link(lo2); lo2.location=(4,-4,3); ld2.energy=450; ld2.size=4
    scene.render.filepath=os.path.join(out_dir,"pose-reset-front.png")
    bpy.ops.render.render(write_still=True)
    out_glb=os.path.join(out_dir,"lam-pose-reset-experiment.glb")
    bpy.ops.export_scene.gltf(filepath=out_glb,export_format="GLB",export_morph=True,export_skins=True,export_animations=False)
    exported_hash=hashlib.sha256(open(out_glb,"rb").read()).hexdigest()
    report={"status":"EXPERIMENT_ONLY_NOT_APPROVED","source_sha256":source_hash,
      "source_unchanged":hashlib.sha256(open(source,"rb").read()).hexdigest()==source_hash,
      "experiment":"Reset all armature pose channels to identity on an imported in-memory copy, then render/export separate candidate.",
      "pose_channels_before":before,"pose_channels_after":after,
      "candidate_file":os.path.basename(out_glb),"candidate_sha256":exported_hash,
      "morphs_before_export":sorted(set(k.name for o in bpy.data.objects if o.type=="MESH" and o.data.shape_keys for k in o.data.shape_keys.key_blocks)),
      "warning":"This experiment tests pose-channel offsets only. It is not an accepted repair; inspect image and re-audit skin, 12 morphs and browser rendering before promotion."}
    with open(os.path.join(out_dir,"pose-reset-experiment-report.json"),"w",encoding="utf-8") as f: json.dump(report,f,indent=2,ensure_ascii=False)
    print("V313_POSE_RESET_EXPERIMENT=NOT_APPROVED")
    print(json.dumps({"source_unchanged":report["source_unchanged"],"bones_with_nonidentity_before":[x["bone"] for x in before if any(abs(v)>1e-5 for v in x["location"]+([x["rotation_quaternion"][i]-(1.0 if i==0 else 0.0) for i in range(4)] if x["rotation_mode"]=="QUATERNION" else x["rotation_euler"])+[s-1 for s in x["scale"]])],
      "morph_count":len(report["morphs_before_export"]),"candidate_sha256":exported_hash},ensure_ascii=False))
if __name__=="__main__": main()
