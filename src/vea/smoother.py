"""Emotion smoothing with hysteresis."""

from vea.emotion import VEA_EMOTIONS


class EmotionSmoother:
    def __init__(self, lerp_speed: float = 0.15, hysteresis_threshold: float = 0.1):
        self._lerp_speed = lerp_speed
        self._hysteresis = hysteresis_threshold
        self._instant_mode = False
        self._instant_threshold = 0.4
        self._instant_smoothing = 0.5
        self._current: dict[str, float] = {e: 0.0 for e in VEA_EMOTIONS}
        self._current["neutral"] = 1.0
        self._target: dict[str, float] = {e: 0.0 for e in VEA_EMOTIONS}
        self._target["neutral"] = 1.0
        self._dominant: str = "neutral"

    @property
    def current(self) -> dict[str, float]:
        return self._current.copy()

    @property
    def dominant(self) -> str:
        return self._dominant

    def set_target(self, raw_scores: dict[str, float]) -> None:
        new_dominant = max(raw_scores, key=raw_scores.get)
        if self._instant_mode:
            if raw_scores[new_dominant] >= self._instant_threshold:
                self._dominant = new_dominant
                self._target = {e: 0.0 for e in VEA_EMOTIONS}
                self._target[new_dominant] = 1.0
            else:
                self._dominant = "neutral"
                self._target = {e: 0.0 for e in VEA_EMOTIONS}
                self._target["neutral"] = 1.0
        else:
            if new_dominant != self._dominant:
                if raw_scores[new_dominant] - raw_scores.get(self._dominant, 0.0) > self._hysteresis:
                    self._dominant = new_dominant
            self._target = dict(raw_scores)

    def tick(self) -> dict[str, float]:
        speed = self._instant_smoothing if self._instant_mode else self._lerp_speed
        for emotion in VEA_EMOTIONS:
            target = self._target.get(emotion, 0.0)
            self._current[emotion] += (target - self._current[emotion]) * speed
        if not self._instant_mode:
            total = sum(self._current.values())
            if total > 0:
                for k in self._current:
                    self._current[k] /= total
        return self._current.copy()

    def update(self, raw_scores: dict[str, float]) -> dict[str, float]:
        new_dominant = max(raw_scores, key=raw_scores.get)

        if self._instant_mode:
            if raw_scores[new_dominant] >= self._instant_threshold:
                self._dominant = new_dominant
                target = {e: 0.0 for e in VEA_EMOTIONS}
                target[new_dominant] = 1.0
            else:
                self._dominant = "neutral"
                target = {e: 0.0 for e in VEA_EMOTIONS}
                target["neutral"] = 1.0
            for emotion in VEA_EMOTIONS:
                self._current[emotion] += (target[emotion] - self._current[emotion]) * self._instant_smoothing
            return self._current.copy()

        if new_dominant != self._dominant:
            if raw_scores[new_dominant] - raw_scores.get(self._dominant, 0.0) > self._hysteresis:
                self._dominant = new_dominant

        for emotion in VEA_EMOTIONS:
            target = raw_scores.get(emotion, 0.0)
            self._current[emotion] += (target - self._current[emotion]) * self._lerp_speed

        total = sum(self._current.values())
        if total > 0:
            for k in self._current:
                self._current[k] /= total

        return self._current.copy()

    def set_lerp_speed(self, speed: float) -> None:
        self._lerp_speed = max(0.01, min(1.0, speed))

    def set_hysteresis(self, threshold: float) -> None:
        self._hysteresis = max(0.0, min(1.0, threshold))

    def set_instant_mode(self, enabled: bool) -> None:
        self._instant_mode = enabled

    def set_instant_threshold(self, threshold: float) -> None:
        self._instant_threshold = max(0.1, min(0.9, threshold))

    def set_instant_smoothing(self, value: float) -> None:
        self._instant_smoothing = max(0.05, min(1.0, value))

    def reset(self) -> None:
        self._current = {e: 0.0 for e in VEA_EMOTIONS}
        self._current["neutral"] = 1.0
        self._target = {e: 0.0 for e in VEA_EMOTIONS}
        self._target["neutral"] = 1.0
        self._dominant = "neutral"
