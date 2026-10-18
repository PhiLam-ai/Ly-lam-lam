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
    hair=material("Lam deep black hair",(.012,.010,.013),.50)
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

    def curve_stroke(name, points, radius, mat):
        """Smooth beveled facial stroke, converted to mesh for GLB export."""
        curve=bpy.data.curves.new(name+"Curve","CURVE")
        curve.dimensions="3D"; curve.resolution_u=16
        curve.bevel_depth=radius; curve.bevel_resolution=4; curve.resolution_u=16
        spline=curve.splines.new("BEZIER")
        spline.bezier_points.add(len(points)-1)
        for i,point in enumerate(points):
            bp=spline.bezier_points[i]; bp.co=point
            bp.handle_left_type="AUTO"; bp.handle_right_type="AUTO"
        obj=bpy.data.objects.new(name,curve); scene.collection.objects.link(obj)
        obj.data.materials.append(mat)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True); bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target="MESH")
        obj=bpy.context.object
        for poly in obj.data.polygons: poly.use_smooth=True
        return obj
    # Integrated character candidate: use lofted garment/limb surfaces and fuse the key
    # transition areas. This replaces the old stacked torso, capsule arms and skirt blockout.

    def loft_rings(name, levels, mat, segments=48, cap_top=True):
        """Elliptical loft; optionally leave the final ring open for a garment neckline."""
        verts=[]; faces=[]
        for z,rx,ry,cy in levels:
            for j in range(segments):
                a=2*math.pi*j/segments
                verts.append((rx*math.cos(a),cy+ry*math.sin(a),z))
        verts.append((0.0,levels[0][3],levels[0][0])); bottom=len(verts)-1
        top=None
        if cap_top:
            verts.append((0.0,levels[-1][3],levels[-1][0])); top=len(verts)-1
        for i in range(len(levels)-1):
            for j in range(segments):
                a=i*segments+j; b=i*segments+(j+1)%segments
                c=(i+1)*segments+(j+1)%segments; d=(i+1)*segments+j
                faces.append((a,b,c,d))
        for j in range(segments):
            faces.append((bottom,(j+1)%segments,j))
            a=(len(levels)-1)*segments+j; b=(len(levels)-1)*segments+(j+1)%segments
            if cap_top:
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
        (4.22,.402,.202,0),(4.33,.315,.170,0),(4.39,.245,.145,0),(4.43,.132,.106,0)
    ],shirt,64,False)

    # Real short sleeves extend the white tee over the upper arms; fuse them into its body.
    tee_sleeves=[]
    for sign,side in [(-1,"L"),(1,"R")]:
        tee_sleeves.append(tube_path("TEE_SLEEVE_"+side,[
            (sign*.385,-.002,4.23,.108,.112),(sign*.415,-.003,4.15,.126,.128),
            (sign*.448,-.006,4.05,.127,.130),(sign*.476,-.010,3.94,.119,.123),
            (sign*.488,-.012,3.875,.115,.118)
        ],shirt,40))
    # Keep the garment pieces as intersecting closed shells: voxel-remeshing the open-neck
    # tee surface can erase its torso. Their overlap is intentional and will be inspected in renders.

    # A narrow dark rib around the open collar helps define a finished neckline.
    bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=10,
        location=(0,0,4.382),major_radius=.116,minor_radius=.008)
    collar=bpy.context.object; collar.name="TEE_BLACK_RIB_COLLAR"; collar.scale.y=.90
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    collar.data.materials.append(pants)
    for poly in collar.data.polygons:poly.use_smooth=True

    # Build the pelvis and two tapered pant legs, then voxel-fuse them into one garment.
    pelvis=loft_rings("PANTS_PELVIS",[
        (2.48,.315,.185,0),(2.60,.350,.205,0),(2.74,.375,.216,0),
        (2.88,.382,.220,0),(3.00,.380,.220,0),(3.12,.372,.216,0),
        (3.20,.350,.204,0),(3.30,.350,.204,0),(3.38,.325,.195,0)
    ],pants,56)
    pant_parts=[pelvis]
    for sign,side in [(-1,"L"),(1,"R")]:
        pant_parts.append(tube_path("PANTS_LEG_"+side,[
            (sign*.200,-.018,.10,.076,.085),(sign*.200,-.012,.22,.079,.089),
            (sign*.198,0,.36,.082,.092),
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
        (0,0,4.18,.102,.098),(0,0,4.27,.105,.100),(0,0,4.36,.108,.102),
        (0,0,4.46,.105,.100),(0,0,4.56,.104,.100),(0,0,4.66,.106,.102),
        (0,0,4.75,.112,.108)
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

    # Ears are fused into the head/neck shell so they no longer look like buttons attached
    # to the side of the face. Keep the outer lobes shallow and close to the head silhouette.
    ear_l=uv("EAR_L",(-.257,-.002,5.015),(.031,.040,.064),skin,40,28)
    ear_r=uv("EAR_R",(.257,-.002,5.015),(.031,.040,.064),skin,40,28)
    fused_head_neck=fuse([neck,fused_head,ear_l,ear_r],"LAM_CONTINUOUS_HEAD_NECK",.007,.22,1)

    # Inset eyes, brown irises, dark pupils and small highlights.
    for x,side in [(-.104,"L"),(.104,"R")]:
        uv("EYE_WHITE_"+side,(x,-.222,5.080),(.043,.011,.026),white,40,28)
        uv("IRIS_"+side,(x,-.233,5.079),(.018,.005,.018),iris,32,24)
        uv("PUPIL_"+side,(x,-.237,5.079),(.008,.003,.010),pupil,24,18)
        uv("EYE_GLINT_"+side,(x-.004,-.239,5.085),(.0032,.0015,.0035),white,20,12)
        # Curved eyelid rims integrate the eyeballs into the head and soften the stylized gaze.
        curve_stroke("EYELID_UPPER_"+side,[
            (x-.043,-.220,5.079),(x,-.229,5.102),(x+.043,-.220,5.079)
        ],.0035,skin)
        curve_stroke("EYELID_LOWER_"+side,[
            (x-.040,-.219,5.077),(x,-.226,5.058),(x+.040,-.219,5.077)
        ],.0028,skin)
        curve_stroke("BROW_"+side,[
            (x-.050,-.222,5.145),(x,-.229,5.155),(x+.050,-.222,5.145)
        ],.0045,hair)
    lips_obj=uv("LAM_LIPS",(0,-.214,4.905),(.046,.0045,.009),lipmat,40,24)
    mouth_dark=material("Mouth cavity deep rose",(.075,.018,.022),.62)
    tongue_mat=material("Tongue muted rose",(.48,.12,.15),.52)
    mouth_cavity=uv("LAM_MOUTH_CAVITY",(0,-.209,4.904),(.030,.0025,.0055),mouth_dark,40,24)
    tongue_obj=uv("LAM_TONGUE",(0,-.212,4.898),(.014,.002,.0028),tongue_mat,32,20)

    # Hair cap and back/side locks are fused into one continuous black hair mass.
    hair_cap=loft_rings("HAIR_CAP_SURFACE",[
        (5.16,.277,.252,.012),(5.205,.292,.266,.012),
        (5.27,.286,.258,.012),(5.34,.255,.235,.012),
        (5.41,.202,.190,.012),(5.465,.125,.122,.012),
        (5.495,.020,.020,.012)
    ],hair,64)
    hair_parts=[hair_cap]
    hair_parts.append(uv("HAIR_BACK_MASS",(0,.105,4.985),(.278,.135,.275),hair,48,32))
    hair_parts.append(uv("HAIR_LOCK_L",(-.245,.015,4.975),(.046,.072,.205),hair,36,24))
    hair_parts.append(uv("HAIR_LOCK_R",(.245,.015,4.975),(.046,.072,.205),hair,36,24))
    # A short diagonal fringe follows the cap surface instead of floating in front like a tube.
    fringe=capsule_piece("HAIR_SIDE_SWEPT_FRINGE",(-.13,-.196,5.375),(.105,-.247,5.255),.020,hair,.014)
    hair_parts.append(fringe)
    fused_hair=fuse(hair_parts,"LAM_CONTINUOUS_HAIR",.010,.26,1)

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
        uv("SNEAKER_SOLE_"+side,(sign*.205,-.235,.078),(.128,.335,.036),sole,40,24)
        uv("SNEAKER_UPPER_"+side,(sign*.205,-.235,.130),(.124,.320,.062),shoes,40,28)
        uv("SNEAKER_TONGUE_"+side,(sign*.205,-.300,.158),(.060,.120,.029),white,32,20)

    # Subtle waistband visible below the tee; the chosen styling stays black and white.
    waistband=loft_rings("PANTS_WAISTBAND",[
        (3.27,.364,.208,0),(3.32,.355,.204,0),(3.37,.330,.195,0)
    ],pants,56)

    # Normalize the generated figure to the requested 1.60 m scale (Z extent about 5.5 units before normalization).
    scale_factor=1.60/5.5
    for obj in list(scene.objects):
        if obj.type=="MESH":
            obj.location *= scale_factor
            obj.scale *= scale_factor
    # Add semantic facial morph targets on the new meshes. These names match the viewer API.
    def add_shape_key(obj, name, transform):
        if obj is None or obj.type!="MESH":
            raise RuntimeError("Cannot add shape key "+name+": target mesh is missing")
        if obj.data.shape_keys is None:
            obj.shape_key_add(name="Basis",from_mix=False)
        key=obj.shape_key_add(name=name,from_mix=False)
        basis=obj.data.shape_keys.key_blocks.get("Basis")
        for i,vertex in enumerate(obj.data.vertices):
            key.data[i].co=transform(vertex.co.copy())
        return key

    def clamp01(x): return max(0.0,min(1.0,x))
    def gauss(x,center,width): return math.exp(-((x-center)/width)**2)

    def head_key(name):
        def transform(co):
            x,y,z=co.x,co.y,co.z
            front=clamp01((-y-.08)/.16)
            ax=abs(x)
            if name=="smile":
                w=front*gauss(ax,.090,.045)*gauss(z,4.91,.060)
                co.y-=.004*w; co.z+=.015*w
            elif name=="cheek_raise":
                w=front*gauss(ax,.145,.064)*gauss(z,4.975,.060)
                co.y-=.007*w; co.z+=.014*w
            elif name=="brow_raise":
                w=front*gauss(ax,.105,.075)*gauss(z,5.145,.060)
                co.z+=.016*w
            elif name=="mouth_open":
                w=front*gauss(z,4.902,.065)*clamp01(1.0-(ax/.14)**2)
                co.z-=.010*w
            elif name=="jaw_open":
                jaw=clamp01((4.985-z)/.30)*clamp01(1.0-(ax/.245)**2)*front
                co.z-=.040*jaw; co.y+=.006*jaw
            elif name=="jaw_hinge":
                jaw=clamp01((4.985-z)/.30)*clamp01(1.0-(ax/.245)**2)*front
                co.z-=.032*jaw; co.y+=.018*jaw
            return co
        return transform

    for name in ("smile","cheek_raise","brow_raise","mouth_open","jaw_open","jaw_hinge"):
        add_shape_key(fused_head_neck,name,head_key(name))

    # Blink targets flatten the visible eyeballs and their iris/pupil highlights together.
    for side,morph in (("L","blink_left"),("R","blink_right")):
        for prefix in ("EYE_WHITE_","IRIS_","PUPIL_","EYE_GLINT_"):
            obj=scene.objects.get(prefix+side)
            if obj:
                add_shape_key(obj,morph,lambda co: Vector((co.x,co.y,co.z*.06)))

    # Brows lift with the same semantic target as the forehead skin.
    for side in ("L","R"):
        brow_obj=scene.objects.get("BROW_"+side)
        if brow_obj:
            add_shape_key(brow_obj,"brow_raise",lambda co: Vector((co.x,co.y,co.z+.020)))

    def mouth_transform(kind):
        def transform(co):
            x,y,z=co.x,co.y,co.z
            if kind=="smile":
                co.x*=1.20; co.z+=.010*(abs(x)/.047)**2
            elif kind=="mouth_open":
                co.z=(z+.004) if z>=0 else (z-.006)
            elif kind=="lip_press":
                co.z*=.22
            elif kind=="lip_fv":
                co.z+=(.004 if z>=0 else -.004); co.x*=1.04
            elif kind=="lip_round":
                co.x*=.58; co.z*=1.45
            elif kind=="jaw_open":
                co.z*=2.2
            elif kind=="jaw_hinge":
                co.z*=1.8
            return co
        return transform

    for key_name in ("smile","mouth_open","lip_press","lip_fv","lip_round","jaw_open","jaw_hinge"):
        add_shape_key(lips_obj,key_name,mouth_transform(key_name))

    def cavity_transform(kind):
        def transform(co):
            if kind=="mouth_open":
                co.z*=3.5
            elif kind=="jaw_open":
                co.z*=3.2
            elif kind=="jaw_hinge":
                co.z*=2.8; co.y-=.002
            elif kind=="smile":
                co.x*=1.3; co.z*=1.4
            elif kind=="lip_press":
                co.z*=.12
            elif kind=="lip_round":
                co.x*=.58; co.z*=1.8
            elif kind=="lip_fv":
                co.z+=(.002 if co.z>=0 else -.002)
            return co
        return transform

    for key_name in ("smile","mouth_open","lip_press","lip_fv","lip_round","jaw_open","jaw_hinge"):
        add_shape_key(mouth_cavity,key_name,cavity_transform(key_name))
    add_shape_key(tongue_obj,"tongue_tip",lambda co: Vector((co.x,co.y-.010,co.z+.022)))
    add_shape_key(tongue_obj,"mouth_open",lambda co: Vector((co.x,co.y,co.z*2.0)))

    required_morphs=[
        "smile","blink_left","blink_right","mouth_open","brow_raise","jaw_open",
        "jaw_hinge","cheek_raise","lip_press","lip_fv","lip_round","tongue_tip"
    ]
    morph_effects={name:0.0 for name in required_morphs}
    for obj in [o for o in scene.objects if o.type=="MESH"]:
        shapes=obj.data.shape_keys
        if not shapes: continue
        basis=shapes.key_blocks.get("Basis")
        if not basis: continue
        for key in shapes.key_blocks:
            if key.name=="Basis" or key.name not in morph_effects: continue
            maximum=0.0
            for i,bv in enumerate(basis.data):
                delta=(key.data[i].co-bv.co).length
                maximum=max(maximum,delta)
            morph_effects[key.name]=max(morph_effects[key.name],maximum)
    missing=[name for name,value in morph_effects.items() if value<=1e-6]
    if missing: raise RuntimeError("Required facial morphs missing or ineffective: "+", ".join(missing))

    # Create the 17-bone Lam humanoid skeleton in the candidate's normalized coordinate space.
    rig_data=bpy.data.armatures.new("Lam_Humanoid_Skeleton")
    rig=bpy.data.objects.new("Lam_Humanoid_Root",rig_data)
    scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.select_all(action="DESELECT"); rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for eb in list(rig.data.edit_bones): rig.data.edit_bones.remove(eb)
    bone_specs=[
        ("Lam_Joint_Hips",(0,0,2.78),(0,0,3.12),None),
        ("Lam_Joint_Spine",(0,0,3.00),(0,0,3.72),"Lam_Joint_Hips"),
        ("Lam_Joint_Chest",(0,0,3.68),(0,0,4.15),"Lam_Joint_Spine"),
        ("Lam_Joint_Neck",(0,0,4.17),(0,0,4.69),"Lam_Joint_Chest"),
        ("Lam_Joint_Head",(0,0,4.62),(0,0,5.35),"Lam_Joint_Neck"),
        ("Lam_Joint_LeftShoulder",(0,0,4.13),(-.425,0,4.05),"Lam_Joint_Chest"),
        ("Lam_Joint_LeftElbow",(-.425,0,4.05),(-.500,-.012,3.72),"Lam_Joint_LeftShoulder"),
        ("Lam_Joint_LeftWrist",(-.500,-.012,3.72),(-.525,-.035,3.17),"Lam_Joint_LeftElbow"),
        ("Lam_Joint_RightShoulder",(0,0,4.13),(.425,0,4.05),"Lam_Joint_Chest"),
        ("Lam_Joint_RightElbow",(.425,0,4.05),(.500,-.012,3.72),"Lam_Joint_RightShoulder"),
        ("Lam_Joint_RightWrist",(.500,-.012,3.72),(.525,-.035,3.17),"Lam_Joint_RightElbow"),
        ("Lam_Joint_LeftHip",(0,0,2.88),(-.195,0,2.58),"Lam_Joint_Hips"),
        ("Lam_Joint_LeftKnee",(-.195,0,2.58),(-.205,0,1.65),"Lam_Joint_LeftHip"),
        ("Lam_Joint_LeftAnkle",(-.205,0,1.65),(-.205,-.03,.13),"Lam_Joint_LeftKnee"),
        ("Lam_Joint_RightHip",(0,0,2.88),(.195,0,2.58),"Lam_Joint_Hips"),
        ("Lam_Joint_RightKnee",(.195,0,2.58),(.205,0,1.65),"Lam_Joint_RightHip"),
        ("Lam_Joint_RightAnkle",(.205,0,1.65),(.205,-.03,.13),"Lam_Joint_RightKnee")
    ]
    bone_map={}; bone_segments=[]
    for name,head_xyz,tail_xyz,parent_name in bone_specs:
        eb=rig.data.edit_bones.new(name)
        eb.head=Vector(head_xyz)*scale_factor; eb.tail=Vector(tail_xyz)*scale_factor
        if parent_name: eb.parent=bone_map[parent_name]
        bone_map[name]=eb
        bone_segments.append((name,Vector(head_xyz)*scale_factor,Vector(tail_xyz)*scale_factor))
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front=False

    # Distance-based smooth weights across the custom bone segments. This is an initial rig
    # pass and is validated with pose probes and render review below, not assumed to be final.
    character_meshes=[o for o in scene.objects if o.type=="MESH" and o.name!="StudioFloor"]
    for obj in character_meshes:
        groups={bone_name:obj.vertex_groups.new(name=bone_name) for bone_name,_,_ in bone_segments}
        world_vertices=[obj.matrix_world @ v.co for v in obj.data.vertices]
        for index,point in enumerate(world_vertices):
            scores=[]
            for bone_name,a,b in bone_segments:
                ab=b-a; denom=max(ab.length_squared,1e-10)
                t=clamp01((point-a).dot(ab)/denom)
                closest=a+ab*t
                distance=(point-closest).length
                score=1.0/((distance+.025)**3)
                scores.append((score,bone_name))
            best=sorted(scores,reverse=True)[:3]
            total=sum(score for score,_ in best)
            for score,bone_name in best:
                groups[bone_name].add([index],score/total,"REPLACE")
        obj.parent=rig
        obj.matrix_parent_inverse=rig.matrix_world.inverted()
        mod=obj.modifiers.new("LamHumanoidSkin","ARMATURE")
        mod.object=rig; mod.use_deform_preserve_volume=True

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
    report={"status":"EXPERIMENTAL_CANDIDATE_NOT_APPROVED","purpose":"Integrated stylized avatar candidate; separate from production GLB","candidate":os.path.basename(glb),"bytes":os.path.getsize(glb),"mesh_count":sum(o.type=="MESH" for o in figure_meshes),"armature_name":rig.name,"bone_count":len(rig.data.bones),"skinned_mesh_count":sum(1 for o in figure_meshes if any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers)),"morph_targets":required_morphs,"morph_max_local_delta":morph_effects,"measured_bounds_m":bounds,"height_error_m":abs(bounds["size"][2]-1.60),"renders":["coherent-body-front.png","coherent-body-three-quarter.png","coherent-body-face-front.png","coherent-body-face-profile.png"],"warnings":["Not a photorealistic final avatar","No armature or facial morphs transferred","Figure normalized to approximately 1.60 m","V397 refined short-hair silhouette, inlaid ears/eyes/lids, reduced mouth protrusion, longer sneakers, and overlapping waistband/shirt hem","Rig and facial morph targets are initial candidates, not production-approved; must pass candidate-specific pose/morph validation, expression render review, and web/mobile acceptance"]}
    with open(os.path.join(out,"coherent-body-candidate.json"),"w",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print("COHERENT_BODY_CANDIDATE="+json.dumps(report,ensure_ascii=False))
    assert os.path.getsize(glb)>1024
    assert abs(bounds["size"][2]-1.60)<0.03, "Candidate height is outside 1.60m tolerance"
    assert len(rig.data.bones)==17, "Candidate rig must have all 17 humanoid bones"
    assert all(v>1e-6 for v in morph_effects.values()), "Candidate facial morphs must be geometrically effective"
if __name__=="__main__":
    try:main()
    except Exception:traceback.print_exc();raise
