using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using VRC.SDK3.Avatars.Components;
using VRC.SDK3.Avatars.ScriptableObjects;

namespace VEA.Editor
{
    public class VeaDebugTest : EditorWindow
    {
        private VRCAvatarDescriptor _avatar;
        private RuntimeAnimatorController _originalFx;
        private bool _isTestMode;

        private static readonly string[] EmotionNames = { "Joy", "Anger", "Sadness", "Surprise", "Neutral" };

        [MenuItem("Tools/VEA/Debug Test")]
        public static void ShowWindow()
        {
            var window = GetWindow<VeaDebugTest>("VEA Debug");
            window.minSize = new Vector2(400, 300);
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("VEA Debug Test", EditorStyles.boldLabel);
            EditorGUILayout.Space(5);

            _avatar = (VRCAvatarDescriptor)EditorGUILayout.ObjectField(
                "Avatar", _avatar, typeof(VRCAvatarDescriptor), true);

            if (_avatar == null)
            {
                EditorGUILayout.HelpBox("アバターをドラッグしてください", MessageType.Warning);
                return;
            }

            EditorGUILayout.Space(10);

            // 診断情報
            EditorGUILayout.LabelField("診断", EditorStyles.boldLabel);

            // Expression Parameters チェック
            var exParams = _avatar.expressionParameters;
            if (exParams != null)
            {
                foreach (var eName in EmotionNames)
                {
                    var p = exParams.FindParameter($"VEA_{eName}");
                    string status = p != null ? $"OK (type={p.valueType})" : "MISSING";
                    EditorGUILayout.LabelField($"  VEA_{eName}: {status}");
                }
            }
            else
            {
                EditorGUILayout.LabelField("  Expression Parameters: 未設定!");
            }

            // FXレイヤーチェック
            EditorGUILayout.Space(5);
            var fxController = GetFxController();
            if (fxController != null)
            {
                EditorGUILayout.LabelField($"  FX Controller: {fxController.name}");
                var layers = fxController.layers;
                for (int i = 0; i < layers.Length; i++)
                {
                    string veaTag = layers[i].name == "VEA_Emotions" ? " ← VEA" : "";
                    EditorGUILayout.LabelField(
                        $"    [{i}] {layers[i].name} (weight={layers[i].defaultWeight}, mode={layers[i].blendingMode}){veaTag}");
                }
            }

            // BlendShape直接テスト
            EditorGUILayout.Space(10);
            EditorGUILayout.LabelField("直接BlendShapeテスト", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Animatorを通さず、BlendShapeを直接動かしてメッシュが反応するか確認します。",
                MessageType.Info);

            if (GUILayout.Button("笑顔テスト (eye_smile_1 + mouth_smile_2 = 100)", GUILayout.Height(25)))
            {
                TestBlendShapeDirect("eye_smile_1", 100f);
                TestBlendShapeDirect("mouth_smile_2", 100f);
                TestBlendShapeDirect("eyebrow_happy", 100f);
                SceneView.RepaintAll();
            }

            if (GUILayout.Button("リセット (全BlendShape = 0)", GUILayout.Height(25)))
            {
                ResetAllBlendShapes();
                SceneView.RepaintAll();
            }

            // テスト用FXコントローラー
            EditorGUILayout.Space(10);
            EditorGUILayout.LabelField("VEA単体テスト用FX", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "VEAレイヤーだけの最小FXコントローラーに一時的に差し替えます。\n" +
                "これで動けば、他のレイヤーとの干渉が原因です。",
                MessageType.Info);

            if (!_isTestMode)
            {
                if (GUILayout.Button("テスト用FXに差し替え", GUILayout.Height(30)))
                    SwitchToTestFx();
            }
            else
            {
                GUI.backgroundColor = new Color(1f, 0.6f, 0.3f);
                if (GUILayout.Button("元のFXに戻す", GUILayout.Height(30)))
                    RestoreOriginalFx();
                GUI.backgroundColor = Color.white;
                EditorGUILayout.HelpBox("テストモード中！確認が終わったら必ず元に戻してください。", MessageType.Warning);
            }
        }

