import math


class DepthEstimator:
    def __init__(self, default_depth_m: float = 1.5):
        self.default_depth_m = default_depth_m

    def estimate(self, frame_payload: dict) -> float:
        for key in ("center_depth", "depth", "estimated_depth"):
            value = frame_payload.get(key)
            try:
                depth = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(depth) and depth > 0:
                return depth
        return self.default_depth_m
