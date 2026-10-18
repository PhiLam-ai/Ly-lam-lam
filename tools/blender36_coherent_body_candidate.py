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
    shirt=material("Lam deep teal fitted crop top",(.025,.095,.105),.48)
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

    def hair_ribbon(name, points, widths, thickness, mat, segments=16):
        """Create a broad, softly rounded tapered hair lock swept along a curved centerline."""
        centers=[Vector(p) for p in points]
        if len(centers)<3 or len(widths)!=len(centers):
            raise ValueError("hair_ribbon requires >=3 points and one width per point")
        verts=[]; faces=[]
        for i,center in enumerate(centers):
            tangent=(centers[min(i+1,len(centers)-1)]-centers[max(i-1,0)]).normalized()
            lateral=Vector((tangent.z,0.0,-tangent.x))
            if lateral.length<1e-6:
                lateral=Vector((1.0,0.0,0.0))
            lateral.normalize()
            depth=tangent.cross(lateral)
            if depth.length<1e-6:
                depth=Vector((0.0,1.0,0.0))
            depth.normalize()
            for j in range(segments):
                a=2.0*math.pi*j/segments
                p=center+lateral*(widths[i]*math.cos(a))+depth*(thickness*math.sin(a))
                verts.append(tuple(p))
        for i in range(len(centers)-1):
            for j in range(segments):
                a=i*segments+j; b=i*segments+(j+1)%segments
                c=(i+1)*segments+(j+1)%segments; d=(i+1)*segments+j
                faces.append((a,b,d,c))
        faces.append(tuple(reversed(tuple(range(segments)))))
        faces.append(tuple((len(centers)-1)*segments+j for j in range(segments)))
        mesh=bpy.data.meshes.new(name+"Mesh")
        mesh.from_pydata(verts,[],faces); mesh.update()
        obj=bpy.data.objects.new(name,mesh); scene.collection.objects.link(obj)
        obj.data.materials.append(mat)
        for poly in obj.data.polygons: poly.use_smooth=True
        return obj

    # Reference-led everyday outfit: fitted dark-teal crop tank, not the earlier white tee blockout.
    shirt_obj=loft_rings("LAM_DARK_TEAL_CROP_TOP",[
        (3.46,.300,.176,0),(3.51,.330,.190,0),(3.60,.350,.198,0),
        (3.72,.365,.202,0),(3.84,.370,.204,0),(3.95,.365,.198,0),
        (4.05,.350,.186,0),(4.13,.323,.166,0),(4.20,.275,.137,0),
        (4.25,.215,.116,0)
    ],shirt,64,False)
    # Narrow shoulder straps follow the reference outfit and connect the neckline toward the shoulders.
    for sign,side in [(-1,"L"),(1,"R")]:
        curve_stroke("CROP_TOP_STRAP_"+side,[
            (sign*.225,-.105,4.105),(sign*.205,-.137,4.19),
            (sign*.167,-.123,4.285),(sign*.142,-.096,4.345)
        ],.014,shirt)

    # A narrow dark rib around the open collar helps define a finished neckline.
    bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=10,
        location=(0,0,4.315),major_radius=.108,minor_radius=.006)
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
    head=uv("LAM_HEAD_BASE",(0,-.005,5.025),(.278,.232,.342),skin,96,64)
    for vert in head.data.vertices:
        zn=vert.co.z/.342
        if zn < -.03:
            t=min(1.0,max(0.0,(-zn-.03)/.97))
            vert.co.x *= (1.0-.31*t)  # V403: more reference-like cheek-to-chin taper
            vert.co.y *= (1.0-.05*t)
        if vert.co.y < 0:
            vert.co.y *= .96
            frontness=min(1.0,max(0.0,(-vert.co.y-.095)/.105))
            zlocal=vert.co.z
            bridge=.010*math.exp(-((vert.co.x/.040)**2)-(((zlocal+.012)/.105)**2))
            tip=.018*math.exp(-((vert.co.x/.038)**2)-(((zlocal+.044)/.034)**2))
            cheek=.007*math.exp(-(((abs(vert.co.x)-.142)/.068)**2)-(((zlocal+.060)/.058)**2))
            vert.co.y -= frontness*(bridge+tip+cheek)
    head.data.update()
    for poly in head.data.polygons:poly.use_smooth=True

    # Fuse a tapered nose bridge and tip directly into the head skin; no separate nose sphere.
    nose=loft_rings("NOSE_RELIEF_TO_FUSE",[
        (4.966,.012,.012,-.241),(4.979,.018,.017,-.247),
        (4.994,.020,.021,-.252),(5.010,.016,.017,-.247),
        (5.040,.010,.012,-.239)
    ],skin,32)
    fused_head=fuse([head,nose],"LAM_HEAD_INTEGRATED_NOSE",.006,.30,1)

    # Ears are fused into the head/neck shell so they no longer look like buttons attached
    # to the side of the face. Keep the outer lobes shallow and close to the head silhouette.
    ear_l=uv("EAR_L",(-.257,-.002,5.015),(.025,.029,.049),skin,40,28)
    ear_r=uv("EAR_R",(.257,-.002,5.015),(.028,.034,.056),skin,40,28)
    fused_head_neck=fuse([neck,fused_head,ear_l,ear_r],"LAM_CONTINUOUS_HEAD_NECK",.007,.22,1)

    # Inset eyes, brown irises, dark pupils and small highlights.
    for x,side in [(-.104,"L"),(.104,"R")]:
        uv("EYE_WHITE_"+side,(x,-.219,5.080),(.030,.0048,.0115),white,40,28)  # V403: flatter almond-like eye opening
        uv("IRIS_"+side,(x,-.225,5.079),(.0105,.0022,.0095),iris,32,24)
        uv("PUPIL_"+side,(x,-.228,5.079),(.0046,.0016,.0060),pupil,24,18)
        uv("EYE_GLINT_"+side,(x-.004,-.233,5.085),(.0025,.0013,.0028),white,20,12)
        # Curved eyelid rims integrate the eyeballs into the head and soften the stylized gaze.
        curve_stroke("EYELID_UPPER_"+side,[
            (x-.043,-.220,5.079),(x,-.229,5.102),(x+.043,-.220,5.079)
        ],.0035,skin)
        curve_stroke("EYELID_LOWER_"+side,[
            (x-.040,-.219,5.077),(x,-.226,5.058),(x+.040,-.219,5.077)
        ],.0028,skin)
        curve_stroke("BROW_"+side,[
            (x-.050,-.211,5.128),(x,-.218,5.140),(x+.050,-.211,5.128)
        ],.0055,hair)
    lips_obj=uv("LAM_LIPS",(0,-.215,4.905),(.066,.0060,.013),lipmat,48,28)  # V403: fuller, softer lip volume
    mouth_dark=material("Mouth cavity deep rose",(.075,.018,.022),.62)
    tongue_mat=material("Tongue muted rose",(.48,.12,.15),.52)
    mouth_cavity=uv("LAM_MOUTH_CAVITY",(0,-.209,4.904),(.038,.0035,.009),mouth_dark,40,24)
    tongue_obj=uv("LAM_TONGUE",(0,-.212,4.898),(.012,.0025,.0025),tongue_mat,32,20)

    # Hair cap and back/side locks are fused into one continuous black hair mass.
    hair_cap=loft_rings("HAIR_CAP_SURFACE",[
        (5.235,.266,.232,.018),(5.270,.286,.248,.018),
        (5.320,.274,.240,.018),(5.370,.240,.214,.016),
        (5.425,.183,.172,.012),(5.468,.112,.108,.008),
        (5.492,.018,.018,.005)
    ],hair,64)
    # V402: lift one side of the frontal hairline into a swept curve instead of a flat helmet rim.
    for vert in hair_cap.data.vertices:
        x,y,z=vert.co
        if y < 0.0 and z < 5.37:
            front_weight=max(0.0,min(1.0,(-y-.025)/.20))
            edge_weight=max(0.0,min(1.0,(5.38-z)/.15))
            sweep_weight=max(0.0,min(1.0,.5-x/.52))
            vert.co.z += front_weight*edge_weight*(.018 - .022*math.exp(-((x/.030)**2)))  # V405: softer center part, remove raised helmet-like sweep
    hair_cap.data.update()
    hair_parts=[hair_cap]
    hair_parts.append(uv("HAIR_BACK_MASS",(0,.105,5.005),(.270,.115,.238),hair,48,32))
    hair_parts.append(uv("HAIR_LOCK_L",(-.242,.006,4.995),(.041,.052,.174),hair,36,24))
    hair_parts.append(uv("HAIR_LOCK_R",(.242,.006,4.995),(.041,.052,.174),hair,36,24))
    # V403: broad layered curtains create the main long-hair silhouette; thin sheen strokes
    # are only accents, never the primary hair mass. Panels are behind the facial surface.
    for sign,side in [(-1,"L"),(1,"R")]:
        hair_parts.append(hair_ribbon("HAIR_LONG_FACE_PANEL_"+side,[
            (sign*.205,-.155,5.315),(sign*.238,-.180,5.170),
            (sign*.265,-.190,4.980),(sign*.280,-.180,4.735),
            (sign*.304,-.165,4.470),(sign*.298,-.150,4.180),
            (sign*.327,-.125,3.890),(sign*.315,-.100,3.590),
            (sign*.345,-.075,3.280),(sign*.328,-.045,2.960),
            (sign*.335,-.025,2.800)
        ],[.020,.040,.052,.060,.068,.067,.062,.056,.047,.032,.008],.024,hair))
        hair_parts.append(hair_ribbon("HAIR_LONG_REAR_PANEL_"+side,[
            (sign*.145,.085,5.330),(sign*.195,.125,5.100),
            (sign*.230,.155,4.820),(sign*.250,.170,4.510),
            (sign*.270,.170,4.180),(sign*.285,.150,3.830),
            (sign*.295,.120,3.490),(sign*.300,.095,3.150),
            (sign*.295,.085,2.860),(sign*.290,.080,2.720)
        ],[.040,.065,.082,.090,.092,.087,.078,.065,.040,.008],.026,hair))
    # A short diagonal fringe follows the cap surface instead of floating in front like a tube.
    fringe=capsule_piece("HAIR_SIDE_SWEPT_FRINGE",(-.155,-.197,5.365),(.125,-.245,5.270),.045,hair,.018)
    hair_parts.append(fringe)
    fused_hair=fuse(hair_parts,"LAM_CONTINUOUS_HAIR",.010,.26,1)

    # Reference-led hair flow: layered curved locks add directional silhouette beyond the cap.
    hair_sheen=material("Lam hair soft charcoal sheen",(.018,.014,.017),.42)
    hair_glint=material("Lam hair subtle warm strand",(.028,.019,.022),.46)
    for sign,side in [(-1,"L"),(1,"R")]:
        # Face-framing locks taper from the part, pass beside the cheek, then fall over the chest.
        for idx,offset in enumerate((0.0,.075)):
            x0=sign*(.035+offset*.32)
            x1=sign*(.105+offset*.52)
            x2=sign*(.185+offset*.62)
            x3=sign*(.235+offset*.62)
            x4=sign*(.270+offset*.58)
            pts=[
                (x0,-.155-offset*.08,5.435-offset*.06),
                (x1,-.206-offset*.035,5.315-offset*.035),
                (x2,-.222-offset*.020,5.145),
                (x3,-.205-offset*.012,4.945),
                (x4,-.178-offset*.010,4.725),
                (sign*(.285+offset*.52),-.145-offset*.008,4.485),
                (sign*(.300+offset*.45),-.115-offset*.006,4.315)
            ]
            curve_stroke("HAIR_FACE_FRAME_"+side+str(idx),pts,.0025 if idx%2 else .0033,hair_sheen if idx%2 else hair_glint)
        # Longer side/back locks follow the shoulder line rather than ending as a single lump.
        for idx,offset in enumerate((0.0,.080)):
            pts=[
                (sign*(.075+offset*.20),.025+offset*.15,5.420-offset*.025),
                (sign*(.150+offset*.24),.095+offset*.12,5.245),
                (sign*(.215+offset*.20),.135+offset*.10,5.030),
                (sign*(.245+offset*.18),.155+offset*.08,4.790),
                (sign*(.255+offset*.15),.135+offset*.08,4.560),
                (sign*(.260+offset*.12),.105+offset*.06,4.345)
            ]
            curve_stroke("HAIR_BACK_FLOW_"+side+str(idx),pts,.0025,hair_sheen)

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
                w=front*gauss(ax,.072,.042)*gauss(z,4.905,.060)
                co.y-=.005*w; co.z+=.020*w
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
                co.z-=.055*jaw; co.y+=.010*jaw
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
                co.x*=1.22; co.z+=.017*(abs(x)/.060)**2
            elif kind=="mouth_open":
                co.z=(z+.012) if z>=0 else (z-.015)
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
                co.x*=1.5; co.z*=1.6
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
    report={"status":"EXPERIMENTAL_CANDIDATE_NOT_APPROVED","purpose":"Integrated stylized avatar candidate; separate from production GLB","candidate":os.path.basename(glb),"bytes":os.path.getsize(glb),"mesh_count":sum(o.type=="MESH" for o in figure_meshes),"armature_name":rig.name,"bone_count":len(rig.data.bones),"skinned_mesh_count":sum(1 for o in figure_meshes if any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers)),"morph_targets":required_morphs,"morph_max_local_delta":morph_effects,"measured_bounds_m":bounds,"height_error_m":abs(bounds["size"][2]-1.60),"renders":["coherent-body-front.png","coherent-body-three-quarter.png","coherent-body-face-front.png","coherent-body-face-profile.png"],"warnings":["Not a photorealistic final avatar","No armature or facial morphs transferred","Figure normalized to approximately 1.60 m","Reference Reconstruction V1: changed everyday outfit to dark-teal crop top, refined eye proportions, and added layered front/back hair-flow curves; head sculpt remains a procedural approximation and candidate is not approved","Rig and facial morph targets are initial candidates, not production-approved; must pass candidate-specific pose/morph validation, expression render review, and web/mobile acceptance"]}
    with open(os.path.join(out,"coherent-body-candidate.json"),"w",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print("COHERENT_BODY_CANDIDATE="+json.dumps(report,ensure_ascii=False))
    assert os.path.getsize(glb)>1024
    assert abs(bounds["size"][2]-1.60)<0.03, "Candidate height is outside 1.60m tolerance"
    assert len(rig.data.bones)==17, "Candidate rig must have all 17 humanoid bones"
    assert all(v>1e-6 for v in morph_effects.values()), "Candidate facial morphs must be geometrically effective"
if __name__=="__main__":
    try:main()
    except Exception:traceback.print_exc();raise
