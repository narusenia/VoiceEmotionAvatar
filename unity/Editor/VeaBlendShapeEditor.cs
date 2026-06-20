using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using VRC.SDK3.Avatars.Components;

namespace VEA.Editor
{
    public class VeaBlendShapeEditor : EditorWindow
    {
        private VRCAvatarDescriptor _avatar;
        private SkinnedMeshRenderer _faceMesh;
        private string _faceMeshPath;
        private string _animFolder = "Assets/VEA/Generated/Animations";
        private Vector2 _scrollPos;
        private int _selectedEmotion;
        private string _searchFilter = "";
        private bool _isPreviewing;

        private bool _fullMode;

        private static readonly string[] SimpleEmotions = { "Joy", "Anger", "Sadness", "Surprise", "Neutral" };
        private static readonly string[] FullEmotions = { "Joy", "Anger", "Sadness", "Surprise", "Disgust", "Fear", "Neutral" };
        private static readonly Color[] SimpleColors =
        {
            new Color(1f, 0.84f, 0f),
            new Color(0.94f, 0.27f, 0.27f),
            new Color(0.38f, 0.65f, 0.96f),
            new Color(0.98f, 0.57f, 0.24f),
            new Color(0.58f, 0.64f, 0.72f),
        };
        private static readonly Color[] FullColors =
        {
            new Color(1f, 0.84f, 0f),
            new Color(0.94f, 0.27f, 0.27f),
            new Color(0.38f, 0.65f, 0.96f),
            new Color(0.98f, 0.57f, 0.24f),
            new Color(0.58f, 0.64f, 0.72f),
            new Color(0.51f, 0.31f, 0.71f),
            new Color(0.39f, 0.78f, 0.71f),
        };

        private string[] EmotionNames => _fullMode ? FullEmotions : SimpleEmotions;
        private Color[] EmotionColors => _fullMode ? FullColors : SimpleColors;

        private Dictionary<string, Dictionary<string, float>> _emotionValues = new();
        private string[] _blendShapeNames = new string[0];

        [MenuItem("Tools/VEA/BlendShape Editor")]
        public static void ShowWindow()
        {
            var window = GetWindow<VeaBlendShapeEditor>("VEA BlendShape Editor");
            window.minSize = new Vector2(450, 500);
        }

        private void OnEnable()
        {
            foreach (var emotion in FullEmotions)
                _emotionValues[emotion] = new Dictionary<string, float>();
        }

        private void OnDisable()
        {
            StopPreview();
        }

        private void OnGUI()
        {
            _scrollPos = EditorGUILayout.BeginScrollView(_scrollPos);

            DrawHeader();
            EditorGUILayout.Space(5);
            DrawAvatarSelection();

            if (_avatar != null && _faceMesh != null)
            {
                EditorGUILayout.Space(5);
                DrawEmotionTabs();
                EditorGUILayout.Space(5);
                DrawBlendShapeList();
                EditorGUILayout.Space(10);
                DrawActions();
            }

            EditorGUILayout.EndScrollView();
        }

        private void DrawHeader()
        {
            EditorGUILayout.LabelField("VEA BlendShape Editor", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "各感情にBlendShapeを追加してスライダーで値を設定。\nプレビューでリアルタイム確認、Saveでアニメーションクリップに書き込みます。",
                MessageType.Info);
            EditorGUI.BeginChangeCheck();
            _fullMode = EditorGUILayout.Toggle("Full Mode (7 emotions)", _fullMode);
            if (EditorGUI.EndChangeCheck())
            {
                _selectedEmotion = Mathf.Min(_selectedEmotion, EmotionNames.Length - 1);
            }
        }

