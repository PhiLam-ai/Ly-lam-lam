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
    dress=material("Candidate deep teal dress",(.025,.12,.15))
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
    # Adult feminine silhouette: defined waist, fuller hips, and a softly fuller chest.
    trunk.append(uv("trunk_waist",(0,0,3.38),(.335,.235,.50),dress))
    trunk.append(uv("trunk_hips",(0,0,2.99),(.455,.285,.36),dress))
    trunk.append(uv("trunk_torso",(0,0,3.89),(.385,.245,.54),dress))
    trunk.append(uv("trunk_chest.L",(-.145,-.115,3.99),(.155,.135,.165),dress,40,28))
    trunk.append(uv("trunk_chest.R",(.145,-.115,3.99),(.155,.135,.165),dress,40,28))
    trunk.append(uv("trunk_shoulders",(0,0,4.255),(.395,.225,.19),dress))
    # Neck and head are intentionally separate to preserve future facial rigging.
    uv("neck",(0,0,4.610),(.125,.125,.265),skin)
    uv("head",(0,-.015,5.055),(.295,.265,.385),skin,64,40)
    # Soft cheek volume and a gentler jaw/chin transition for a less toy-like face.
    uv("cheek.L",(-.125,-.220,4.985),(.060,.025,.050),skin,32,20)
    uv("cheek.R",(.125,-.220,4.985),(.060,.025,.050),skin,32,20)
    uv("chin",(0,-.195,4.865),(.070,.028,.045),skin,32,20)
    # ears
    uv("ear.L",(-.310,0,5.035),(.050,.060,.085),skin)
    uv("ear.R",(.310,0,5.035),(.050,.060,.085),skin)
    # Hair cap and back hair
    uv("hair_cap",(0,.025,5.225),(.325,.292,.285),hair,48,32)
    # Swept fringe pieces soften the hard helmet-like hairline.
    uv("fringe.L",(-.095,-.224,5.205),(.125,.035,.040),hair,32,20)
    uv("fringe.R",(.075,-.226,5.212),(.125,.035,.040),hair,32,20)
    uv("fringe_tip",(0,-.237,5.168),(.065,.025,.030),hair,32,20)
    uv("hair_back",(0,.16,4.99),(.315,.16,.46),hair,36,24)
    uv("hair_side.L",(-.265,.015,4.99),(.075,.10,.37),hair)
    uv("hair_side.R",(.265,.015,4.99),(.075,.10,.37),hair)
    # eyes face toward -Y
    for x,side in [(-.115,"L"),(.115,"R")]:
        uv("eye_white."+side,(x,-.257,5.075),(.041,.017,.027),white)
        uv("iris."+side,(x,-.274,5.074),(.015,.008,.017),iris)
        uv("brow."+side,(x,-.258,5.119),(.040,.007,.006),hair)
    uv("nose",(0,-.278,4.995),(.022,.028,.030),skin)
    uv("mouth",(0,-.267,4.925),(.046,.010,.009),material("Muted rose lips",(.42,.105,.12),.4))
    # A tiny smile highlight, kept subtle in this geometry-only prototype.
    uv("lower_lip",(0,-.268,4.913),(.030,.007,.005),material("Lower lip",(.57,.20,.20),.4))
    # Arms are grouped and voxel-fused per side to reduce toy-like elbow/wrist seams.
    arms=[]
    for sign,side in [(-1,"L"),(1,"R")]:
        shoulder=(sign*.355,-.005,4.275); elbow=(sign*.555,-.005,3.80); wrist=(sign*.585,-.035,3.35); hand=(sign*.585,-.055,3.18)
        arms.append(capsule_piece("upper_arm."+side,shoulder,elbow,.135,skin,.14))
        arms.append(uv("elbow."+side,elbow,(.11,.115,.11),skin))
        arms.append(capsule_piece("forearm."+side,elbow,wrist,.095,skin,.10))
        arms.append(uv("hand."+side,hand,(.09,.07,.125),skin))
        for j in range(4):
            x=sign*(.545+j*.028)
            arms.append(capsule_piece("finger."+side+str(j),(x,-.065,3.10),(x,-.07,3.015-(.02 if j in (0,3) else 0)),.018,skin,.018))
        arms.append(capsule_piece("thumb."+side,(sign*.535,-.08,3.19),(sign*.49,-.09,3.11),.024,skin,.024))
    # legs are fused separately into one lower-body surface; dress hem overlaps the upper legs.
    legs=[]
    for sign,side in [(-1,"L"),(1,"R")]:
        hip=(sign*.205,0,2.72); knee=(sign*.205,-.005,1.72); ankle=(sign*.20,0,.30)
        legs.append(capsule_piece("thigh."+side,hip,(sign*.205,-.005,1.60),.205,skin,.205))
        # Omit the separate knee sphere; overlapping thigh/shin capsules fuse into a smoother transition.
        legs.append(capsule_piece("shin."+side,(sign*.205,-.005,1.82),ankle,.115,skin,.12))
        uv("foot."+side,(sign*.22,-.115,.14),(.11,.19,.075),shoes)
    # fuse body parts that should visually read continuous. Voxel remesh joins overlapping surfaces.
    def fuse(objects,name,voxel):
        # Each fused anatomical group is intended to use one material only.
        # Prevent overlapping capsule faces from leaving material-index bands.
        base_material = next((m for obj in objects for m in obj.data.materials if m), None)
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.object.join()
        o=bpy.context.object; o.name=name
        mod=o.modifiers.new("VoxelFuse","REMESH"); mod.mode="VOXEL"; mod.voxel_size=voxel
        bpy.ops.object.modifier_apply(modifier=mod.name)
        sm=o.modifiers.new("AnatomicalTransitionSmooth","SMOOTH"); sm.factor=1.1; sm.iterations=12
        bpy.ops.object.modifier_apply(modifier=sm.name)
        o.data.materials.clear()
        if base_material:
            o.data.materials.append(base_material)
            for p in o.data.polygons: p.material_index=0
        for p in o.data.polygons:p.use_smooth=True
        return o
    fused_trunk=fuse(trunk,"BODY_DRESS_CONTINUOUS",.024)
    fused_legs=fuse(legs,"BODY_LEGS_CONTINUOUS",.016)
    fused_arms=fuse(arms,"BODY_ARMS_CONTINUOUS",.014)
    # Add a modest flared skirt overlay so the prototype reads as a dressed adult figure,
    # rather than a single tight torso/hip capsule. Kept isolated to this experimental candidate.
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=.51, radius2=.385, depth=.56, location=(0,-.012,2.82))
    skirt=bpy.context.object; skirt.name="EXPERIMENTAL_FLARED_SKIRT"; skirt.data.materials.append(dress)
    bevel=skirt.modifiers.new("Soft skirt edges","BEVEL"); bevel.width=.045; bevel.segments=3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for p in skirt.data.polygons: p.use_smooth=True
    # Normalize the generated figure to the requested 1.60 m scale (Z extent about 5.5 units before normalization).
    scale_factor=1.60/5.5
    for obj in list(scene.objects):
        if obj.type=="MESH":
            obj.location *= scale_factor
            obj.scale *= scale_factor
    # Measure the actual scaled character mesh bounds (exclude floor/cameras/lights).
    bpy.context.view_layer.update()
    figure_meshes=[obj for obj in scene.objects if obj.type=="MESH" and obj.name!="StudioFloor"]
    coords=[]
    for obj in figure_meshes:
        coords.extend([obj.matrix_world @ Vector(corner) for corner in obj.bound_box])
    bounds={"min":[min(v[i] for v in coords) for i in range(3)],
            "max":[max(v[i] for v in coords) for i in range(3)]}
    bounds["size"]=[bounds["max"][i]-bounds["min"][i] for i in range(3)]
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
    # Side profile catches head-depth, face-offset, torso-depth, and skirt/leg intersection issues.
    cam3=camera("SideCamera",(dist,0,.77)); scene.camera=cam3
    scene.render.filepath=os.path.join(out,"coherent-body-side.png"); bpy.ops.render.render(write_still=True)
    glb=os.path.join(out,"lam-coherent-body-candidate.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in scene.objects:
        # Export only the character; keep the studio floor out of the GLB runtime asset.
        if o.type in {"MESH","ARMATURE"} and o.name != "StudioFloor":o.select_set(True)
    bpy.context.view_layer.objects.active=fused_trunk
    bpy.ops.export_scene.gltf(filepath=glb,export_format="GLB",use_selection=True)
    report={"status":"EXPERIMENTAL_CANDIDATE_NOT_APPROVED","purpose":"Procedural stylized anatomy prototype; separate from production GLB","candidate":os.path.basename(glb),"bytes":os.path.getsize(glb),"mesh_count":sum(o.type=="MESH" for o in figure_meshes),"measured_bounds_m":bounds,"height_error_m":abs(bounds["size"][2]-1.60),"renders":["coherent-body-front.png","coherent-body-three-quarter.png","coherent-body-side.png"],"warnings":["Not a photorealistic final avatar","No armature or facial morphs transferred","Figure normalized to approximately 1.60 m","Arms fused as experimental skin surfaces to reduce segment seams","Must visually inspect and test in web viewer before any promotion","Adult silhouette refinement: fuller hip and thigh volumes plus softly fuller chest; experimental only"]}
    with open(os.path.join(out,"coherent-body-candidate.json"),"w",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print("COHERENT_BODY_CANDIDATE="+json.dumps(report,ensure_ascii=False))
    assert os.path.getsize(glb)>1024
    assert abs(bounds["size"][2]-1.60)<0.03, "Candidate height is outside 1.60m tolerance"
if __name__=="__main__":
    try:main()
    except Exception:traceback.print_exc();raise
