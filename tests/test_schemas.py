import unittest
import asyncio

from pydantic import TypeAdapter

from app.schemas.agent import ChatRequest
from app.schemas.detection import GeminiObject
from app.schemas.spatial import DiffEvent, SpatialQueryResponse
from app.services.cross_scan_matching import build_cross_scan_matches
from app.services.depth import DepthEstimator
from app.services.gemini_queue import GeminiDescribeJob, GeminiDescribeQueue
from app.services.identity import ObjectIdentityResolver
from app.services.label_fusion import LabelFusion
from app.services.scan_store import InMemoryScanStore
from app.services.pose import object_key_from_gemini_object
from app.schemas.ws_messages import ProbeInboundMessage


class SchemaContractTests(unittest.TestCase):
    def test_chat_request_defaults_are_backward_compatible(self):
        payload = ChatRequest(prompt="hello").model_dump()
        self.assertEqual(payload, {"prompt": "hello", "context": ""})

    def test_spatial_query_response_contract_shape(self):
        response = SpatialQueryResponse(
            query="where are my keys",
            answer="On the desk.",
            results=[
                {
                    "score": 0.98,
                    "description": "keys on desk",
                    "frame_url": "/spatial/frame/scan-1/frame.jpg",
                    "yolo_data": [{"label": "keys"}],
                }
            ],
        ).model_dump()
        self.assertEqual(set(response.keys()), {"query", "answer", "results"})
        self.assertEqual(
            set(response["results"][0].keys()),
            {"score", "description", "frame_url", "yolo_data", "position", "yolo_label", "track_id"},
        )

    def test_diff_event_preserves_from_alias(self):
        event = DiffEvent(
            type="MOVE",
            label="chair",
            distance=1.2,
            from_={"x": 0, "y": 0, "z": 0},
            to={"x": 1, "y": 0, "z": 0},
        ).model_dump(by_alias=True)
        self.assertIn("from", event)
        self.assertEqual(event["from"]["x"], 0)

    def test_ws_probe_union_accepts_frame_message(self):
        adapter = TypeAdapter(ProbeInboundMessage)
        parsed = adapter.validate_python(
            {
                "type": "frame",
                "image": "abc",
                "pose": {"alpha": 1, "beta": 2, "gamma": 3},
                "scan_id": "scan-1",
            }
        )
        self.assertEqual(parsed.type, "frame")
        self.assertEqual(parsed.pose.alpha, 1)

    def test_gemini_object_accepts_text_position_for_rest_path(self):
        obj = GeminiObject(name="mug", position="left side of desk", details="red ceramic mug")
        self.assertEqual(obj.position, "left side of desk")

    def test_scan_store_records_rest_gemini_objects_with_text_position(self):
        store = InMemoryScanStore()
        asyncio.run(
            store.record_gemini_objects(
                "scan-rest",
                [
                    {
                        "name": "mug",
                        "position": "left side of desk",
                        "details": "red ceramic mug",
                        "timestamp": 123.0,
                        "frame_path": "frame.jpg",
                    }
                ],
                123.0,
            )
        )
        record = asyncio.run(store.get("scan-rest"))
        self.assertIsNotNone(record)
        self.assertEqual(record.objects[0].position, "left side of desk")

    def test_gemini_object_key_uses_detection_key_rules(self):
        key = object_key_from_gemini_object(
            {
                "name": "red mug",
                "yolo_label": "cup",
                "track_id": 7,
                "bbox": [10, 20, 30, 40],
                "position": {"x": 0.1, "y": 0.2, "z": -1.2},
            }
        )
        self.assertEqual(key, "cup_7")

    def test_depth_estimator_prefers_payload_depth(self):
        estimator = DepthEstimator(default_depth_m=1.5)
        self.assertEqual(estimator.estimate({"center_depth": 2.25}), 2.25)
        self.assertEqual(estimator.estimate({}), 1.5)

    def test_identity_resolver_prefers_track_id(self):
        resolver = ObjectIdentityResolver(match_distance_m=0.6, stale_sec=3.0)
        key = resolver.resolve(
            "scan",
            {"label": "cup", "track_id": 3, "bbox": [1, 2, 3, 4], "position_3d": {"x": 0, "y": 0, "z": 0}},
            10.0,
        )
        self.assertEqual(key, "cup_3")

    def test_identity_resolver_matches_nearby_untracked_object(self):
        resolver = ObjectIdentityResolver(match_distance_m=0.6, stale_sec=3.0)
        first = resolver.resolve(
            "scan",
            {"label": "cup", "track_id": -1, "bbox": [0, 0, 20, 20], "position_3d": {"x": 0, "y": 0, "z": 0}},
            10.0,
        )
        second = resolver.resolve(
            "scan",
            {"label": "cup", "track_id": -1, "bbox": [40, 40, 60, 60], "position_3d": {"x": 0.1, "y": 0, "z": 0.1}},
            11.0,
        )
        self.assertEqual(first, second)

    def test_label_fusion_prefers_fresh_gemini_cache(self):
        result = LabelFusion().fuse(
            {"label": "cup", "confidence": 0.4},
            {"name": "red mug", "details": "ceramic", "updated_at": 10.0},
            12.0,
            20.0,
        )
        self.assertEqual(result.display_label, "red mug")
        self.assertEqual(result.label_source, "gemini_cache")

    def test_gemini_queue_dedupes_and_drops_when_full(self):
        queue = GeminiDescribeQueue(max_size=1, concurrency=1, timeout_sec=1)
        job = GeminiDescribeJob(
            scan_id="scan",
            object_key="cup_1",
            crop_bytes=b"crop",
            detection={"label": "cup"},
            frame_path="frame.jpg",
            timestamp=1.0,
            source="probe",
            gemini=object(),
            scan_store=object(),
            spatial_memory=object(),
        )
        other = GeminiDescribeJob(
            scan_id="scan",
            object_key="cup_2",
            crop_bytes=b"other",
            detection={"label": "cup"},
            frame_path="frame.jpg",
            timestamp=1.0,
            source="probe",
            gemini=object(),
            scan_store=object(),
            spatial_memory=object(),
        )
        self.assertTrue(queue.enqueue(job))
        self.assertFalse(queue.enqueue(job))
        self.assertFalse(queue.enqueue(other))

    def test_cross_scan_match_scores_same_label_nearby_candidate(self):
        matches = build_cross_scan_matches(
            [{"scan_id": "a", "object_key": "cup_1", "canonical_label": "cup", "last_position": {"x": 0, "y": 0, "z": 0}}],
            [{"scan_id": "b", "object_key": "cup_2", "canonical_label": "cup", "last_position": {"x": 0.1, "y": 0, "z": 0}}],
        )
        self.assertEqual(matches[0]["candidate_object_key"], "cup_2")
        self.assertGreater(matches[0]["similarity_score"], 0.9)


if __name__ == "__main__":
    unittest.main()