        private void DrawAvatarSelection()
        {
            EditorGUI.BeginChangeCheck();
            _avatar = (VRCAvatarDescriptor)EditorGUILayout.ObjectField(
                "Avatar", _avatar, typeof(VRCAvatarDescriptor), true);
            if (EditorGUI.EndChangeCheck() && _avatar != null)
            {
                DetectFaceMesh();
                LoadExistingClips();
            }

            if (_avatar != null)
            {
                EditorGUI.BeginChangeCheck();
                _faceMesh = (SkinnedMeshRenderer)EditorGUILayout.ObjectField(
                    "Face Mesh", _faceMesh, typeof(SkinnedMeshRenderer), true);
                if (EditorGUI.EndChangeCheck() && _faceMesh != null)
                {
                    CacheFaceMeshPath();
                    CacheBlendShapeNames();
                }

                if (_faceMesh == null)
                {
                    EditorGUILayout.HelpBox(
                        "顔のSkinnedMeshRendererが見つかりません。手動でドラッグしてください。",
                        MessageType.Warning);
                }
            }
        }

        private void DetectFaceMesh()
        {
            _faceMesh = null;
            var renderers = _avatar.GetComponentsInChildren<SkinnedMeshRenderer>(true);

            // BlendShapeが最も多いメッシュを顔として推定
            int maxShapes = 0;
            foreach (var r in renderers)
            {
                if (r.sharedMesh == null) continue;
                int count = r.sharedMesh.blendShapeCount;
                if (count > maxShapes)
                {
                    maxShapes = count;
                    _faceMesh = r;
                }
            }

            if (_faceMesh != null)
            {
                CacheFaceMeshPath();
                CacheBlendShapeNames();
            }
        }

        private void CacheFaceMeshPath()
        {
            _faceMeshPath = GetRelativePath(_avatar.transform, _faceMesh.transform);
        }

        private void CacheBlendShapeNames()
        {
            if (_faceMesh == null || _faceMesh.sharedMesh == null)
            {
                _blendShapeNames = new string[0];
                return;
            }

            var mesh = _faceMesh.sharedMesh;
            _blendShapeNames = new string[mesh.blendShapeCount];
            for (int i = 0; i < mesh.blendShapeCount; i++)
                _blendShapeNames[i] = mesh.GetBlendShapeName(i);
        }

        private void DrawEmotionTabs()
        {
            EditorGUILayout.BeginHorizontal();
            for (int i = 0; i < EmotionNames.Length; i++)
            {
                var prevColor = GUI.backgroundColor;
                if (i == _selectedEmotion)
                    GUI.backgroundColor = EmotionColors[i];
                if (GUILayout.Toggle(i == _selectedEmotion, EmotionNames[i], "Button", GUILayout.Height(28)))
                    _selectedEmotion = i;
                GUI.backgroundColor = prevColor;
            }
            EditorGUILayout.EndHorizontal();

            string emotion = EmotionNames[_selectedEmotion];
            int count = _emotionValues[emotion].Count;
            EditorGUILayout.LabelField($"  {emotion}: {count} BlendShapes 設定済み",
                EditorStyles.miniLabel);
        }

