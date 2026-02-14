# SpatialVCS: Project Specification for AI Agents

> **Usage**: Copy the relevant section below and paste it into your AI coding assistant (Cursor, Windsurf, GitHub Copilot) to generate your part of the project.

---

## 🌍 Global Context (For All Agents)

**Project Name**: SpatialVCS (Spatial Version Control System)
**Concept**: A "Git for Reality" that scans physical spaces, indexes objects with 3D coordinates, and tracks changes over time.
**Tech Stack**:
- **Backend**: Python (FastAPI, WebSocket, YOLOv8, Gemini Flash 2.5, FAISS)
- **Frontend (Mobile)**: React + Vite (WebXR/Canvas for camera access)
- **Frontend (Desktop)**: React + Vite + Three.js (3D Visualization)
- **Protocol**: WebSocket (Socket.io or native `ws://`) for real-time data streaming.

---

## 📱 Role A: Mobile Probe (The "Scanner")

**User Goal**: Build a lightweight mobile web app to capture video frames and device orientation.

**Prompt for AI**:
```markdown
You are an expert Frontend Developer specializing in Mobile Web and WebXR.
Create a React + Vite application called "spatial-probe" with the following requirements:

1.  **Camera Access**: Use `navigator.mediaDevices.getUserMedia` to stream the rear camera to a `<video>` element (hidden or visible).
2.  **Frame Capture**: Use a HTML5 Canvas to capture a JPEG frame from the video stream every 1000ms (1fps).
3.  **Sensor Access**: Use `DeviceOrientationEvent` to capture `alpha` (compass), `beta` (tilt), and `gamma` (roll).
    - Note: You must implement a "Start" button to request permission on iOS Safari (`DeviceOrientationEvent.requestPermission()`).
4.  **WebSocket Client**: 
    - Connect to `ws://YOUR_MAC_IP:8000/ws/probe/{client_id}`.
    - Every second, send a JSON packet:
      {
        "type": "frame",
        "scan_id": "session_123",
        "timestamp": 1234567890,
        "pose": { "alpha": 0, "beta": 0, "gamma": 0 },
        "image": "base64_encoded_jpeg_string..."
      }
5.  **UI**: Minimalist "Cyberpunk" style. Large "Start Scan" button. Real-time status log.

Stack: React, Vite, TailwindCSS.
```

---

## 🧠 Role B: Backend Brain (The "Server")

**User Goal**: Handle WebSocket streams, process images with AI, and manage spatial memory.

**Prompt for AI**:
```markdown
You are an expert Python Backend Developer.
Extend the existing FastAPI application to handle real-time spatial data streams.

1.  **WebSocket Manager**:
    - Create a `ConnectionManager` class to handle two types of clients: `Probe` (Mobile) and `Dashboard` (Desktop).
    - Endpoint: `/ws/probe/{client_id}` -> Receives frames.
    - Endpoint: `/ws/dashboard/{client_id}` -> Broadcasts results.
2.  **Processing Pipeline**:
    - When a frame arrives from `Probe`:
      a. Decode Base64 image to OpenCV format.
      b. Run YOLOv8 detection (already implemented in `video_processor.py`).
      c. (Async) Send to Gemini for "Spatial Description" (already in `llm.py`).
      d. Store in Vector DB (already in `spatial_memory.py`).
      e. **Broadcast** the detection result immediately to all connected `Dashboard` clients.
3.  **Data Contract (Broadcast)**:
    - Send this JSON to Dashboard:
      {
        "type": "update",
        "objects": [
          { "label": "cup", "confidence": 0.95, "position": { "x": 0.5, "y": 0.2, "z": -1.5 } }  // Simulate Z depth if missing
        ],
        "log": "Detected Red Cup at 12:00:01"
      }
```

---

## 💻 Role C: Desktop Dashboard (The "Viewer")

**User Goal**: Visualize the spatial data in real-time 3D.

**Prompt for AI**:
```markdown
You are an expert Creative Developer specializing in React and Three.js.
Create a "Mission Control" dashboard for SpatialVCS.

1.  **3D Scene (Three.js / React-Three-Fiber)**:
    - A dark, grid-based 3D environment (like a Tron grid).
    - Camera: OrbitControls.
    - Represents the user (Probe) as a Cone mesh that rotates based on incoming `alpha/beta/gamma` data.
2.  **Real-time Updates**:
    - Connect to `ws://localhost:8000/ws/dashboard/admin`.
    - Listen for `update` messages.
    - When an object is detected, spawn a **Text Label** or **3D Icon** at its estimated position in the 3D scene.
3.  **Search Interface**:
    - A floating search bar overlay.
    - On submit, call `POST /spatial/query` (already exists).
    - Highlight the matching objects in the 3D scene (e.g., draw a red line to them).
4.  **UI**: Glassmorphism, dark mode, futuristic HUD style.

Stack: React, Vite, Three.js, React-Three-Fiber, TailwindCSS.
```

---
