using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using VRC.SDK3.Avatars.Components;
using nadena.dev.modular_avatar.core;

namespace VEA.Editor
{
    public class VeaMaSetup : EditorWindow
    {
        private VRCAvatarDescriptor _avatar;
        private string _outputFolder = "Assets/VEA/Generated";
        private Vector2 _scrollPos;

        private static readonly string[] EmotionNames = { "Joy", "Anger", "Sadness", "Surprise", "Neutral" };
        private const string ParameterPrefix = "VEA";
        private const string VEA_OBJECT_NAME = "VEA_EmotionSystem";

        [MenuItem("Tools/VEA/Setup with Modular Avatar")]
        public static void ShowWindow()
        {
            var window = GetWindow<VeaMaSetup>("VEA MA Setup");
            window.minSize = new Vector2(420, 320);
        }

        private void OnGUI()
        {
            _scrollPos = EditorGUILayout.BeginScrollView(_scrollPos);

            EditorGUILayout.LabelField("VEA - Modular Avatar Setup", EditorStyles.boldLabel);
            EditorGUILayout.Space(5);
            EditorGUILayout.HelpBox(
                "Modular Avatarを使ってVEAのFXレイヤーを非破壊で追加します。\n" +
                "Face-Emoなど他のツールと干渉しません。",
                MessageType.Info);
            EditorGUILayout.Space(5);

            _avatar = (VRCAvatarDescriptor)EditorGUILayout.ObjectField(
                "Avatar", _avatar, typeof(VRCAvatarDescriptor), true);

            if (_avatar == null)
            {
                EditorGUILayout.HelpBox("アバターをドラッグしてください。", MessageType.Warning);
                EditorGUILayout.EndScrollView();
                return;
            }

            var existing = _avatar.transform.Find(VEA_OBJECT_NAME);
            if (existing != null)
            {
                EditorGUILayout.Space(5);
                EditorGUILayout.HelpBox("VEAは既にセットアップ済みです。再セットアップすると上書きされます。", MessageType.Info);
            }

            EditorGUILayout.Space(10);

            if (GUILayout.Button("Setup VEA (Modular Avatar)", GUILayout.Height(35)))
            {
                RunSetup();
            }

            if (existing != null)
            {
                EditorGUILayout.Space(5);
                GUI.backgroundColor = new Color(1f, 0.5f, 0.5f);
                if (GUILayout.Button("VEAを削除", GUILayout.Height(25)))
                {
                    Undo.DestroyObjectImmediate(existing.gameObject);
                }
                GUI.backgroundColor = Color.white;
            }

            EditorGUILayout.EndScrollView();
        }

        private void RunSetup()
        {
            Undo.SetCurrentGroupName("VEA MA Setup");
            int undoGroup = Undo.GetCurrentGroup();

            if (!Directory.Exists(_outputFolder))
            {
                Directory.CreateDirectory(_outputFolder);
                AssetDatabase.Refresh();
            }

            var controller = CreateVeaController();
            var clips = CreateAnimationClips();
            SetupBlendTree(controller, clips);
            SetupMaObject(controller);

            Undo.CollapseUndoOperations(undoGroup);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            EditorUtility.DisplayDialog("VEA MA Setup",
                "セットアップ完了！\n\n" +
                "1. Tools → VEA → BlendShape Editor で表情を設定\n" +
                "2. アバターをアップロード\n\n" +
                "Modular Avatarがビルド時にFXレイヤーをマージします。",
                "OK");
        }

        private AnimatorController CreateVeaController()
        {
            string path = $"{_outputFolder}/VEA_MA_FX.controller";
            var existing = AssetDatabase.LoadAssetAtPath<AnimatorController>(path);
            if (existing != null)
            {
                foreach (var eName in EmotionNames)
                {
                    string pName = $"{ParameterPrefix}_{eName}";
                    if (!existing.parameters.Any(p => p.name == pName))
                        existing.AddParameter(pName, AnimatorControllerParameterType.Float);
                }
                return existing;
            }

            var controller = new AnimatorController();
            controller.name = "VEA_MA_FX";
            AssetDatabase.CreateAsset(controller, path);

            foreach (var eName in EmotionNames)
                controller.AddParameter($"{ParameterPrefix}_{eName}", AnimatorControllerParameterType.Float);

            return controller;
        }