        private void DrawBlendShapeList()
        {
            string emotion = EmotionNames[_selectedEmotion];
            var values = _emotionValues[emotion];

            // 現在設定済みのBlendShape
            EditorGUILayout.LabelField("設定済み", EditorStyles.boldLabel);

            var toRemove = new List<string>();
            foreach (var kvp in values.ToList())
            {
                EditorGUILayout.BeginHorizontal();

                // 色付きドット
                var rect = GUILayoutUtility.GetRect(12, 18, GUILayout.Width(12));
                EditorGUI.DrawRect(new Rect(rect.x + 2, rect.y + 5, 8, 8), EmotionColors[_selectedEmotion]);

                EditorGUILayout.LabelField(kvp.Key, GUILayout.Width(200));

                float newVal = EditorGUILayout.Slider(kvp.Value, 0f, 100f);
                if (newVal != kvp.Value)
                {
                    values[kvp.Key] = newVal;
                    if (_isPreviewing)
                        ApplyPreview();
                }

                if (GUILayout.Button("×", GUILayout.Width(22), GUILayout.Height(18)))
                    toRemove.Add(kvp.Key);

                EditorGUILayout.EndHorizontal();
            }

            foreach (var key in toRemove)
            {
                values.Remove(key);
                if (_isPreviewing) ApplyPreview();
            }

            // BlendShape追加セクション
            EditorGUILayout.Space(8);
            EditorGUILayout.LabelField("BlendShape を追加", EditorStyles.boldLabel);
            _searchFilter = EditorGUILayout.TextField("検索", _searchFilter);

            if (_blendShapeNames.Length > 0)
            {
                var filtered = _blendShapeNames
                    .Where(n => !values.ContainsKey(n))
                    .Where(n => string.IsNullOrEmpty(_searchFilter) ||
                                n.ToLower().Contains(_searchFilter.ToLower()))
                    .ToArray();

                int displayCount = Mathf.Min(filtered.Length, 30);
                if (filtered.Length > 30)
                    EditorGUILayout.LabelField($"  {filtered.Length} 件中 30件表示（検索で絞り込めます）",
                        EditorStyles.miniLabel);

                for (int i = 0; i < displayCount; i++)
                {
                    EditorGUILayout.BeginHorizontal();
                    EditorGUILayout.LabelField(filtered[i], GUILayout.Width(250));
                    if (GUILayout.Button("+ 追加", GUILayout.Width(60)))
                    {
                        values[filtered[i]] = 100f;
                        if (_isPreviewing) ApplyPreview();
                    }
                    EditorGUILayout.EndHorizontal();
                }
            }
        }

        private void DrawActions()
        {
            EditorGUILayout.BeginHorizontal();

            // プレビューボタン
            var prevBg = GUI.backgroundColor;
            if (_isPreviewing)
                GUI.backgroundColor = new Color(0.3f, 0.9f, 0.4f);
            if (GUILayout.Button(_isPreviewing ? "■ Stop Preview" : "▶ Preview", GUILayout.Height(30)))
            {
                if (_isPreviewing) StopPreview();
                else StartPreview();
            }
            GUI.backgroundColor = prevBg;

            // 保存ボタン
            GUI.backgroundColor = new Color(0.4f, 0.7f, 1f);
            if (GUILayout.Button("Save Current", GUILayout.Height(30)))
            {
                SaveClip(EmotionNames[_selectedEmotion]);
            }
            GUI.backgroundColor = prevBg;

            // 全保存ボタン
            GUI.backgroundColor = new Color(0.3f, 0.85f, 0.5f);
            if (GUILayout.Button("Save All", GUILayout.Height(30)))
            {
                foreach (var emotion in EmotionNames)
                    SaveClip(emotion);
                EditorUtility.DisplayDialog("VEA", "全感情のアニメーションクリップを保存しました。", "OK");
            }
            GUI.backgroundColor = prevBg;

            EditorGUILayout.EndHorizontal();

            // プリセット
            EditorGUILayout.Space(5);
            if (GUILayout.Button("Milfy 推奨プリセットを読み込み"))
            {
                LoadMilfyPreset();
            }
        }

        private void SaveClip(string emotion)
        {
            var values = _emotionValues[emotion];
            string clipPath = $"{_animFolder}/VEA_{emotion}.anim";

            var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
            if (clip == null)
            {
                clip = new AnimationClip { name = $"VEA_{emotion}" };
                AssetDatabase.CreateAsset(clip, clipPath);
            }

            clip.ClearCurves();

            foreach (var kvp in values)
            {
                var curve = new AnimationCurve(new Keyframe(0, kvp.Value));
                clip.SetCurve(_faceMeshPath, typeof(SkinnedMeshRenderer),
                    $"blendShape.{kvp.Key}", curve);
            }

            EditorUtility.SetDirty(clip);
            AssetDatabase.SaveAssets();
        }

        private float[] _savedWeights;

        private void StartPreview()
        {
            if (_faceMesh != null && _faceMesh.sharedMesh != null)
            {
                int count = _faceMesh.sharedMesh.blendShapeCount;
                _savedWeights = new float[count];
                for (int i = 0; i < count; i++)
                    _savedWeights[i] = _faceMesh.GetBlendShapeWeight(i);
            }
            _isPreviewing = true;
            ApplyPreview();
        }

