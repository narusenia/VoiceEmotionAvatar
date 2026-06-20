"""Emotion recognition module using emotion2vec."""

import logging
import tempfile
import wave

import numpy as np

logger = logging.getLogger(__name__)

MODEL_ID = "iic/emotion2vec_plus_large"

# emotion2vec outputs 9 labels:
# 0:angry 1:disgusted 2:fearful 3:happy 4:neutral 5:other 6:sad 7:surprised 8:unknown
EMOTION_LABELS_9 = [
    "angry", "disgusted", "fearful", "happy", "neutral",
    "other", "sad", "surprised", "unknown",
]

# VEA 5-emotion mapping from emotion2vec's 9 labels
VEA_EMOTIONS = ["joy", "anger", "sadness", "surprise", "neutral"]

LABEL_TO_VEA = {
    "happy": "joy",
    "angry": "anger",
    "sad": "sadness",
    "surprised": "surprise",
    "neutral": "neutral",
    "disgusted": "anger",
    "fearful": "surprise",
    "other": "neutral",
    "unknown": "neutral",
}


def _map_scores_to_vea(labels: list[str], scores: list[float]) -> dict[str, float]:
    vea_scores = {e: 0.0 for e in VEA_EMOTIONS}
    for label, score in zip(labels, scores):
        vea_emotion = LABEL_TO_VEA.get(label, "neutral")
        vea_scores[vea_emotion] += score
    total = sum(vea_scores.values())
    if total > 0:
        for k in vea_scores:
            vea_scores[k] /= total
    return vea_scores


class EmotionRecognizer:
    def __init__(self):
        self._model = None

    def load_model(self) -> None:
        from funasr import AutoModel
        logger.info("Loading emotion2vec model: %s", MODEL_ID)
        self._model = AutoModel(model=MODEL_ID, disable_update=True)
        logger.info("Model loaded successfully")

    def predict(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> dict[str, float]:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if np.max(np.abs(audio_chunk)) < 1e-6:
            return {e: (1.0 if e == "neutral" else 0.0) for e in VEA_EMOTIONS}

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp_path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                pcm = (audio_chunk * 32767).astype(np.int16)
                wf.writeframes(pcm.tobytes())

        try:
            res = self._model.generate(
                tmp_path,
                granularity="utterance",
                extract_embedding=False,
            )
        except Exception as e:
            logger.error("Emotion prediction failed: %s", e)
            return {e_name: (1.0 if e_name == "neutral" else 0.0) for e_name in VEA_EMOTIONS}
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if not res or not res[0].get("labels"):
            return {e: (1.0 if e == "neutral" else 0.0) for e in VEA_EMOTIONS}

        labels = res[0]["labels"]
        scores = res[0]["scores"]
        return _map_scores_to_vea(labels, scores)
