# Probe Frame Capture Fix Notes (2026-02-14)

This note documents the fixes for the "mobile cannot capture/send frames" regression.

## Root causes identified

1. `poseRef` was used but never defined in `ProbeView`, causing runtime errors during orientation updates.
2. `captureAndSend` used `video.videoWidth/videoHeight` and `drawImage(video, ...)` without defining `video`.
3. WebSocket URL carried `api_key` query params, which leaked key material into backend access logs.

## Fixes implemented

### 1) Fixed runtime refs in Probe
- File: `frontend/src/components/ProbeView.jsx`
- Added:
  - `const poseRef = useRef({ alpha: 0, beta: 0, gamma: 0 });`
- Kept state (`pose`) for UI display and ref (`poseRef`) for low-latency frame payload access.

### 2) Fixed frame capture variable usage
- File: `frontend/src/components/ProbeView.jsx`
- Added:
  - `const video = videoRef.current;`
- Updated capture logic to use `video` safely:
  - `video.videoWidth || 640`
  - `video.videoHeight || 480`
- Added guards:
  - return if no canvas context
  - return if width/height invalid

### 3) Removed API key from WebSocket URL
- File: `frontend/src/components/ProbeView.jsx`
- Changed socket URL to:
  - `.../ws/probe/${scanId}`
- Added auth message on WS open:
  - `{ type: 'auth', api_key: apiKey }`

### 4) Backend WebSocket auth support
- File: `main.py`
- Added support for `type: "auth"` messages in `/ws/probe/{client_id}`:
  - Updates in-memory Gemini client for that connection
  - Sends `{ type: "auth_ack" }` to probe
- Added frame-level fallback key handling (`data.api_key`) for compatibility.

## Validation

- Python compile check passed:
  - `python3 -m py_compile main.py`
- Frontend build passed:
  - `npm run build`

## Expected runtime behavior after fix

- Probe page no longer crashes on orientation updates.
- Capture loop can read valid video dimensions and send frames again.
- Backend logs no longer include API key in WS query string.
