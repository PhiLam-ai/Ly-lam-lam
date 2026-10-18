import bpy, json, math, os, sys
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []

def parse_args():
    args=args_after_dashdash(); cfg={"input":"lam-default.glb","output-dir":"artifacts/facial-expression-renders"}
    i=0
    while i<len(args):
        if args[i] in ("--input","--output-dir") and i+1<len(args):
            cfg["input" if args[i]=="--input" else "output-dir"]=args[i+1]; i+=2
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
    # Frame tightly around the actual facial feature meshes, not the upper third of the whole body.
    # Including torso/shoulder bounds here previously made the face too small to inspect.
    face_objs=list(shape_objs)
    face_names=("head","hair","ear","nose","face","eye","brow","mouth","chin","teeth","tongue")
    for o in meshes:
        name=o.name.lower()
        is_forearm="forearm" in name or "arm" in name
        if o not in face_objs and not is_forearm and any(token in name for token in face_names):
            face_objs.append(o)
    if not face_objs: raise RuntimeError("No face meshes available for close-up framing")
    pts=[o.matrix_world @ Vector(c) for o in face_objs for c in o.bound_box]
    mins=[min(p[i] for p in pts) for i in range(3)]; maxs=[max(p[i] for p in pts) for i in range(3)]
    center=[(mins[i]+maxs[i])/2 for i in range(3)]
    head_h=maxs[2]-mins[2]
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
    # GLB front-facing features face toward +Y; render from +Y so eyes and mouth are visible.\n    cam.location=(center[0],center[1]+head_h*4,center[2]); aim(cam,center)
    cam_data.type="ORTHO"; cam_data.ortho_scale=head_h*1.38; scene.camera=cam
    for o in shape_objs:
        for k in o.data.shape_keys.key_blocks: k.value=0.0
    scene.render.filepath=os.path.join(out,"face-neutral.png"); bpy.ops.render.render(write_still=True)
    records=[]
    # Render each unique expression once, enabling that key on every mesh that owns it.
    # This produces one coherent face expression per key rather than 12 duplicates per mesh.
    key_names=[]
    for o in shape_objs:
        for k in list(o.data.shape_keys.key_blocks)[1:]:
            if k.name not in key_names: key_names.append(k.name)
    for key_name in key_names:
        for other in shape_objs:
            for ok in other.data.shape_keys.key_blocks: ok.value=0.0
        enabled=[]
        for o in shape_objs:
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
            "shape_key_mesh_count":len(shape_objs),"render_count":1+len(records),
            "note":"Renders are isolated diagnostic images, not automatic expression-quality approval.",
            "expressions":records}
    with open(os.path.join(out,"facial-expression-render-report.json"),"w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print("FACIAL_EXPRESSION_RENDER_AUDIT="+json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
