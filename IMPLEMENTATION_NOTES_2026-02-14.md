# SpatialVCS Implementation Notes (2026-02-14)

This file summarizes the code changes implemented in this iteration.

## 1) Capture Pipeline Upgrades

### Mobile Probe now sends real device orientation
- File: `frontend/src/components/ProbeView.jsx`
- Added `deviceorientation` listener to collect `alpha/beta/gamma`.
- Added iOS permission request (`DeviceOrientationEvent.requestPermission`) when starting scan.
- Included `pose` in each frame payload sent via WebSocket.
- Added on-screen pose debug line (`POSE: alpha/beta/gamma`).

### Backend now uses orientation to build pose matrix
- File: `main.py`
- Added helper functions:
  - `_rotation_matrix_from_orientation(alpha, beta, gamma)`
  - `_pose_matrix_str_from_orientation(alpha, beta, gamma)`
- Replaced hardcoded identity pose in WebSocket scan flow with computed pose matrix per frame.

## 2) Spatial Diff changed to rule-based threshold logic

### Data preparation for rule-based diff
- File: `main.py`
- Extended scan record structure to store `detections` in addition to semantic objects.
- Added `_record_detections(scan_record, detections, timestamp)` to persist per-frame detection positions.
- Both WS scan and REST scan now record detections.

### Diff API contract + algorithm
- File: `main.py`
- `SpatialDiffRequest` now supports configurable `threshold` (meters), default `0.5`.
- Added:
  - `_euclidean_distance(a, b)` (SciPy first, math fallback)
  - `_latest_position_by_label(detections)`
- Replaced LLM-only diff with deterministic events:
  - `MOVE` when distance > threshold
  - `ADDED` when label appears only in after scan
  - `REMOVED` when label appears only in before scan
- New response shape includes:
  - `threshold`
  - `change_count`
  - `events`
  - `summary`

## 3) Dashboard Diff UI

- File: `frontend/src/components/DashboardView.jsx`
- Added scan list polling from `/spatial/scans`.
- Added `SPATIAL DIFF` panel:
  - before-scan selector
  - after-scan selector
  - threshold input
  - run button
- Added rendering of rule-based diff results (`MOVE/ADDED/REMOVED`) and summary.

## 4) Vector Store Migration to ChromaDB

- File: `services/spatial_memory.py`
- Replaced FAISS implementation with ChromaDB persistent collection (`data/chroma`).
- Preserved external interface:
  - `add_observation(text, meta)`
  - `search(query, k, scan_id=None)`
  - `save()`
  - `is_ready()`
- Added metadata serialization/deserialization to support nested structures in Chroma metadata.
- Query returns normalized score from Chroma distances.

## 5) Dependency updates

- File: `requirements.txt`
- Added `scipy` for threshold distance calculations in spatial diff.

## 6) Validation performed

- Python compile check passed:
  - `main.py`
  - `services/*.py`
- Frontend build passed:
  - `npm run build`

## Notes / Known follow-ups

- ChromaDB is now the active storage backend; existing FAISS files are no longer used by default.
- If SciPy import fails in some environments, diff still works via math fallback.
- Current 3D coordinates still rely on monocular approximation (no true depth sensor fusion yet).
