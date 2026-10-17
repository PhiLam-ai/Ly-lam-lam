#!/usr/bin/env python3
"""Unit tests for the V387 glTF skinning structural validator."""
import unittest

from validate_gltf_skinning_v387 import EXPECTED_MORPHS, validate


def valid_gltf():
    morphs = sorted(EXPECTED_MORPHS)
    return {
        "nodes": [
            {"name": "ArmatureRoot"},
            {"name": "Body", "mesh": 0, "skin": 0},
        ],
        "meshes": [{
            "name": "BodyMesh",
            "extras": {"targetNames": morphs},
            "primitives": [{
                "attributes": {"POSITION": 0, "JOINTS_0": 1, "WEIGHTS_0": 2},
                "targets": [{} for _ in morphs],
            }],
        }],
        "skins": [{"joints": [0], "inverseBindMatrices": 3}],
        "animations": [{
            "name": "Idle",
            "channels": [{"target": {"node": 0, "path": "rotation"}}],
        }],
        "accessors": [
            {"count": 3, "type": "VEC3", "componentType": 5126},
            {"count": 3, "type": "VEC4", "componentType": 5123},
            {"count": 3, "type": "VEC4", "componentType": 5126},
            {"count": 1, "type": "MAT4", "componentType": 5126},
        ],
    }


class SkinningValidatorTests(unittest.TestCase):
    def test_accepts_structurally_valid_skinned_glb_json(self):
        self.assertEqual(validate(valid_gltf()), [])

    def test_rejects_baked_unskinned_mesh(self):
        gltf = valid_gltf()
        gltf["skins"] = []
        gltf["nodes"][1].pop("skin")
        errors = validate(gltf)
        self.assertTrue(any("No glTF skins found" in error for error in errors))

    def test_rejects_skin_attribute_count_mismatch(self):
        gltf = valid_gltf()
        gltf["accessors"][2]["count"] = 2
        errors = validate(gltf)
        self.assertTrue(any("counts must match POSITION" in error for error in errors))

    def test_rejects_invalid_joint_accessor_type(self):
        gltf = valid_gltf()
        gltf["accessors"][1]["componentType"] = 5126
        errors = validate(gltf)
        self.assertTrue(any("JOINTS_0 must be VEC4 unsigned byte/short" in error for error in errors))

    def test_requires_all_expected_facial_morph_names(self):
        gltf = valid_gltf()
        gltf["meshes"][0]["extras"]["targetNames"].remove("smile")
        errors = validate(gltf)
        self.assertTrue(any("smile" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
