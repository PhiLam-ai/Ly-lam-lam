import bpy, os, sys, json, hashlib, math, traceback
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []

def main():
    args=args_after_dashdash(); out=os.path.abspath("artifacts/coherent-body-candidate")
    for i,a in enumerate(args[:-1]):
        if a=="--output-dir": out=os.path.abspath(args[i+1])
    os.makedirs(out,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type="WORLD"
    scene.render.resolution_x=900; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    if scene.world is None: scene.world=bpy.data.worlds.new("LamCandidateWorld")
    scene.world.color=(0.045,0.045,0.045)

    def material(name,color,rough=.6):
        m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.roughness=rough; return m
    skin=material("Candidate warm skin",(0.62,.34,.23))
    dress=material("Candidate deep teal dress",(.035,.16,.19))
    hair=material("Candidate black hair",(.025,.018,.022),.32)
    shoes=material("Candidate dark shoes",(.035,.035,.04))
    white=material("Candidate eye whites",(.86,.8,.7),.35)
    iris=material("Candidate brown eyes",(.18,.075,.025),.28)
    def uv(name,loc,scale,mat,segments=32,rings=20):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
        o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        o.data.materials.append(mat)
        for p in o.data.polygons:p.use_smooth=True
        return o
    def capsule_piece(name,a,b,radius,mat,depth=None):
        mid=(Vector(a)+Vector(b))/2; vec=Vector(b)-Vector(a)
        o=uv(name,mid,(radius,radius if depth is None else depth,vec.length/2+radius),mat)
        o.rotation_mode="QUATERNION"; o.rotation_quaternion=vec.to_track_quat("Z","Y")
        return o
    # Units: approximate 1.60m total height, Z up. Build a stylized female figure.
    # Dress and trunk are fused via voxel remesh, creating a continuous torso/hip silhouette.
    trunk=[]
    trunk.append(uv("trunk_waist",(0,0,3.35),(.34,.23,.48),dress))
    trunk.append(uv("trunk_hips",(0,0,2.92),(.48,.29,.40),dress))
    trunk.append(uv("trunk_torso",(0,0,3.88),(.43,.25,.60),dress))
    trunk.append(uv("trunk_shoulders",(0,0,4.31),(.55,.25,.20),dress))
    # Neck and head are intentionally separate to preserve future facial rigging.
    uv("neck",(0,0,4.60),(.14,.14,.25),skin)
    uv("head",(0,-.015,5.02),(.29,.27,.39),skin,48,32)
    # ears
    uv("ear.L",(-.29,0,5.02),(.065,.075,.105),skin)
    uv("ear.R",(.29,0,5.02),(.065,.075,.105),skin)
    # Hair cap and back hair
    uv("hair_cap",(0,.025,5.20),(.31,.285,.29),hair,40,24)
    uv("hair_back",(0,.16,4.98),(.30,.16,.48),hair,36,24)
    uv("hair_side.L",(-.265,.015,4.99),(.075,.10,.37),hair)
    uv("hair_side.R",(.265,.015,4.99),(.075,.10,.37),hair)
    # eyes face toward -Y
    for x,side in [(-.115,"L"),(.115,"R")]:
        uv("eye_white."+side,(x,-.257,5.075),(.066,.035,.048),white)
        uv("iris."+side,(x,-.288,5.074),(.027,.016,.03),iris)
        uv("brow."+side,(x,-.258,5.145),(.075,.025,.018),hair)
    uv("nose",(0,-.294,4.995),(.045,.07,.075),skin)
    uv("mouth",(0,-.275,4.91),(.075,.018,.022),material("Muted rose lips",(.34,.075,.08),.4))
    # Arms are grouped and voxel-fused per side to reduce toy-like elbow/wrist seams.
    arms=[]
    for sign,side in [(-1,"L"),(1,"R")]:
        shoulder=(sign*.52,0,4.28); elbow=(sign*.67,-.005,3.78); wrist=(sign*.69,-.035,3.32); hand=(sign*.69,-.055,3.15)
        arms.append(capsule_piece("upper_arm."+side,shoulder,elbow,.125,skin,.13))
        arms.append(uv("elbow."+side,elbow,(.115,.12,.12),skin))
        arms.append(capsule_piece("forearm."+side,elbow,wrist,.095,skin,.10))
        arms.append(uv("hand."+side,hand,(.09,.07,.125),skin))
        for j in range(4):
            x=sign*(.635+j*.035)
            arms.append(capsule_piece("finger."+side+str(j),(x,-.065,3.10),(x,-.07,3.015-(.02 if j in (0,3) else 0)),.018,skin,.018))
        arms.append(capsule_piece("thumb."+side,(sign*.62,-.08,3.16),(sign*.57,-.09,3.08),.024,skin,.024))
    # legs are fused separately into one lower-body surface; dress hem overlaps the upper legs.
    legs=[]
    for sign,side in [(-1,"L"),(1,"R")]:
        hip=(sign*.22,0,2.72); knee=(sign*.23,-.005,1.72); ankle=(sign*.23,0,.30)
        legs.append(capsule_piece("thigh."+side,hip,knee,.19,skin,.19))
        legs.append(uv("knee."+side,knee,(.17,.17,.18),skin))
        legs.append(capsule_piece("shin."+side,knee,ankle,.115,skin,.12))
        uv("foot."+side,(sign*.23,-.12,.14),(.13,.28,.12),shoes)
    # fuse body parts that should visually read continuous. Voxel remesh joins overlapping surfaces.
    def fuse(objects,name,voxel):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.object.join()
        o=bpy.context.object; o.name=name
        mod=o.modifiers.new("VoxelFuse","REMESH"); mod.mode="VOXEL"; mod.voxel_size=voxel
        bpy.ops.object.modifier_apply(modifier=mod.name)
        sm=o.modifiers.new("GentleSmooth","SMOOTH"); sm.factor=1.15; sm.iterations=3
        bpy.ops.object.modifier_apply(modifier=sm.name)
        for p in o.data.polygons:p.use_smooth=True
        return o
    fused_trunk=fuse(trunk,"BODY_DRESS_CONTINUOUS",.028)
    fused_legs=fuse(legs,"BODY_LEGS_CONTINUOUS",.022)
    fused_arms=fuse(arms,"BODY_ARMS_CONTINUOUS",.018)
    # Normalize the generated figure to the requested 1.60 m scale (Z extent about 5.5 units before normalization).
    scale_factor=1.60/5.5
    for obj in list(scene.objects):
        if obj.type=="MESH":
            obj.location *= scale_factor
            obj.scale *= scale_factor
    # camera, ground, and render
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.015))
    floor=bpy.context.object; floor.name="StudioFloor"; floor.data.materials.append(material("Studio floor",(.055,.06,.065)))
    target=(0,0,.77); dist=4.1
    def camera(name,loc):
        d=bpy.data.cameras.new(name); c=bpy.data.objects.new(name,d); scene.collection.objects.link(c); c.location=loc
        c.rotation_euler=(Vector(target)-c.location).to_track_quat("-Z","Y").to_euler(); d.type="ORTHO"; d.ortho_scale=1.85; return c
    cam=camera("FrontCamera",(0,-dist,.77)); scene.camera=cam
    scene.render.filepath=os.path.join(out,"coherent-body-front.png"); bpy.ops.render.render(write_still=True)
    cam2=camera("ThreeQuarterCamera",(dist*.7,-dist*.7,.77)); scene.camera=cam2
    scene.render.filepath=os.path.join(out,"coherent-body-three-quarter.png"); bpy.ops.render.render(write_still=True)
    glb=os.path.join(out,"lam-coherent-body-candidate.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in scene.objects:
        if o.type in {"MESH","ARMATURE"}:o.select_set(True)
    bpy.context.view_layer.objects.active=fused_trunk
    bpy.ops.export_scene.gltf(filepath=glb,export_format="GLB",use_selection=True)
    report={"status":"EXPERIMENTAL_CANDIDATE_NOT_APPROVED","purpose":"Procedural stylized anatomy prototype; separate from production GLB","candidate":os.path.basename(glb),"bytes":os.path.getsize(glb),"mesh_count":sum(o.type=="MESH" for o in scene.objects),"renders":["coherent-body-front.png","coherent-body-three-quarter.png"],"warnings":["Not a photorealistic final avatar","No armature or facial morphs transferred","Figure normalized to approximately 1.60 m","Arms fused as experimental skin surfaces to reduce segment seams","Must visually inspect and test in web viewer before any promotion"]}
    with open(os.path.join(out,"coherent-body-candidate.json"),"w",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print("COHERENT_BODY_CANDIDATE="+json.dumps(report,ensure_ascii=False))
    assert os.path.getsize(glb)>1024
if __name__=="__main__":
    try:main()
    except Exception:traceback.print_exc();raise
