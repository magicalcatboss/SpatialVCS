import unittest
import asyncio

from pydantic import TypeAdapter

from app.schemas.agent import ChatRequest
from app.schemas.detection import GeminiObject
from app.schemas.spatial import DiffEvent, SpatialQueryResponse
from app.services.scan_store import InMemoryScanStore
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
            {"score", "description", "frame_url", "yolo_data"},
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


if __name__ == "__main__":
    unittest.main()
