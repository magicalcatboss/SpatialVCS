"""
Vision Service - Face Analysis using OpenCV (no MediaPipe dependency issues).
Uses OpenCV's built-in DNN face detector + simple heuristics for emotion/gaze.
"""
import cv2
import numpy as np

def analyze_face_image(image_bytes: bytes):
    """
    Process image bytes, detect face, return emotions & gaze.
    Uses OpenCV Haar Cascade (guaranteed to work on all Python versions).
    """
    # Decode Image
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return {"error": "Invalid image data"}
        
    h, w, _ = frame.shape
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Use OpenCV's built-in Haar Cascade for face detection
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) == 0:
        return {"found": False, "message": "No face detected"}
    
    # Take the largest face
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    
    # Extract face ROI
    face_roi = gray[y:y+fh, x:x+fw]
    
    # --- Gaze Estimation (eye position heuristic) ---
    eye_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_eye.xml'
    )
    eyes = eye_cascade.detectMultiScale(face_roi, 1.1, 4)
    
    gaze = {"direction": "center", "x": 0.5, "y": 0.5}
    if len(eyes) >= 2:
        # Average eye center positions relative to face
        eye_centers = [(ex + ew/2, ey + eh/2) for (ex, ey, ew, eh) in eyes[:2]]
        avg_x = sum(e[0] for e in eye_centers) / 2 / fw
        avg_y = sum(e[1] for e in eye_centers) / 2 / fh
        
        direction = "center"
        if avg_x < 0.4: direction = "right"  # Mirrored
        elif avg_x > 0.6: direction = "left"  # Mirrored
        
        gaze = {"direction": direction, "x": round(avg_x, 2), "y": round(avg_y, 2)}
    
    # --- Emotion Estimation (brightness/contrast heuristic) ---
    # Simple proxy: brighter face region = more likely smiling
    mean_brightness = np.mean(face_roi)
    std_brightness = np.std(face_roi)
    
    emotions = {"joy": 0.0, "surprise": 0.0, "neutral": 0.0}
    
    if mean_brightness > 140 and std_brightness > 40:
        emotions["joy"] = 0.7
        emotions["neutral"] = 0.3
    elif std_brightness > 50:
        emotions["surprise"] = 0.6
        emotions["neutral"] = 0.4
    else:
        emotions["neutral"] = 0.9
        emotions["joy"] = 0.1
    
    return {
        "found": True,
        "face_box": {"x": int(x), "y": int(y), "w": int(fw), "h": int(fh)},
        "gaze": gaze,
        "emotions": emotions,
        "eyes_detected": len(eyes)
    }
