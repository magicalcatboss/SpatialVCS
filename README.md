# SpatialVCS API

**Spatial Version Control System** — Search reality like the web, manage space like code.

Built on the Gemini Toolkit, extended with spatial AI capabilities.

## Features

### Spatial AI (NEW)
- **Spatial Scan** (`POST /spatial/scan/frame`): Stream frames → AI detects & remembers every object
- **Semantic Query** (`POST /spatial/query`): Ask "Where are my keys?" → Get annotated frame + position
- **Spatial Diff** (`POST /spatial/diff`): Compare two scans → "Keys moved from desk to entrance"
- **Memory Browser** (`GET /spatial/memory/{scan_id}`): View all remembered objects

### Original Toolkit (Preserved)
- **Vision**: Face Detection, Emotion Recognition, Gaze Tracking (OpenCV)
- **Scene Description**: Gemini Vision multimodal image analysis
- **Audio**: Text-to-Speech (gTTS) + Speech-to-Text (Gemini)
- **Agent**: Chat and structured data extraction (Gemini Flash)

## Setup

1. **Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API Key**:
   Create a `.env` file:
   ```
   GEMINI_API_KEY=your_key_here
   ```

3. **Run Server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Open Docs**: Visit `http://localhost:8000/docs`

5. **Run Frontend (HTTPS for mobile camera access)**:
   ```bash
   cd frontend
   npm install
   npm run dev -- --host 0.0.0.0
   ```
   Then open the Vite URL from your laptop or Tailscale IP on phone.

## API Endpoints

### Spatial Module
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/spatial/scan/frame` | Upload single frame, create/update spatial memory |
| POST | `/spatial/query` | Search objects by natural language |
| POST | `/spatial/diff` | Compare two scans for changes |
| GET | `/spatial/scans` | List all scan records |
| GET | `/spatial/memory/{scan_id}` | View objects in a scan |

### Vision Module
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/vision/face-analysis` | Face detection + emotion + gaze |
| POST | `/vision/describe` | Gemini scene description |

### Audio Module
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/audio/speak` | Text-to-Speech (MP3 stream) |
| POST | `/audio/transcribe` | Speech-to-Text (Gemini) |

### Agent Module
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/chat` | Gemini chat completion |
| POST | `/agent/extract` | Structured data extraction |

## Architecture

```
SpatialVCS API (FastAPI)
├── /spatial/*          ← NEW: Spatial memory & search
│   ├── video_processor    (OpenCV + YOLOv8)
│   ├── spatial_memory     (FAISS vector search)
│   └── frame_annotator    (Bounding box overlay)
├── /vision/*           ← Face analysis + Scene description
├── /audio/*            ← TTS + STT
└── /agent/*            ← Chat + Extraction
```

## Tech Stack
- **Backend**: FastAPI + Python
- **LLM**: Google Gemini 2.5 Flash
- **Object Detection**: YOLOv8 (ultralytics)
- **Vector Search**: FAISS / ChromaDB
- **Embeddings**: Sentence Transformers
- **TTS**: gTTS / OpenAI TTS
