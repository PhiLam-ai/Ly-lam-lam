import bpy, json, os, sys, hashlib
from collections import defaultdict

EXPECTED = [
    (("brow", "eye", "mouth", "nose", "ear", "hair", "head", "teeth", "tongue", "eyelid"), ("Lam_Joint_Head",)),
    (("hand", "finger", "thumb", "palm"), ("Lam_Joint_LeftWrist", "Lam_Joint_RightWrist")),
    (("foot", "toe"), ("Lam_Joint_LeftAnkle", "Lam_Joint_RightAnkle")),
    (("calf", "shin", "patella", "knee"), ("Lam_Joint_LeftKnee", "Lam_Joint_RightKnee", "Lam_Joint_LeftAnkle", "Lam_Joint_RightAnkle")),
    (("thigh", "upper_leg"), ("Lam_Joint_LeftHip", "Lam_Joint_RightHip", "Lam_Joint_Hips")),
    (("forearm", "elbow", "wrist"), ("Lam_Joint_LeftElbow", "Lam_Joint_RightElbow", "Lam_Joint_LeftWrist", "Lam_Joint_RightWrist")),
    (("upper_arm", "shoulder", "clavicle"), ("Lam_Joint_LeftShoulder", "Lam_Joint_RightShoulder", "Lam_Joint_Chest")),
    (("torso", "chest", "abdomen", "waist", "pelvis", "spine"), ("Lam_Joint_Hips", "Lam_Joint_Spine", "Lam_Joint_Chest")),
]

def expected_for(name):
    n=name.lower()
    for tokens, bones in EXPECTED:
        if any(t in n for t in tokens):
            return list(bones)
    return []

def main():
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    source=os.path.abspath("lam-default.glb")
    out_dir=os.path.abspath("artifacts/v313-named-weight-audit")
    for i,arg in enumerate(args[:-1]):
        if arg=="--input": source=os.path.abspath(args[i+1])
        elif arg=="--output-dir": out_dir=os.path.abspath(args[i+1])
    os.makedirs(out_dir,exist_ok=True)
    source_hash=hashlib.sha256(open(source,"rb").read()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    arm=next((o for o in bpy.context.scene.objects if o.type=="ARMATURE"),None)
    if arm is None: raise RuntimeError("No armature found")
    rows=[]
    for obj in (o for o in bpy.context.scene.objects if o.type=="MESH"):
        group_names={g.index:g.name for g in obj.vertex_groups}
        total=defaultdict(float); members=defaultdict(int); per_vertex=defaultdict(int)
        for v in obj.data.vertices:
            seen=set()
            for g in v.groups:
                bone=group_names.get(g.group,"")
                if not bone or g.weight<=1e-6: continue
                total[bone]+=float(g.weight); members[bone]+=1; seen.add(bone)
            for bone in seen: per_vertex[bone]+=1
        ranking=sorted(total, key=total.get, reverse=True)
        expected=expected_for(obj.name)
        dominant=ranking[0] if ranking else None
        # Only flag a name mismatch when the object name maps to a known body region.
        mismatch=bool(expected and dominant and dominant not in expected)
        rows.append({
            "mesh":obj.name,"vertex_count":len(obj.data.vertices),
            "expected_bone_family":expected,"dominant_weight_groups":[
                {"bone":b,"sum_weight":round(total[b],5),"weighted_memberships":members[b],
                 "vertices_with_group":per_vertex[b],
                 "mean_weight_per_vertex_with_group":round(total[b]/max(1,per_vertex[b]),5)}
                for b in ranking[:5]],
            "dominant_group_mismatch":mismatch,
            "note":"Name-based heuristic only; review mesh semantics, full weight distribution, rig and render before editing."
        })
    mismatches=[r for r in rows if r["dominant_group_mismatch"]]
    report={"status":"DIAGNOSTIC_ONLY_NO_MODEL_CHANGES","source":os.path.basename(source),
      "source_sha256":source_hash,"mesh_count":len(rows),"bone_count":len(arm.data.bones),
      "expected_mapping_rules":[{"name_tokens":list(tokens),"acceptable_bones":list(bones)} for tokens,bones in EXPECTED],
      "mismatch_count":len(mismatches),"mismatches":mismatches,"meshes":rows,
      "warning":"Expected groups are inferred from mesh names and are not a definitive rig specification. No weights, transforms, morphs or source file were changed."}
    path=os.path.join(out_dir,"v313-named-weight-audit.json")
    with open(path,"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print("V313_NAMED_WEIGHT_AUDIT=DIAGNOSTIC_ONLY")
    print(json.dumps({"source_sha256":source_hash,"mesh_count":len(rows),"mismatch_count":len(mismatches),
      "mismatches":[{"mesh":r["mesh"],"expected":r["expected_bone_family"],"dominant":r["dominant_weight_groups"][0]["bone"] if r["dominant_weight_groups"] else None} for r in mismatches]},ensure_ascii=False))
if __name__=="__main__": main()
