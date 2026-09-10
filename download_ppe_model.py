"""
Downloads a pre-trained PPE YOLO model from HuggingFace.
Detects: helmet, vest, gloves, boots, goggles (all PPE items)
Run: venv\Scripts\python.exe download_ppe_model.py
"""
import urllib.request
import os
import shutil

# Multiple sources to try (in order of preference)
SOURCES = [
    {
        "name": "PPE Model v1 (Helmet+Vest+Gloves+Boots+Goggles)",
        "url": "https://huggingface.co/spaces/madhukarkumar/ppe-detection/resolve/main/ppe_detection_yolov8.pt",
        "dest": "runs/detect/train-2/weights/best.pt"
    },
    {
        "name": "Hard Hat Detection Model (HuggingFace)",
        "url": "https://huggingface.co/keremberke/yolov8n-hard-hat-detection/resolve/main/best.pt",
        "dest": "runs/detect/train-helmet/weights/best.pt"
    }
]

def download_file(url, dest_path, name):
    print(f"\nDownloading: {name}")
    print(f"  URL: {url}")
    print(f"  To:  {dest_path}")
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Backup existing model
    if os.path.exists(dest_path):
        backup = dest_path + ".backup"
        shutil.copy2(dest_path, backup)
        print(f"  Backed up existing model to: {backup}")
    
    try:
        def progress(count, block_size, total_size):
            if total_size > 0:
                percent = min(count * block_size * 100 / total_size, 100)
                print(f"\r  Progress: {percent:.1f}% ({count*block_size//1024//1024}MB / {total_size//1024//1024}MB)", end="")
        
        urllib.request.urlretrieve(url, dest_path, reporthook=progress)
        print(f"\n  SUCCESS! Model saved to: {dest_path}")
        
        # Verify it's a valid file
        size = os.path.getsize(dest_path)
        if size < 100000:  # Less than 100KB is suspicious
            print(f"  WARNING: File seems too small ({size} bytes). May be invalid.")
            if os.path.exists(dest_path + ".backup"):
                shutil.copy2(dest_path + ".backup", dest_path)
                print("  Restored backup.")
            return False
        
        print(f"  File size: {size / 1024 / 1024:.1f} MB")
        return True
        
    except Exception as e:
        print(f"\n  FAILED: {e}")
        if os.path.exists(dest_path + ".backup"):
            shutil.copy2(dest_path + ".backup", dest_path)
            print("  Restored backup.")
        return False

if __name__ == "__main__":
    print("="*60)
    print("PPE Model Downloader")
    print("="*60)
    
    success = False
    for source in SOURCES:
        if download_file(source["url"], source["dest"], source["name"]):
            success = True
            print(f"\n✓ Done! Restart your Flask server to use the new model.")
            break
    
    if not success:
        print("\n✗ All downloads failed.")
        print("\nManual option: Download from Roboflow Universe:")
        print("  1. Go to: https://universe.roboflow.com/roboflow-100/ppe-raw-images")
        print("  2. Sign in (free) → Click 'Download' → Choose YOLOv8")
        print("  3. Save best.pt to: runs/detect/train-2/weights/best.pt")
