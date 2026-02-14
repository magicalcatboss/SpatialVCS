# 🏗️ SpatialVCS System Architecture Review

Here is the complete logic breakdown of your "Spatial Version Control System".

## 1. The Core Concept (Metaphor)
*   **Git for Reality**: We treat physical space like code.
*   **Commit** = Scanning a room.
*   **Diff** = Detecting moved objects.
*   **Search** = "Ctrl+F" for real life objects.

## 2. System Components

### 📱 A. The Probe (Mobile Frontend)
*   **Role**: The "Eye" & "Sensor".
*   **Logic**:
    1.  **Camera**: Captures video frames (30fps).
    2.  **Gyroscope**: Captures device orientation (Alpha/Beta/Gamma).
    3.  **WebSocket**: Streams `Frame + Pose` to backend in real-time.
    4.  **No Processing**: It’s dumb. It just sends raw data to the brain.

### 🧠 B. The Brain (Backend - FastAPI)
*   **Role**: Processing Center.
*   **Pipeline**:
    1.  **Vision (YOLOv8)**:
        *   Fast detection (ms). Locates objects (Cup, Chair, Person).
        *   Output: 2D Bounding Boxes.
    2.  **Spatial Math**:
        *   Combines `2D Box` + `Phone Orientation` + `Estimated Depth`.
        *   Calculates **3D World Coordinates (X, Y, Z)**.
    3.  **Semantic Memory (Gemini)**:
        *   **Throttled**: Runs every ~3 seconds (to save API quota).
        *   **Action**: Looks at the whole image and writes a poetic description ("A cluttered desk with a red ceramic mug and a silver MacBook").
        *   **Storage**: Embeds this text into **ChromaDB** (Vector Database).

### 💻 C. The Command Center (Desktop Frontend)
*   **Role**: Visualization & Control.
*   **Features**:
    1.  **Live View**: Shows real-time 3D coordinates.
    2.  **Semantic Search**:
        *   Input: "Where is my vape?"
        *   Process: Embedding Search -> Gemini RAG (Retrieval Augmented Generation).
        *   Output: "I saw it on the dining table 5 minutes ago."
    3.  **Spatial Diff**:
        *   **Algorithm**: `EuclideanDistance(Object_A_Old, Object_A_New) > Threshold`.
        *   **Live Mode**: Compares `Current Frame` vs `Database Snapshot` in real-time.

## 3. Data Flow Example

**Scenario: "I moved my cup."**

1.  **Baseline**: You scanned the table earlier (Scan ID: `SCN-100`).
    *   Database knows: `Cup` is at `(1.0, 0.5, 0.0)`.
2.  **Event**: You move the cup to the right.
3.  **Live Scan**: You point the camera at the new location.
    *   YOLO sees `Cup`.
    *   Math calculates new position: `(1.8, 0.5, 0.0)`.
4.  **Comparison**:
    *   `Distance = sqrt((1.8-1.0)^2 + ...)` = **0.8 meters**.
    *   Threshold is 0.5m.
5.  **Result**:
    *   System flags **MOVE** event.
    *   Dashboard updates instantly.

---

This architecture is **Hybrid**:
*   **Local AI (YOLO)** for Speed (60fps).
*   **Cloud AI (Gemini)** for Intelligence (Understanding/Search).
*   **Geometric Logic** for Precision (Diff).
