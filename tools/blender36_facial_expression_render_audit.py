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
    # Estimate head framing from meshes in the upper 30% of the character's total bounds.
    allpts=[o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    zmin=min(p.z for p in allpts); zmax=max(p.z for p in allpts); zcut=zmax-(zmax-zmin)*0.34
    head_objs=[]
    for o in meshes:
        pts=[o.matrix_world @ Vector(c) for c in o.bound_box]
        if max(p.z for p in pts)>=zcut: head_objs.append(o)
    pts=[o.matrix_world @ Vector(c) for o in head_objs for c in o.bound_box]
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
    cam.location=(center[0],center[1]-head_h*4,center[2]); aim(cam,center)
    cam_data.type="ORTHO"; cam_data.ortho_scale=head_h*1.38; scene.camera=cam
    for o in shape_objs:
        for k in o.data.shape_keys.key_blocks: k.value=0.0
    scene.render.filepath=os.path.join(out,"face-neutral.png"); bpy.ops.render.render(write_still=True)
    records=[]
    for o in shape_objs:
        for k in list(o.data.shape_keys.key_blocks)[1:]:
            for other in shape_objs:
                for ok in other.data.shape_keys.key_blocks: ok.value=0.0
            k.value=1.0
            # Stable filenames and one isolated key per render.
            safe="".join(c.lower() if c.isalnum() else "-" for c in k.name).strip("-")
            filename=f"{o.name}__{safe}.png"
            scene.render.filepath=os.path.join(out,filename); bpy.ops.render.render(write_still=True)
            records.append({"mesh":o.name,"key":k.name,"value":1.0,"image":filename,"status":"RENDERED_ISOLATED"})
            k.value=0.0
    report={"status":"RENDERED_VISUAL_REVIEW_REQUIRED","source":os.path.basename(src),
            "head_meshes_used_for_framing":[o.name for o in head_objs],
            "shape_key_mesh_count":len(shape_objs),"render_count":1+len(records),
            "note":"Renders are isolated diagnostic images, not automatic expression-quality approval.",
            "expressions":records}
    with open(os.path.join(out,"facial-expression-render-report.json"),"w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print("FACIAL_EXPRESSION_RENDER_AUDIT="+json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
