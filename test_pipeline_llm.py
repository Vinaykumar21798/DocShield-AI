import os
import sys
from modules.detection.service import DetectionService

def main():
    print("Initializing DocShield-AI Detection Service...")
    
    # Enable Qwen detector for this manual test run
    os.environ["BYPASS_LLM"] = "False"
    
    try:
        service = DetectionService()
    except Exception as e:
        print(f"Error initializing detection service: {e}")
        sys.exit(1)
        
    text = "The patient John Doe was prescribed Metformin 1000mg by Dr. Jane Smith at Apollo Hospital on 2026-08-04."
    
    print("\nText to analyze:")
    print("-" * 50)
    print(text)
    print("-" * 50)
    
    print("\nRunning detection pipeline...")
    try:
        results = service.detect(text, document_type="healthcare")
        
        print(f"\nFound {len(results)} entities:")
        for i, entity in enumerate(results, 1):
            print(f"\n[{i}] Entity: '{entity.entity_value}'")
            print(f"    Type: {entity.entity_type}")
            print(f"    Confidence: {entity.confidence_score:.2f}")
            print(f"    Detector: {entity.detector}")
            if entity.metadata:
                print(f"    Metadata: {entity.metadata}")
    except Exception as e:
        print(f"Error running pipeline: {e}")
        print("Please verify that Ollama is running and has the model pulled:")
        print("  - qwen3:4b")

if __name__ == "__main__":
    main()
