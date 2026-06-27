using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using VRC.SDK3.Avatars.Components;
using VRC.SDK3.Avatars.ScriptableObjects;

namespace VEA.Editor
{
    public class VeaSetupWindow : EditorWindow
    {
        private VRCAvatarDescriptor _avatar;
        private string _outputFolder = "Assets/VEA/Generated";
        private bool _createAnimClips = true;
        private Vector2 _scrollPos;

        private bool _fullMode;
        private static readonly string[] SimpleEmotions = { "Joy", "Anger", "Sadness", "Surprise", "Neutral" };
        private static readonly string[] FullEmotions = { "Joy", "Anger", "Sadness", "Surprise", "Disgust", "Fear", "Neutral" };
        private string[] EmotionNames => _fullMode ? FullEmotions : SimpleEmotions;
        private const string ParameterPrefix = "VEA";
        private const string LayerName = "VEA_Emotions";

        [MenuItem("Tools/VEA/Setup Avatar")]
        public static void ShowWindow()
        {
            var window = GetWindow<VeaSetupWindow>("VEA Setup");
            window.minSize = new Vector2(400, 350);
        }

        private void OnGUI()
        {
            _scrollPos = EditorGUILayout.BeginScrollView(_scrollPos);

            EditorGUILayout.LabelField("VoiceEmotionAvatar Setup", EditorStyles.boldLabel);
            EditorGUILayout.Space(5);

            EditorGUILayout.HelpBox(
                "アバターにVEA用のExpression Parameters、FXレイヤー、表情アニメーション雛形を追加します。",
                MessageType.Info);
            EditorGUILayout.Space(5);

            _avatar = (VRCAvatarDescriptor)EditorGUILayout.ObjectField(
                "Avatar", _avatar, typeof(VRCAvatarDescriptor), true);

            _outputFolder = EditorGUILayout.TextField("Output Folder", _outputFolder);
            _fullMode = EditorGUILayout.Toggle("Full Mode (7 emotions)", _fullMode);
            _createAnimClips = EditorGUILayout.Toggle("Create Animation Clips", _createAnimClips);

            EditorGUILayout.Space(10);

            if (_avatar == null)
            {
                EditorGUILayout.HelpBox("シーン上のアバター（VRCAvatarDescriptor）をドラッグしてください。", MessageType.Warning);
            }
            else
            {
                DrawStatus();
                EditorGUILayout.Space(10);

                if (GUILayout.Button("Setup VEA", GUILayout.Height(35)))
                {
                    RunSetup();
                }
            }

            EditorGUILayout.EndScrollView();
        }

        private void DrawStatus()
        {
            EditorGUILayout.LabelField("Current Status", EditorStyles.boldLabel);

            var exParams = _avatar.expressionParameters;
            if (exParams == null)
            {
                EditorGUILayout.HelpBox("Expression Parametersが未設定です。新規作成します。", MessageType.Warning);
            }
            else
            {
                int existing = EmotionNames.Count(e => exParams.FindParameter($"{ParameterPrefix}_{e}") != null);
                EditorGUILayout.LabelField($"  VEAパラメータ: {existing}/{EmotionNames.Length} 登録済み");
                int cost = exParams.CalcTotalCost();
                int newCost = (EmotionNames.Length - existing) * 8;
                EditorGUILayout.LabelField($"  パラメータコスト: {cost} + {newCost} = {cost + newCost} / 256");
                if (cost + newCost > 256)
                {
                    EditorGUILayout.HelpBox("パラメータコストが上限(256)を超えます！不要なパラメータを削除してください。", MessageType.Error);
                }
            }

            var fxLayer = GetFxLayer();
            if (fxLayer == null)
            {
                EditorGUILayout.HelpBox("FXレイヤーが見つかりません。", MessageType.Warning);
            }
            else
            {
                bool hasVeaLayer = fxLayer.layers.Any(l => l.name == LayerName);
                EditorGUILayout.LabelField($"  FX Controller: {fxLayer.name}");
                EditorGUILayout.LabelField($"  VEAレイヤー: {(hasVeaLayer ? "あり（上書きします）" : "なし（新規追加）")}");
            }
        }

        private void RunSetup()
        {
            Undo.SetCurrentGroupName("VEA Setup");
            int undoGroup = Undo.GetCurrentGroup();

            if (!Directory.Exists(_outputFolder))
            {
                Directory.CreateDirectory(_outputFolder);
                AssetDatabase.Refresh();
            }

            SetupExpressionParameters();
            var clips = _createAnimClips ? CreateAnimationClips() : GetExistingOrEmptyClips();
            SetupFxLayer(clips);

            Undo.CollapseUndoOperations(undoGroup);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            EditorUtility.DisplayDialog("VEA Setup", "セットアップが完了しました！\n\n表情アニメーションクリップを編集して、各感情のBlendShape値を設定してください。", "OK");
        }

