import sys
import time
import traceback

try:
    print("Testing stream_handler initialization...")
    import cv2
    import numpy as np
    
    # Try loading models first
    from stream_handler import ppe_model, gg_model, VideoProcessor
    print("Models loaded successfully.")
    
    # Initialize processor
    print("Initializing VideoProcessor(0)...")
    processor = VideoProcessor(0)
    
    # Wait a few seconds to let the thread run
    for i in range(5):
        time.sleep(1)
        with processor.lock:
            frame = processor.latest_processed_frame
            score = processor.latest_score
            labels = processor.latest_detected_labels
            thread_alive = processor.thread.is_alive()
        
        print(f"[{i}] Thread alive: {thread_alive}, Frame ready: {frame is not None}, Score: {score}, Labels: {labels}")
        if not thread_alive:
            print("Error: Background thread died!")
            break
            
    # Stop processor
    processor.stop()
    print("Test finished.")
    
except Exception as e:
    print("Exception occurred during diagnostic:")
    traceback.print_exc()
