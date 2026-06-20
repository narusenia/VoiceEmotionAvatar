"""Emotion recognition module using emotion2vec."""

import logging
import os
import tempfile
import wave

import numpy as np

logger = logging.getLogger(__name__)

MODEL_ID = "iic/emotion2vec_plus_large"

EMOTIONS_SIMPLE = ["joy", "anger", "sadness", "surprise", "neutral"]
EMOTIONS_FULL = ["joy", "anger", "sadness", "surprise", "neutral", "disgust", "fear"]

LABEL_TO_SIMPLE = {
    "happy": "joy", "开心/happy": "joy",
    "angry": "anger", "生气/angry": "anger",
    "sad": "sadness", "难过/sad": "sadness",
    "surprised": "surprise", "吃惊/surprised": "surprise",
    "neutral": "neutral", "中立/neutral": "neutral",
    "disgusted": "anger", "厌恶/disgusted": "anger",
    "fearful": "surprise", "恐惧/fearful": "surprise",
    "other": "neutral", "其他/other": "neutral",
    "unknown": "neutral", "<unk>": "neutral",
}

LABEL_TO_FULL = {
    "happy": "joy", "开心/happy": "joy",
    "angry": "anger", "生气/angry": "anger",
    "sad": "sadness", "难过/sad": "sadness",
    "surprised": "surprise", "吃惊/surprised": "surprise",
    "neutral": "neutral", "中立/neutral": "neutral",
    "disgusted": "disgust", "厌恶/disgusted": "disgust",
    "fearful": "fear", "恐惧/fearful": "fear",
    "other": "neutral", "其他/other": "neutral",
    "unknown": "neutral", "<unk>": "neutral",
}


def get_emotions(full_mode: bool = False) -> list[str]:
    return EMOTIONS_FULL if full_mode else EMOTIONS_SIMPLE


def map_scores(labels: list[str], scores: list[float], full_mode: bool = False) -> dict[str, float]:
    emotions = EMOTIONS_FULL if full_mode else EMOTIONS_SIMPLE
    label_map = LABEL_TO_FULL if full_mode else LABEL_TO_SIMPLE
    result = {e: 0.0 for e in emotions}
    for label, score in zip(labels, scores):
        mapped = label_map.get(label, "neutral")
        result[mapped] += score
    total = sum(result.values())
    if total > 0:
        for k in result:
            result[k] /= total
    return result


def neutral_scores(full_mode: bool = False) -> dict[str, float]:
    emotions = EMOTIONS_FULL if full_mode else EMOTIONS_SIMPLE
    return {e: (1.0 if e == "neutral" else 0.0) for e in emotions}


class EmotionRecognizer:
    def __init__(self):
        self._model = None
        self.full_mode = False

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
            return neutral_scores(self.full_mode)

        tmp_path = self._write_wav(audio_chunk, sample_rate)

        try:
            res = self._model.generate(
                tmp_path,
                granularity="utterance",
                extract_embedding=False,
            )
        except Exception as e:
            logger.error("Emotion prediction failed: %s", e)
            return neutral_scores(self.full_mode)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if not res or not res[0].get("labels"):
            return neutral_scores(self.full_mode)

        return map_scores(res[0]["labels"], res[0]["scores"], self.full_mode)
