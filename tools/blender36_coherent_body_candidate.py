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
    skin=material("Lam warm natural skin",(0.62,.34,.23),.52)
    shirt=material("Lam clean white streetwear top",(.88,.88,.84),.62)
    pants=material("Lam matte black biker pants",(.018,.018,.022),.5)
    hair=material("Lam deep black hair",(.018,.014,.018),.28)
    shoes=material("Lam white sneakers",(.88,.88,.86),.45)
    sole=material("Sneaker dark sole",(.04,.04,.045),.62)
    white=material("Natural warm eye whites",(.88,.83,.76),.4)
    iris=material("Warm brown irises",(.20,.085,.035),.3)
    pupil=material("Dark pupils",(.012,.009,.008),.22)
    lipmat=material("Soft natural rose lips",(.37,.105,.11),.45)
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
    # Integrated character candidate: use lofted garment/limb surfaces and fuse the key
    # transition areas. This replaces the old stacked torso, capsule arms and skirt blockout.

    def loft_rings(name, levels, mat, segments=48):
        """Closed elliptical loft; levels are (z, radius_x, radius_y, center_y)."""
        verts=[]; faces=[]
        for z,rx,ry,cy in levels:
            for j in range(segments):
                a=2*math.pi*j/segments
                verts.append((rx*math.cos(a),cy+ry*math.sin(a),z))
        verts.append((0.0,levels[0][3],levels[0][0])); bottom=len(verts)-1
        verts.append((0.0,levels[-1][3],levels[-1][0])); top=len(verts)-1
        for i in range(len(levels)-1):
            for j in range(segments):
                a=i*segments+j; b=i*segments+(j+1)%segments
                c=(i+1)*segments+(j+1)%segments; d=(i+1)*segments+j
                faces.append((a,b,c,d))
        for j in range(segments):
            faces.append((bottom,(j+1)%segments,j))
            a=(len(levels)-1)*segments+j; b=(len(levels)-1)*segments+(j+1)%segments
            faces.append((top,a,b))
        mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(verts,[],faces); mesh.update()
        obj=bpy.data.objects.new(name,mesh); scene.collection.objects.link(obj); obj.data.materials.append(mat)
        for p in obj.data.polygons:p.use_smooth=True
        return obj

    def tube_path(name, levels, mat, segments=28):
        """Closed limb loft; levels are (x, y, z, radius_x, radius_y)."""
        verts=[]; faces=[]
        for x,y,z,rx,ry in levels:
            for j in range(segments):
                a=2*math.pi*j/segments
                verts.append((x+rx*math.cos(a),y+ry*math.sin(a),z))
        verts.append((levels[0][0],levels[0][1],levels[0][2])); bottom=len(verts)-1
        verts.append((levels[-1][0],levels[-1][1],levels[-1][2])); top=len(verts)-1
        for i in range(len(levels)-1):
            for j in range(segments):
                a=i*segments+j; b=i*segments+(j+1)%segments
                c=(i+1)*segments+(j+1)%segments; d=(i+1)*segments+j
                faces.append((a,b,c,d))
        for j in range(segments):
            faces.append((bottom,(j+1)%segments,j))
            a=(len(levels)-1)*segments+j; b=(len(levels)-1)*segments+(j+1)%segments
            faces.append((top,a,b))
        mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(verts,[],faces); mesh.update()
        obj=bpy.data.objects.new(name,mesh); scene.collection.objects.link(obj); obj.data.materials.append(mat)
        for p in obj.data.polygons:p.use_smooth=True
        return obj

    def fuse(objects,name,voxel,smooth_factor=.55,smooth_iterations=2):
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects: obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.object.join()
        obj=bpy.context.object; obj.name=name
        remesh=obj.modifiers.new("IntegratedSurface","REMESH")
        remesh.mode="VOXEL"; remesh.voxel_size=voxel
        bpy.ops.object.modifier_apply(modifier=remesh.name)
        smooth=obj.modifiers.new("SurfacePolish","SMOOTH")
        smooth.factor=smooth_factor; smooth.iterations=smooth_iterations
        bpy.ops.object.modifier_apply(modifier=smooth.name)
        for poly in obj.data.polygons:poly.use_smooth=True
        return obj

    # White short-sleeved streetwear tee with a shaped waist and sloped shoulder line.
    shirt_obj=loft_rings("LAM_WHITE_TEE",[
        (3.36,.345,.190,0),(3.40,.370,.202,0),(3.48,.385,.210,0),
        (3.58,.392,.214,0),(3.72,.400,.218,0),(3.86,.415,.222,0),
        (3.98,.435,.225,0),(4.08,.448,.224,0),(4.16,.438,.215,0),
        (4.22,.402,.202,0),(4.27,.315,.170,0),(4.30,.185,.132,0)
    ],shirt,64)

    # Build the pelvis and two tapered pant legs, then voxel-fuse them into one garment.
    pelvis=loft_rings("PANTS_PELVIS",[
        (2.48,.315,.185,0),(2.60,.350,.205,0),(2.74,.375,.216,0),
        (2.88,.382,.220,0),(3.00,.380,.220,0),(3.12,.372,.216,0),
        (3.20,.350,.204,0),(3.25,.315,.190,0)
    ],pants,56)
    pant_parts=[pelvis]
    for sign,side in [(-1,"L"),(1,"R")]:
        pant_parts.append(tube_path("PANTS_LEG_"+side,[
            (sign*.195,0,.28,.078,.085),(sign*.198,0,.36,.082,.092),
            (sign*.200,0,.48,.088,.100),(sign*.205,0,.68,.098,.108),
            (sign*.205,0,.92,.108,.118),(sign*.207,0,1.18,.119,.128),
            (sign*.207,0,1.43,.132,.138),(sign*.205,0,1.64,.142,.148),
            (sign*.203,0,1.78,.148,.153),(sign*.200,0,1.96,.154,.158),
            (sign*.198,0,2.18,.162,.165),(sign*.195,0,2.39,.170,.172),
            (sign*.192,0,2.58,.178,.178),(sign*.190,0,2.73,.183,.181)
        ],pants,32))
    fused_pants=fuse(pant_parts,"LAM_CONTINUOUS_BLACK_PANTS",.012,.55,2)

    # Shorter/slimmer neck, partly hidden by the collar and lower head.
    neck=tube_path("LAM_NECK",[
        (0,0,4.36,.112,.105),(0,0,4.43,.108,.103),(0,0,4.53,.103,.100),
        (0,0,4.64,.104,.101),(0,0,4.75,.112,.108)
    ],skin,40)

    # Tapered jaw and low-relief cheek contours sculpted into the head surface.
    head=uv("LAM_HEAD_BASE",(0,-.005,5.025),(.272,.235,.348),skin,96,64)
    for vert in head.data.vertices:
        zn=vert.co.z/.348
        if zn < -.03:
            t=min(1.0,max(0.0,(-zn-.03)/.97))
            vert.co.x *= (1.0-.24*t)
            vert.co.y *= (1.0-.05*t)
        if vert.co.y < 0:
            vert.co.y *= .94
            frontness=min(1.0,max(0.0,(-vert.co.y-.095)/.105))
            zlocal=vert.co.z
            bridge=.012*math.exp(-((vert.co.x/.040)**2)-(((zlocal+.012)/.105)**2))
            tip=.025*math.exp(-((vert.co.x/.043)**2)-(((zlocal+.044)/.034)**2))
            cheek=.007*math.exp(-(((abs(vert.co.x)-.142)/.068)**2)-(((zlocal+.060)/.058)**2))
            vert.co.y -= frontness*(bridge+tip+cheek)
    head.data.update()
    for poly in head.data.polygons:poly.use_smooth=True

    # Fuse a tapered nose bridge and tip directly into the head skin; no separate nose sphere.
    nose=loft_rings("NOSE_RELIEF_TO_FUSE",[
        (4.965,.014,.014,-.244),(4.978,.022,.021,-.253),
        (4.995,.024,.026,-.258),(5.012,.018,.021,-.250),
        (5.045,.012,.014,-.238)
    ],skin,32)
    fused_head=fuse([head,nose],"LAM_HEAD_INTEGRATED_NOSE",.006,.30,1)

    # Ears are small and partly embedded in the head silhouette.
    uv("EAR_L",(-.266,-.002,5.015),(.036,.047,.073),skin,32,24)
    uv("EAR_R",(.266,-.002,5.015),(.036,.047,.073),skin,32,24)

    # Inset eyes, brown irises, dark pupils and small highlights.
    for x,side in [(-.104,"L"),(.104,"R")]:
        uv("EYE_WHITE_"+side,(x,-.217,5.080),(.046,.017,.029),white,40,28)
        uv("IRIS_"+side,(x,-.235,5.079),(.020,.007,.020),iris,32,24)
        uv("PUPIL_"+side,(x,-.241,5.079),(.009,.0035,.011),pupil,24,18)
        uv("EYE_GLINT_"+side,(x-.005,-.244,5.086),(.0038,.002,.0042),white,20,12)
        uv("BROW_"+side,(x,-.219,5.137),(.058,.008,.011),hair,32,20)
    uv("LAM_LIPS",(0,-.232,4.905),(.047,.006,.010),lipmat,40,24)

    # Hair cap and back/side locks are fused into one continuous black hair mass.
    hair_cap=loft_rings("HAIR_CAP_SURFACE",[
        (5.16,.277,.252,.012),(5.205,.292,.266,.012),
        (5.27,.286,.258,.012),(5.34,.255,.235,.012),
        (5.41,.202,.190,.012),(5.465,.125,.122,.012),
        (5.495,.020,.020,.012)
    ],hair,64)
    hair_parts=[hair_cap]
    hair_parts.append(uv("HAIR_BACK_MASS",(0,.105,4.925),(.285,.142,.365),hair,48,32))
    hair_parts.append(uv("HAIR_LOCK_L",(-.245,.015,4.955),(.052,.083,.245),hair,36,24))
    hair_parts.append(uv("HAIR_LOCK_R",(.245,.015,4.955),(.052,.083,.245),hair,36,24))
    fused_hair=fuse(hair_parts,"LAM_CONTINUOUS_HAIR",.012,.48,2)

    # Slim, tapered arm lofts; elbow transitions are built into each surface.
    arm_parts=[]
    for sign,side in [(-1,"L"),(1,"R")]:
        arm_parts.append(tube_path("ARM_SKIN_"+side,[
            (sign*.385,0,4.19,.085,.095),(sign*.425,-.002,4.10,.103,.108),
            (sign*.465,-.006,3.99,.105,.108),(sign*.492,-.010,3.84,.094,.099),
            (sign*.510,-.015,3.69,.085,.090),(sign*.525,-.020,3.55,.075,.080),
            (sign*.530,-.025,3.40,.070,.076),(sign*.528,-.030,3.26,.065,.070),
            (sign*.525,-.035,3.17,.061,.065)
        ],skin,32))
        arm_parts.append(uv("PALM_"+side,(sign*.525,-.040,3.105),(.061,.052,.090),skin,32,24))
        for finger in range(4):
            x=sign*(.488+finger*.025)
            z0=3.085-(.010 if finger in (0,3) else 0)
            arm_parts.append(capsule_piece("FINGER_"+side+str(finger),
                (x,-.047,z0),(x+sign*.002,-.049,z0-.075),.013,skin,.013))
        arm_parts.append(capsule_piece("THUMB_"+side,
            (sign*.478,-.043,3.12),(sign*.455,-.051,3.065),.018,skin,.018))
    fused_arms=fuse(arm_parts,"LAM_CONTINUOUS_ARM_AND_HAND_FORMS",.010,.48,2)

    # White sneakers with a subtle dark sole and a fuller upper.
    for sign,side in [(-1,"L"),(1,"R")]:
        uv("SNEAKER_SOLE_"+side,(sign*.205,-.075,.085),(.116,.184,.042),sole,40,24)
        uv("SNEAKER_UPPER_"+side,(sign*.205,-.080,.135),(.112,.180,.065),shoes,40,28)
        uv("SNEAKER_TONGUE_"+side,(sign*.205,-.145,.167),(.055,.085,.030),white,32,20)

    # Subtle waistband visible below the tee; the chosen styling stays black and white.
    waistband=loft_rings("PANTS_WAISTBAND",[
        (3.14,.369,.215,0),(3.19,.359,.208,0),(3.225,.337,.198,0)
    ],pants,56)

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
    # V388 diagnostic views: face close-up from front and profile, to reveal feature placement.
    face_target=(0,0,1.455)
    def face_camera(name,loc,ortho):
        d=bpy.data.cameras.new(name); cc=bpy.data.objects.new(name,d); scene.collection.objects.link(cc); cc.location=loc
        cc.rotation_euler=(Vector(face_target)-cc.location).to_track_quat("-Z","Y").to_euler()
        d.type="ORTHO"; d.ortho_scale=ortho; return cc
    face_front=face_camera("FaceCloseupFront",(0,-2.5,1.455),.58); scene.camera=face_front
    scene.render.resolution_x=900; scene.render.resolution_y=900
    scene.render.filepath=os.path.join(out,"coherent-body-face-front.png"); bpy.ops.render.render(write_still=True)
    face_profile=face_camera("FaceCloseupProfile",(2.5,0,1.455),.58); scene.camera=face_profile
    scene.render.filepath=os.path.join(out,"coherent-body-face-profile.png"); bpy.ops.render.render(write_still=True)
    scene.render.resolution_x=900; scene.render.resolution_y=1100
    glb=os.path.join(out,"lam-coherent-body-candidate.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in scene.objects:
        if o.type in {"MESH","ARMATURE"}:o.select_set(True)
    bpy.context.view_layer.objects.active=shirt_obj
    bpy.ops.export_scene.gltf(filepath=glb,export_format="GLB",use_selection=True)
    report={"status":"EXPERIMENTAL_CANDIDATE_NOT_APPROVED","purpose":"Procedural stylized anatomy prototype; separate from production GLB","candidate":os.path.basename(glb),"bytes":os.path.getsize(glb),"mesh_count":sum(o.type=="MESH" for o in figure_meshes),"measured_bounds_m":bounds,"height_error_m":abs(bounds["size"][2]-1.60),"renders":["coherent-body-front.png","coherent-body-three-quarter.png","coherent-body-face-front.png","coherent-body-face-profile.png"],"warnings":["Not a photorealistic final avatar","No armature or facial morphs transferred","Figure normalized to approximately 1.60 m","Arms fused as experimental skin surfaces to reduce segment seams","Must visually inspect and test in web viewer before any promotion","Second silhouette refinement: softened waist-to-hip transition, reduced shoulder shelf and smaller feet/knees","Integrated full-form pass: shaped white tee, continuous black pants, tapered limbs, head-integrated nose and cheek relief, inset eyes, fused hair and white sneakers; visual review required","Experimental candidate only; no production rig or facial morph transfer; must pass front/profile/three-quarter, pose/deformation and web/mobile acceptance gates before production consideration"]}
    with open(os.path.join(out,"coherent-body-candidate.json"),"w",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print("COHERENT_BODY_CANDIDATE="+json.dumps(report,ensure_ascii=False))
    assert os.path.getsize(glb)>1024
    assert abs(bounds["size"][2]-1.60)<0.03, "Candidate height is outside 1.60m tolerance"
if __name__=="__main__":
    try:main()
    except Exception:traceback.print_exc();raise
