from dataclasses import dataclass


@dataclass
class LabelFusionResult:
    display_label: str
    canonical_label: str
    details: str
    label_confidence: float
    label_source: str


class LabelFusion:
    def fuse(self, detection: dict, cached: dict | None, timestamp: float, ttl_sec: float) -> LabelFusionResult:
        yolo_label = detection.get("label") or detection.get("yolo_label") or "object"
        yolo_conf = float(detection.get("confidence", 0.0))
        gemini_name = detection.get("gemini_name")
        gemini_details = detection.get("gemini_details", "")

        if cached and (float(timestamp) - float(cached.get("updated_at", 0.0)) <= ttl_sec):
            return LabelFusionResult(
                display_label=cached.get("name") or yolo_label,
                canonical_label=cached.get("name") or yolo_label,
                details=cached.get("details", gemini_details),
                label_confidence=max(yolo_conf, 0.75),
                label_source="gemini_cache",
            )

        if gemini_name:
            return LabelFusionResult(
                display_label=gemini_name,
                canonical_label=gemini_name if yolo_conf >= 0.35 else yolo_label,
                details=gemini_details,
                label_confidence=max(yolo_conf, 0.8),
                label_source="gemini",
            )

        return LabelFusionResult(
            display_label=yolo_label,
            canonical_label=yolo_label,
            details="",
            label_confidence=yolo_conf,
            label_source="yolo",
        )