        private Dictionary<string, AnimationClip> CreateAnimationClips()
        {
            var clips = new Dictionary<string, AnimationClip>();
            string animFolder = $"{_outputFolder}/Animations";
            if (!Directory.Exists(animFolder))
            {
                Directory.CreateDirectory(animFolder);
                AssetDatabase.Refresh();
            }

            foreach (var eName in EmotionNames)
            {
                string clipPath = $"{animFolder}/VEA_{eName}.anim";
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (clip == null)
                {
                    clip = new AnimationClip { name = $"VEA_{eName}" };
                    AssetDatabase.CreateAsset(clip, clipPath);
                }
                clips[eName] = clip;
            }

            return clips;
        }

        private void SetupBlendTree(AnimatorController controller, Dictionary<string, AnimationClip> clips)
        {
            var layers = controller.layers;
            int existingIdx = -1;
            for (int i = 0; i < layers.Length; i++)
            {
                if (layers[i].name == "VEA_Emotions")
                {
                    existingIdx = i;
                    break;
                }
            }

            var blendTree = new BlendTree
            {
                name = "VEA_DirectBlend",
                blendType = BlendTreeType.Direct,
            };

            foreach (var eName in EmotionNames)
            {
                blendTree.AddChild(clips[eName]);
                var children = blendTree.children;
                children[children.Length - 1].directBlendParameter = $"{ParameterPrefix}_{eName}";
                blendTree.children = children;
            }

            if (existingIdx >= 0)
            {
                var sm = layers[existingIdx].stateMachine;
                foreach (var s in sm.states)
                    sm.RemoveState(s.state);
                var state = sm.AddState("VEA_Blend");
                state.motion = blendTree;
                state.writeDefaultValues = true;
                if (AssetDatabase.GetAssetPath(blendTree) == "")
                    AssetDatabase.AddObjectToAsset(blendTree, controller);
            }
            else
            {
                var sm = new AnimatorStateMachine
                {
                    name = "VEA_Emotions",
                    hideFlags = HideFlags.HideInHierarchy,
                };
                AssetDatabase.AddObjectToAsset(sm, controller);

                var state = sm.AddState("VEA_Blend");
                state.motion = blendTree;
                state.writeDefaultValues = true;
                AssetDatabase.AddObjectToAsset(blendTree, controller);

                var newLayer = new AnimatorControllerLayer
                {
                    name = "VEA_Emotions",
                    stateMachine = sm,
                    defaultWeight = 1f,
                };

                var layerList = new List<AnimatorControllerLayer>(layers) { newLayer };
                controller.layers = layerList.ToArray();
            }

            EditorUtility.SetDirty(controller);
        }

        private void SetupMaObject(AnimatorController controller)
        {
            var existing = _avatar.transform.Find(VEA_OBJECT_NAME);
            GameObject veaObj;

            if (existing != null)
            {
                veaObj = existing.gameObject;
                Undo.RecordObject(veaObj, "Update VEA MA");
            }
            else
            {
                veaObj = new GameObject(VEA_OBJECT_NAME);
                Undo.RegisterCreatedObjectUndo(veaObj, "Create VEA MA Object");
                veaObj.transform.SetParent(_avatar.transform);
                veaObj.transform.localPosition = Vector3.zero;
                veaObj.transform.localRotation = Quaternion.identity;
                veaObj.transform.localScale = Vector3.one;
            }

            // MA Merge Animator
            var mergeAnimator = veaObj.GetComponent<ModularAvatarMergeAnimator>();
            if (mergeAnimator == null)
                mergeAnimator = Undo.AddComponent<ModularAvatarMergeAnimator>(veaObj);

            mergeAnimator.animator = controller;
            mergeAnimator.layerType = VRCAvatarDescriptor.AnimLayerType.FX;
            mergeAnimator.pathMode = MergeAnimatorPathMode.Absolute;
            mergeAnimator.matchAvatarWriteDefaults = true;
            EditorUtility.SetDirty(mergeAnimator);

            // MA Parameters
            var maParams = veaObj.GetComponent<ModularAvatarParameters>();
            if (maParams == null)
                maParams = Undo.AddComponent<ModularAvatarParameters>(veaObj);

            maParams.parameters = new List<ParameterConfig>();
            foreach (var eName in EmotionNames)
            {
                maParams.parameters.Add(new ParameterConfig
                {
                    nameOrPrefix = $"{ParameterPrefix}_{eName}",
                    syncType = ParameterSyncType.Float,
                    localOnly = false,
                    defaultValue = eName == "Neutral" ? 1f : 0f,
                    saved = false,
                    hasExplicitDefaultValue = true,
                });
            }
            EditorUtility.SetDirty(maParams);
        }
    }
}