        private void SetupExpressionParameters()
        {
            var exParams = _avatar.expressionParameters;
            if (exParams == null)
            {
                exParams = CreateInstance<VRCExpressionParameters>();
                exParams.parameters = new VRCExpressionParameters.Parameter[0];
                string path = $"{_outputFolder}/VEA_ExpressionParameters.asset";
                AssetDatabase.CreateAsset(exParams, path);
                Undo.RecordObject(_avatar, "Set Expression Parameters");
                _avatar.expressionParameters = exParams;
                EditorUtility.SetDirty(_avatar);
            }

            Undo.RecordObject(exParams, "Add VEA Parameters");
            var paramList = new List<VRCExpressionParameters.Parameter>(exParams.parameters);

            foreach (string emotion in EmotionNames)
            {
                string paramName = $"{ParameterPrefix}_{emotion}";
                if (exParams.FindParameter(paramName) != null)
                    continue;

                paramList.Add(new VRCExpressionParameters.Parameter
                {
                    name = paramName,
                    valueType = VRCExpressionParameters.ValueType.Float,
                    defaultValue = emotion == "Neutral" ? 1.0f : 0.0f,
                    saved = false,
                    networkSynced = true,
                });
            }

            exParams.parameters = paramList.ToArray();
            EditorUtility.SetDirty(exParams);
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

            foreach (string emotion in EmotionNames)
            {
                string clipPath = $"{animFolder}/VEA_{emotion}.anim";
                var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (existing != null)
                {
                    clips[emotion] = existing;
                    continue;
                }

                var clip = new AnimationClip { name = $"VEA_{emotion}" };

                // Placeholder curve - ユーザーが後から編集する
                var curve = new AnimationCurve(new Keyframe(0, 0));
                clip.SetCurve("Body", typeof(SkinnedMeshRenderer), "blendShape.placeholder_" + emotion, curve);

                AssetDatabase.CreateAsset(clip, clipPath);
                clips[emotion] = clip;
            }

            return clips;
        }

        private Dictionary<string, AnimationClip> GetExistingOrEmptyClips()
        {
            var clips = new Dictionary<string, AnimationClip>();
            foreach (string emotion in EmotionNames)
            {
                string clipPath = $"{_outputFolder}/Animations/VEA_{emotion}.anim";
                var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (existing != null)
                    clips[emotion] = existing;
            }
            return clips;
        }

        private AnimatorController GetFxLayer()
        {
            if (!_avatar.customizeAnimationLayers)
                return null;

            foreach (var layer in _avatar.baseAnimationLayers)
            {
                if (layer.type == VRCAvatarDescriptor.AnimLayerType.FX && !layer.isDefault)
                    return layer.animatorController as AnimatorController;
            }
            return null;
        }

        private void SetupFxLayer(Dictionary<string, AnimationClip> clips)
        {
            var fxController = GetFxLayer();
            if (fxController == null)
            {
                fxController = new AnimatorController();
                fxController.name = "VEA_FX";
                string controllerPath = $"{_outputFolder}/VEA_FX.controller";
                AssetDatabase.CreateAsset(fxController, controllerPath);

                Undo.RecordObject(_avatar, "Set FX Layer");
                _avatar.customizeAnimationLayers = true;
                var layers = _avatar.baseAnimationLayers;
                for (int i = 0; i < layers.Length; i++)
                {
                    if (layers[i].type == VRCAvatarDescriptor.AnimLayerType.FX)
                    {
                        layers[i].isDefault = false;
                        layers[i].animatorController = fxController;
                        break;
                    }
                }
                _avatar.baseAnimationLayers = layers;
                EditorUtility.SetDirty(_avatar);
            }

            Undo.RecordObject(fxController, "Add VEA FX Layer");

            foreach (string emotion in EmotionNames)
            {
                string paramName = $"{ParameterPrefix}_{emotion}";
                if (!fxController.parameters.Any(p => p.name == paramName))
                {
                    fxController.AddParameter(paramName, AnimatorControllerParameterType.Float);
                }
            }

            int existingIdx = -1;
            var controllerLayers = fxController.layers;
            for (int i = 0; i < controllerLayers.Length; i++)
            {
                if (controllerLayers[i].name == LayerName)
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

            foreach (string emotion in EmotionNames)
            {
                string paramName = $"{ParameterPrefix}_{emotion}";
                AnimationClip clip = clips.ContainsKey(emotion) ? clips[emotion] : null;
                if (clip == null)
                {
                    clip = new AnimationClip { name = $"VEA_{emotion}_empty" };
                }
                blendTree.AddChild(clip);
                var children = blendTree.children;
                children[children.Length - 1].directBlendParameter = paramName;
                blendTree.children = children;
            }

            if (existingIdx >= 0)
            {
                var stateMachine = controllerLayers[existingIdx].stateMachine;
                foreach (var state in stateMachine.states)
                    stateMachine.RemoveState(state.state);

                var newState = stateMachine.AddState("VEA_Blend");
                newState.motion = blendTree;
                newState.writeDefaultValues = true;

                // BlendTreeをコントローラーのサブアセットとして保存
                if (AssetDatabase.GetAssetPath(blendTree) == "")
                    AssetDatabase.AddObjectToAsset(blendTree, fxController);
            }
            else
            {
                var stateMachine = new AnimatorStateMachine
                {
                    name = LayerName,
                    hideFlags = HideFlags.HideInHierarchy,
                };
                AssetDatabase.AddObjectToAsset(stateMachine, fxController);

                var state = stateMachine.AddState("VEA_Blend");
                state.motion = blendTree;
                state.writeDefaultValues = true;
                AssetDatabase.AddObjectToAsset(blendTree, fxController);

                var newLayer = new AnimatorControllerLayer
                {
                    name = LayerName,
                    stateMachine = stateMachine,
                    defaultWeight = 1f,
                };

                var layerList = new List<AnimatorControllerLayer>(controllerLayers) { newLayer };
                fxController.layers = layerList.ToArray();
            }

            EditorUtility.SetDirty(fxController);
        }
    }
}