        private void StopPreview()
        {
            if (!_isPreviewing) return;
            _isPreviewing = false;

            if (_faceMesh == null || _faceMesh.sharedMesh == null) return;

            if (_savedWeights != null)
            {
                for (int i = 0; i < _savedWeights.Length && i < _faceMesh.sharedMesh.blendShapeCount; i++)
                    _faceMesh.SetBlendShapeWeight(i, _savedWeights[i]);
                _savedWeights = null;
            }

            SceneView.RepaintAll();
        }

        private void ApplyPreview()
        {
            if (_faceMesh == null || _faceMesh.sharedMesh == null) return;

            // まず全リセット
            for (int i = 0; i < _faceMesh.sharedMesh.blendShapeCount; i++)
                _faceMesh.SetBlendShapeWeight(i, 0);

            // 現在選択中の感情のBlendShapeを適用
            string emotion = EmotionNames[_selectedEmotion];
            var values = _emotionValues[emotion];

            var mesh = _faceMesh.sharedMesh;
            foreach (var kvp in values)
            {
                int idx = mesh.GetBlendShapeIndex(kvp.Key);
                if (idx >= 0)
                    _faceMesh.SetBlendShapeWeight(idx, kvp.Value);
            }

            SceneView.RepaintAll();
        }

        private void LoadMilfyPreset()
        {
            _emotionValues["Joy"] = new Dictionary<string, float>
            {
                { "eye_smile_1", 100f },
                { "mouth_smile_2", 100f },
                { "eyebrow_happy", 100f },
            };
            _emotionValues["Anger"] = new Dictionary<string, float>
            {
                { "eye_angry", 100f },
                { "eyebrow_angry", 100f },
                { "mouth_angry", 100f },
            };
            _emotionValues["Sadness"] = new Dictionary<string, float>
            {
                { "eye_sad", 100f },
                { "eyebrow_sad", 100f },
                { "mouth_straight", 100f },
            };
            _emotionValues["Surprise"] = new Dictionary<string, float>
            {
                { "eye_surprised", 100f },
                { "eyebrow_surprised", 100f },
                { "mouth_o_1", 100f },
            };
            _emotionValues["Neutral"] = new Dictionary<string, float>();
            _emotionValues["Disgust"] = new Dictionary<string, float>
            {
                { "eye_zito_1", 100f },
                { "eyebrow_seriously_1", 100f },
                { "mouth_straight", 80f },
            };
            _emotionValues["Fear"] = new Dictionary<string, float>
            {
                { "eye_surprised", 80f },
                { "eyebrow_confuse_1", 100f },
                { "mouth_o_1", 60f },
                { "extra_sweat", 100f },
            };

            if (_isPreviewing) ApplyPreview();
            Repaint();
        }

        private static string GetRelativePath(Transform root, Transform target)
        {
            var parts = new List<string>();
            var current = target;
            while (current != null && current != root)
            {
                parts.Add(current.name);
                current = current.parent;
            }
            parts.Reverse();
            return string.Join("/", parts);
        }

        private void LoadExistingClips()
        {
            foreach (var emotion in FullEmotions)
            {
                _emotionValues[emotion] = new Dictionary<string, float>();
                string clipPath = $"{_animFolder}/VEA_{emotion}.anim";
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (clip == null) continue;

                var bindings = AnimationUtility.GetCurveBindings(clip);
                foreach (var binding in bindings)
                {
                    if (!binding.propertyName.StartsWith("blendShape.")) continue;
                    string shapeName = binding.propertyName.Substring("blendShape.".Length);
                    if (shapeName.StartsWith("placeholder_")) continue;
                    var curve = AnimationUtility.GetEditorCurve(clip, binding);
                    if (curve != null && curve.keys.Length > 0)
                        _emotionValues[emotion][shapeName] = curve.keys[0].value;
                }
            }
        }
    }
}
