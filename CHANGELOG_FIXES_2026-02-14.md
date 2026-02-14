# SpatialVCS Stability + Indexing Fixes (2026-02-14)

## Scope
This change set targets the four high-priority issues discussed in review:
1. Gemini semantic indexing was gated by YOLO detections.
2. 8m + frequent sampling could overload backend and destabilize WebSocket.
3. Probe capture loop lacked backpressure.
4. Dashboard persistence keying could flicker when `track_id = -1`.

## Files Changed
- `main.py`
- `services/video_processor.py`
- `frontend/src/components/ProbeView.jsx`
- `frontend/src/components/DashboardView.jsx`

## What Changed

### 1) Gemini indexing decoupled from detections (P1)
In `main.py` websocket probe pipeline:
- Gemini call condition changed from:
  - `if gemini and detections and (frame_count % 3 == 1)`
- to:
  - `if gemini and (frame_count % GEMINI_FRAME_STRIDE == 1)`
- Added `GEMINI_FRAME_STRIDE` env config (`SPATIAL_GEMINI_FRAME_STRIDE`, default `3`).

Effect:
- Scenes with no current YOLO hits can still generate semantic records (if Gemini returns objects), preventing “scanned but no searchable result”.

### 2) 8m load controls and detection throttling (P2)
In `main.py`:
- Added `YOLO_FRAME_STRIDE` (`SPATIAL_YOLO_FRAME_STRIDE`, default `1`).
- For frames not selected by stride:
  - Save frame path only (`run_detection=False`) to reduce heavy inference load.

In `services/video_processor.py`:
- Added inference tuning envs:
  - `SPATIAL_MODEL_IMGSZ` (default `640`)
  - `SPATIAL_DETECT_CONF` (default `0.35`)
  - `SPATIAL_MAX_DETECTIONS` (default `30`)
  - `SPATIAL_USE_TRACKING` (default enabled)
- Kept 8m support while allowing fallback and runtime tuning.

Effect:
- Maintains 8m quality path but provides practical levers to stabilize latency and avoid WS jitter under load.

### 3) Probe backpressure + camera readiness (P2)
In `frontend/src/components/ProbeView.jsx`:
- Added in-flight gate (`inFlightRef`) so a new frame is not sent until ack/error/auth_ack arrives.
- Added 4s timeout fallback to release in-flight lock if ack is lost.
- Added video readiness guard (`video.readyState < 2` or zero dimensions -> skip send).
- Reduced per-frame logging pressure (log every 3 sends).

Effect:
- Prevents frame pile-up and reduces reconnect/disconnect oscillation.

### 4) Stable persistence IDs for untracked objects (P2)
In `main.py` and `DashboardView.jsx`:
- Replaced random fallback keys for `track_id = -1` with deterministic cell-based keys:
  - based on label + bbox center bucket (+ z bucket)
- Normalized state vector to consistent render shape (`id`, `label`, `confidence`, `position`).
- Increased persistence prune window from `500ms` to `1800ms` to reduce flicker.

Effect:
- UI cards remain stable between neighboring frames even when tracker temporarily drops IDs.

### 5) Reset endpoint auth alignment
`/spatial/reset` already required API key in backend. Dashboard wipe action now sends `x-api-key` header.

Effect:
- Frontend action matches backend auth requirement and avoids false “wipe failed”.

## New/Updated Runtime Knobs
- `SPATIAL_YOLO_FRAME_STRIDE` (default `1`)
- `SPATIAL_GEMINI_FRAME_STRIDE` (default `3`)
- `SPATIAL_FALLBACK_KEY_BUCKET_PX` (default `96`)
- `SPATIAL_TARGET_CLASSES` (broader indoor-oriented default)
- `SPATIAL_MODEL_IMGSZ` (default `640`)
- `SPATIAL_DETECT_CONF` (default `0.35`)
- `SPATIAL_MAX_DETECTIONS` (default `30`)
- `SPATIAL_USE_TRACKING` (default `1`)

## Verification Performed
- Python syntax check:
  - `python3 -m py_compile main.py services/video_processor.py`
- Frontend production build:
  - `npm run build` (Vite build successful)

## Notes
- This update is tuned for “stable demo first” while keeping 8m available.
- If you still see backend pressure, increase `SPATIAL_YOLO_FRAME_STRIDE` to `2` before reducing model size.
