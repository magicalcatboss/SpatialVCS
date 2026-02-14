"""
LLM Service - Gemini Client using the modern google.genai SDK.
Supports Chat, Structured Data Extraction, Image Description, Audio Transcription,
and SpatialVCS features (Spatial Description, Query Answering, Diff Analysis).
"""
from google import genai
from google.genai import types
import os
import json

class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.flash_model = "gemini-2.5-flash"
        self.pro_model = "gemini-2.5-flash"
        
    def chat(self, prompt: str, context: str = ""):
        """Simple chat completion."""
        try:
            full_prompt = f"Context: {context}\nUser: {prompt}" if context else prompt
            response = self.client.models.generate_content(
                model=self.flash_model,
                contents=full_prompt
            )
            return {"text": response.text}
        except Exception as e:
            return {"error": str(e)}

    def extract_structured_data(self, text: str, schema_description: str):
        """Agentic task: Extract JSON from text."""
        prompt = f"""
        Task: Extract data into the following schema: {schema_description}
        Input Text: {text}
        Return ONLY valid JSON.
        """
        try:
            response = self.client.models.generate_content(
                model=self.flash_model,
                contents=prompt
            )
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return {"data": clean_text}
        except Exception as e:
            return {"error": str(e)}

    def describe_image(self, image_bytes: bytes):
        """Multimodal: Describe an image for accessibility."""
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            response = self.client.models.generate_content(
                model=self.pro_model,
                contents=[
                    "Describe this image in detail for a visually impaired user. "
                    "Focus on people's expressions, body language, objects, and spatial layout.",
                    image_part
                ]
            )
            return {"description": response.text}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # SpatialVCS Methods
    # ============================================================

    def describe_for_spatial(self, image_bytes: bytes):
        """
        SpatialVCS: Analyze an image frame and return structured object data.
        Returns a JSON list of objects with name, position, color, and details.
        """
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            response = self.client.models.generate_content(
                model=self.pro_model,
                contents=[
                    "You are a spatial analysis AI. Analyze this image and list EVERY distinct object visible.\n"
                    "For each object, provide:\n"
                    "- name: what the object is (e.g. 'red ceramic mug', 'silver laptop')\n"
                    "- position: where in the frame (e.g. 'left side of desk', 'center of shelf')\n"
                    "- details: distinguishing features (color, brand, state)\n\n"
                    "Return ONLY valid JSON in this format:\n"
                    '{"scene_summary": "brief overall description", '
                    '"objects": [{"name": "...", "position": "...", "details": "..."}]}\n'
                    "Be thorough - include small items like keys, pens, cables, etc.",
                    image_part
                ]
            )
            # Parse the JSON response
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            try:
                parsed = json.loads(clean_text)
                return parsed
            except json.JSONDecodeError:
                return {"scene_summary": response.text, "objects": []}
        except Exception as e:
            return {"error": str(e)}

    def answer_spatial_query(self, query: str, search_results: list):
        """
        SpatialVCS: Generate a natural language answer from search results.
        Takes the user's question and the top matching records, returns a human-friendly response.
        """
        try:
            context = json.dumps(search_results, ensure_ascii=False, indent=2)
            prompt = (
                f"You are a helpful spatial memory assistant. The user scanned their space earlier "
                f"and now asks a question. Based on the search results from the spatial memory database, "
                f"give a clear, concise, and helpful answer.\n\n"
                f"User question: {query}\n\n"
                f"Search results (ranked by relevance):\n{context}\n\n"
                f"Answer naturally. Include the timestamp and position. "
                f"If not confident, say so. Keep it under 3 sentences."
            )
            response = self.client.models.generate_content(
                model=self.flash_model,
                contents=prompt
            )
            return {"answer": response.text.strip()}
        except Exception as e:
            return {"error": str(e)}

    def compare_spatial_diffs(self, before_objects: list, after_objects: list):
        """
        SpatialVCS: Compare two spatial snapshots and identify changes.
        Like 'git diff' but for physical spaces.
        """
        try:
            prompt = (
                "You are a spatial change detection AI. Compare these two snapshots of a space "
                "taken at different times.\n\n"
                f"BEFORE snapshot:\n{json.dumps(before_objects, ensure_ascii=False)}\n\n"
                f"AFTER snapshot:\n{json.dumps(after_objects, ensure_ascii=False)}\n\n"
                "Identify ALL changes. Return ONLY valid JSON:\n"
                '{"changes": [{"object": "name", "action": "moved|added|removed|modified", '
                '"from": "previous location or state", "to": "new location or state", '
                '"details": "brief explanation"}], '
                '"summary": "one sentence summary of changes", '
                '"change_count": number}'
            )
            response = self.client.models.generate_content(
                model=self.flash_model,
                contents=prompt
            )
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(clean_text)
            except json.JSONDecodeError:
                return {"summary": response.text, "changes": [], "change_count": 0}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # Original Methods (preserved)
    # ============================================================

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav"):
        """
        Speech-to-Text using Gemini's multimodal audio capability.
        Supports: audio/wav, audio/mp3, audio/webm, audio/ogg
        """
        try:
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            response = self.client.models.generate_content(
                model=self.flash_model,
                contents=[
                    "Transcribe the following audio precisely. "
                    "Return ONLY the transcribed text, nothing else.",
                    audio_part
                ]
            )
            return {"text": response.text.strip(), "source": "gemini"}
        except Exception as e:
            return {"error": str(e)}