        private void TestBlendShapeDirect(string shapeName, float value)
        {
            var renderers = _avatar.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            foreach (var r in renderers)
            {
                if (r.sharedMesh == null) continue;
                int idx = r.sharedMesh.GetBlendShapeIndex(shapeName);
                if (idx >= 0)
                {
                    r.SetBlendShapeWeight(idx, value);
                    Debug.Log($"Set {r.name}.{shapeName} = {value}");
                }
            }
        }

        private void ResetAllBlendShapes()
        {
            var renderers = _avatar.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            foreach (var r in renderers)
            {
                if (r.sharedMesh == null) continue;
                for (int i = 0; i < r.sharedMesh.blendShapeCount; i++)
                    r.SetBlendShapeWeight(i, 0);
            }
        }

        private AnimatorController GetFxController()
        {
            if (!_avatar.customizeAnimationLayers) return null;
            foreach (var layer in _avatar.baseAnimationLayers)
            {
                if (layer.type == VRCAvatarDescriptor.AnimLayerType.FX && !layer.isDefault)
                    return layer.animatorController as AnimatorController;
            }
            return null;
        }

        private void SwitchToTestFx()
        {
            var testController = new AnimatorController();
            testController.name = "VEA_TestFX";
            string path = "Assets/VEA/Generated/VEA_TestFX.controller";
            AssetDatabase.CreateAsset(testController, path);

            foreach (var eName in EmotionNames)
                testController.AddParameter($"VEA_{eName}", AnimatorControllerParameterType.Float);

            var blendTree = new BlendTree
            {
                name = "VEA_TestBlend",
                blendType = BlendTreeType.Direct,
            };

            foreach (var eName in EmotionNames)
            {
                string clipPath = $"Assets/VEA/Generated/Animations/VEA_{eName}.anim";
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (clip == null)
                {
                    clip = new AnimationClip { name = $"VEA_{eName}_empty" };
                }
                blendTree.AddChild(clip);
                var children = blendTree.children;
                children[children.Length - 1].directBlendParameter = $"VEA_{eName}";
                blendTree.children = children;
            }

            AssetDatabase.AddObjectToAsset(blendTree, testController);

            var layer = testController.layers[0];
            var state = layer.stateMachine.AddState("VEA_Blend");
            state.motion = blendTree;
            state.writeDefaultValues = true;

            var layers = testController.layers;
            layers[0].defaultWeight = 1f;
            testController.layers = layers;

            EditorUtility.SetDirty(testController);
            AssetDatabase.SaveAssets();

            // 差し替え
            Undo.RecordObject(_avatar, "Switch to Test FX");
            var avatarLayers = _avatar.baseAnimationLayers;
            for (int i = 0; i < avatarLayers.Length; i++)
            {
                if (avatarLayers[i].type == VRCAvatarDescriptor.AnimLayerType.FX)
                {
                    _originalFx = avatarLayers[i].animatorController;
                    avatarLayers[i].animatorController = testController;
                    avatarLayers[i].isDefault = false;
                    break;
                }
            }
            _avatar.baseAnimationLayers = avatarLayers;
            EditorUtility.SetDirty(_avatar);

            _isTestMode = true;
        }

        private void RestoreOriginalFx()
        {
            if (_originalFx == null) return;

            Undo.RecordObject(_avatar, "Restore FX");
            var avatarLayers = _avatar.baseAnimationLayers;
            for (int i = 0; i < avatarLayers.Length; i++)
            {
                if (avatarLayers[i].type == VRCAvatarDescriptor.AnimLayerType.FX)
                {
                    avatarLayers[i].animatorController = _originalFx;
                    break;
                }
            }
            _avatar.baseAnimationLayers = avatarLayers;
            EditorUtility.SetDirty(_avatar);

            _isTestMode = false;
            _originalFx = null;
        }
    }
}
