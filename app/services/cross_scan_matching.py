from app.services.pose import euclidean_distance


def score_spatial_object_match(source: dict, candidate: dict) -> float:
    label_score = 1.0 if (source.get("canonical_label") or source.get("yolo_label")) == (candidate.get("canonical_label") or candidate.get("yolo_label")) else 0.0
    source_pos = source.get("last_position") or {}
    candidate_pos = candidate.get("last_position") or {}
    try:
        distance = euclidean_distance(source_pos, candidate_pos)
    except Exception:
        distance = 999.0
    position_score = max(0.0, 1.0 - min(distance, 3.0) / 3.0)
    return round((label_score * 0.65) + (position_score * 0.35), 4)


def build_cross_scan_matches(source_objects: list[dict], candidate_objects: list[dict], limit: int = 5) -> list[dict]:
    matches = []
    for source in source_objects:
        ranked = sorted(
            (
                {
                    "source_object_key": source.get("object_key", ""),
                    "candidate_object_key": candidate.get("object_key", ""),
                    "candidate_scan_id": candidate.get("scan_id", ""),
                    "label": candidate.get("canonical_label") or candidate.get("yolo_label") or "",
                    "similarity_score": score_spatial_object_match(source, candidate),
                }
                for candidate in candidate_objects
                if candidate.get("scan_id") != source.get("scan_id")
            ),
            key=lambda item: item["similarity_score"],
            reverse=True,
        )
        matches.extend(ranked[:limit])
    return matches
