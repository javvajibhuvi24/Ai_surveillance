"""
Diagnostic: Shows EXACTLY what the PPE model sees at ultra-low threshold.
Run: venv\Scripts\python.exe diagnose_model.py <image_path>
"""
import sys
import cv2
from ultralytics import YOLO

PPE_MODEL_PATH = "runs/detect/train-2/weights/best.pt"
GG_MODEL_PATH  = "runs/detect/train-3/weights/best.pt"

def diagnose(img_path):
    print("\n" + "="*60)
    print(f"Testing image: {img_path}")
    img = cv2.imread(img_path)
    if img is None:
        print("ERROR: Could not read image!")
        return
    print(f"Image size: {img.shape[1]}x{img.shape[0]}")
    
    for model_path, name in [(PPE_MODEL_PATH, "PPE (train-2)"), (GG_MODEL_PATH, "GG (train-3)")]:
        print(f"\n--- {name} ---")
        print(f"    Classes: ", end="")
        try:
            model = YOLO(model_path)
            print(model.names)
        except Exception as e:
            print(f"FAILED to load: {e}")
            continue
        
        for imgsz in [640, 1024]:
            for conf in [0.01, 0.05, 0.10, 0.25]:
                results = model(img, imgsz=imgsz, conf=conf, verbose=False)
                detections = []
                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    conf_val = float(box.conf[0])
                    label = model.names[cls_id]
                    detections.append(f"{label}({conf_val:.3f})")
                
                if detections:
                    print(f"    imgsz={imgsz}, conf>={conf}: {', '.join(detections)}")
                else:
                    print(f"    imgsz={imgsz}, conf>={conf}: NOTHING DETECTED")
    
    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: venv\\Scripts\\python.exe diagnose_model.py path\\to\\image.jpg")
        print("\nRunning with a test: drag an image to this window or provide path.")
    else:
        diagnose(sys.argv[1])
