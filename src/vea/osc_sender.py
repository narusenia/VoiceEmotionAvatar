"""OSC parameter sender for VRChat."""

import logging

from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)


class OscSender:
    def __init__(self, ip: str = "127.0.0.1", port: int = 9000, prefix: str = "VEA"):
        self._ip = ip
        self._port = port
        self._prefix = prefix
        self._client: SimpleUDPClient | None = None

    def connect(self) -> None:
        self._client = SimpleUDPClient(self._ip, self._port)
        logger.info("OSC client connected to %s:%d", self._ip, self._port)

    def send(self, scores: dict[str, float]) -> None:
        if self._client is None:
            return
        for emotion, value in scores.items():
            address = f"/avatar/parameters/{self._prefix}_{emotion.capitalize()}"
            try:
                self._client.send_message(address, float(value))
            except Exception as e:
                logger.error("OSC send error (%s): %s", address, e)

    def update_target(self, ip: str, port: int) -> None:
        self._ip = ip
        self._port = port
        self._client = SimpleUDPClient(ip, port)
        logger.info("OSC target updated to %s:%d", ip, port)

    def close(self) -> None:
        self._client = None
