"""Emotion recognition module using emotion2vec."""

import logging
import os
import tempfile
import wave

import numpy as np

logger = logging.getLogger(__name__)

MODEL_ID = "iic/emotion2vec_plus_large"

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
        self._log_count = 0

    def load_model(self) -> None:
        logger.info("FunASR をインポート中...")
        from funasr import AutoModel
        logger.info("emotion2vec モデルをロード中: %s (初回はダウンロードが入ります)", MODEL_ID)
        self._model = AutoModel(model=MODEL_ID, disable_update=True)
        logger.info("モデルロード完了 - 推論準備OK")

    def _write_wav(self, audio_chunk: np.ndarray, sample_rate: int) -> str:
        fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with wave.open(tmp_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            pcm = (audio_chunk * 32767).astype(np.int16)
            wf.writeframes(pcm.tobytes())
        return tmp_path

    def predict(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> dict[str, float]:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if np.max(np.abs(audio_chunk)) < 1e-6:
            return {e: (1.0 if e == "neutral" else 0.0) for e in VEA_EMOTIONS}

        tmp_path = self._write_wav(audio_chunk, sample_rate)

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
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        self._log_count += 1
        if self._log_count <= 5 or self._log_count % 20 == 0:
            logger.info("Model raw output: %s", res)

        if not res or not res[0].get("labels"):
            if not res:
                logger.warning("Model returned empty result")
            elif res and not res[0].get("labels"):
                logger.warning("Model result has no 'labels' key. Keys: %s", list(res[0].keys()))
            return {e: (1.0 if e == "neutral" else 0.0) for e in VEA_EMOTIONS}

        labels = res[0]["labels"]
        scores = res[0]["scores"]

        if self._log_count <= 5:
            logger.info("Labels: %s", labels)
            logger.info("Scores: %s", [f"{s:.3f}" for s in scores])

        return _map_scores_to_vea(labels, scores)
