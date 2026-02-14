import cv2
import numpy as np
import os

def annotate_frame(frame_path: str, bbox: list, label: str, distance: float = None):
    """
    Draw a red bounding box and label on a frame.
    Returns the path to the NEW annotated image.
    """
    if not os.path.exists(frame_path):
        return None
        
    img = cv2.imread(frame_path)
    if img is None:
        return None
        
    x1, y1, x2, y2 = map(int, bbox)
    
    # 1. Draw Red Box (BGR)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
    
    # 2. Add Label Background
    text = label
    if distance:
        text += f" ({distance:.1f}m)"
        
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    cv2.rectangle(img, (x1, y1 - 30), (x1 + w, y1), (0, 0, 255), -1)
    
    # 3. Add White Text
    cv2.putText(img, text, (x1, y1 - 8), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
    # Save as new file
    output_path = frame_path.replace(".jpg", "_annotated.jpg")
    cv2.imwrite(output_path, img)
    
    return output_path
