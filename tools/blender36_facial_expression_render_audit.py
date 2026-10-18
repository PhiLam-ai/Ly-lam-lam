import bpy, json, math, os, sys
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []

def parse_args():
    args=args_after_dashdash(); cfg={"input":"lam-default.glb","output-dir":"artifacts/facial-expression-renders","front-axis":"+Y"}
    i=0
    while i<len(args):
        if args[i] in ("--input","--output-dir","--front-axis") and i+1<len(args):
            key={"--input":"input","--output-dir":"output-dir","--front-axis":"front-axis"}[args[i]]
            cfg[key]=args[i+1]; i+=2
        else: i+=1
    return cfg

def aim(camera, target):
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()

def main():
    cfg=parse_args(); src=os.path.abspath(cfg["input"]); out=os.path.abspath(cfg["output-dir"])
    os.makedirs(out,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    scene=bpy.context.scene
    meshes=[o for o in scene.objects if o.type=="MESH"]
    shape_objs=[o for o in meshes if o.data.shape_keys and len(o.data.shape_keys.key_blocks)>1]
    if not shape_objs: raise RuntimeError("No shape-key meshes found")

    # Treat facial framing as a semantic allowlist. Some imported non-face meshes
    # (notably sneaker tongues) can carry generic shape keys and must never set the
    # camera bounds for a face close-up.
    face_names=("head","hair","ear","nose","face","eye","brow","mouth","chin","teeth","tongue","lip","jaw","cheek","pupil","iris","eyelid")
    non_face_names=("sneaker","shoe","foot","forearm","upper_arm","arm_skin","hand","finger","thumb")
    def is_face_mesh(obj):
        name=obj.name.lower()
        return any(token in name for token in face_names) and not any(token in name for token in non_face_names)

    face_objs=[o for o in meshes if is_face_mesh(o)]
    face_shape_objs=[o for o in shape_objs if is_face_mesh(o)]
    if not face_objs: raise RuntimeError("No face meshes available for close-up framing")
    if not face_shape_objs: raise RuntimeError("No facial shape-key meshes available")
    if cfg["front-axis"] not in ("+Y","-Y"): raise ValueError("--front-axis must be +Y or -Y")
    front_sign=1 if cfg["front-axis"]=="+Y" else -1
    pts=[o.matrix_world @ Vector(corner) for o in face_objs for corner in o.bound_box]
    mins=[min(p[i] for p in pts) for i in range(3)]; maxs=[max(p[i] for p in pts) for i in range(3)]
    # LAM_CONTINUOUS_HEAD_NECK includes the long neck in a single mesh. Clip the
    # vertical camera bounds to the top 0.82 scene units so the face, not torso,
    # determines the framing even when a head/neck mesh is fused.
    face_min_z=max(mins[2],maxs[2]-0.82)
    center=[(mins[0]+maxs[0])/2,(mins[1]+maxs[1])/2,(face_min_z+maxs[2])/2]
    head_h=maxs[2]-face_min_z
    if head_h<=0: raise RuntimeError("Invalid head bounds")
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"; scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type="WORLD"; scene.display.shading.show_specular_highlight=True
    scene.render.resolution_x=720; scene.render.resolution_y=720; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGBA"
    scene.world=bpy.data.worlds.new("LamExpressionAuditWorld")
    scene.world.color=(0.055,0.055,0.055)
    cam_data=bpy.data.cameras.new("FacialExpressionAuditCamera")
    cam=bpy.data.objects.new("FacialExpressionAuditCamera",cam_data); scene.collection.objects.link(cam)
    # Keep production's known +Y direction as the default; candidates can opt into -Y explicitly.
    cam.location=(center[0],center[1]+front_sign*head_h*4,center[2]); aim(cam,center)
    cam_data.type="ORTHO"; cam_data.ortho_scale=head_h*1.38; scene.camera=cam
    for o in shape_objs:
        for k in o.data.shape_keys.key_blocks: k.value=0.0
    # Render four cardinal directions first; the GLB's front axis must be verified from pixels,
    # not guessed. Keep these probes as artifacts for diagnosing orientation.
    orientation_probes=[]
    for label,dx,dy in (("x_plus",1,0),("x_minus",-1,0),("y_plus",0,1),("y_minus",0,-1)):
        cam.location=(center[0]+dx*head_h*4,center[1]+dy*head_h*4,center[2])
        aim(cam,center)
        filename=f"orientation-probe__{label}.png"
        scene.render.filepath=os.path.join(out,filename); bpy.ops.render.render(write_still=True)
        orientation_probes.append({"view":label,"image":filename})
    cam.location=(center[0],center[1]+front_sign*head_h*4,center[2]); aim(cam,center)
    scene.render.filepath=os.path.join(out,"face-neutral.png"); bpy.ops.render.render(write_still=True)
    records=[]
    # Render each unique expression once, enabling that key on every mesh that owns it.
    # This produces one coherent face expression per key rather than 12 duplicates per mesh.
    key_names=[]
    for o in face_shape_objs:
        for k in list(o.data.shape_keys.key_blocks)[1:]:
            if k.name not in key_names: key_names.append(k.name)
    for key_name in key_names:
        for other in shape_objs:
            for ok in other.data.shape_keys.key_blocks: ok.value=0.0
        enabled=[]
        for o in face_shape_objs:
            key=o.data.shape_keys.key_blocks.get(key_name)
            if key is not None:
                key.value=1.0
                enabled.append(o.name)
        safe="".join(c.lower() if c.isalnum() else "-" for c in key_name).strip("-")
        filename=f"face-expression__{safe}.png"
        scene.render.filepath=os.path.join(out,filename); bpy.ops.render.render(write_still=True)
        records.append({"key":key_name,"value":1.0,"meshes_enabled":enabled,"image":filename,"status":"RENDERED_ISOLATED"})
    report={"status":"RENDERED_VISUAL_REVIEW_REQUIRED","source":os.path.basename(src),
            "face_meshes_used_for_framing":[o.name for o in face_objs],
            "non_facial_shape_key_meshes_excluded":[o.name for o in shape_objs if not is_face_mesh(o)],
            "shape_key_mesh_count":len(face_shape_objs),"render_count":1+len(records),
            "frontal_camera_direction":cfg["front-axis"],"orientation_probes":orientation_probes,
            "note":"Renders are isolated diagnostic images, not automatic expression-quality approval.",
            "expressions":records}
    with open(os.path.join(out,"facial-expression-render-report.json"),"w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print("FACIAL_EXPRESSION_RENDER_AUDIT="+json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
