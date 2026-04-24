from dataclasses import dataclass

from app.services.pose import euclidean_distance, object_key_from_detection


@dataclass
class ObjectState:
    object_key: str
    label: str
    position: dict
    last_seen: float


class ObjectIdentityResolver:
    def __init__(self, match_distance_m: float = 0.6, stale_sec: float = 3.0):
        self.match_distance_m = match_distance_m
        self.stale_sec = stale_sec
        self._states: dict[str, dict[str, ObjectState]] = {}

    def resolve(self, scan_id: str, detection: dict, timestamp: float) -> str:
        track_id = int(detection.get("track_id", -1))
        if track_id > -1:
            object_key = object_key_from_detection(detection)
            self._remember(scan_id, object_key, detection, timestamp)
            return object_key

        label = detection.get("yolo_label") or detection.get("label") or "object"
        position = detection.get("position_3d") or {}
        candidates = []
        for state in self._states.get(scan_id, {}).values():
            if state.label != label:
                continue
            if timestamp - state.last_seen > self.stale_sec:
                continue
            distance = euclidean_distance(position, state.position)
            if distance <= self.match_distance_m:
                candidates.append((distance, state.object_key))

        if candidates:
            object_key = min(candidates, key=lambda item: item[0])[1]
        else:
            object_key = object_key_from_detection(detection)

        self._remember(scan_id, object_key, detection, timestamp)
        return object_key

    def _remember(self, scan_id: str, object_key: str, detection: dict, timestamp: float) -> None:
        label = detection.get("yolo_label") or detection.get("label") or "object"
        self._states.setdefault(scan_id, {})[object_key] = ObjectState(
            object_key=object_key,
            label=label,
            position=detection.get("position_3d") or {},
            last_seen=timestamp,
        )
        self._prune(scan_id, timestamp)

    def _prune(self, scan_id: str, timestamp: float) -> None:
        states = self._states.get(scan_id, {})
        stale = [key for key, state in states.items() if timestamp - state.last_seen > self.stale_sec * 3]
        for key in stale:
            states.pop(key, None)
