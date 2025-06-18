#!/usr/bin/env python3
"""Simple inference engine for tests."""

import time
import random
from typing import Any, Dict


class InferenceEngine:
    """Minimal inference engine returning mock predictions."""

    def __init__(self, ai_manager=None):
        self.ai_manager = ai_manager

    def run_inference(self, model_name: str, input_data: Any, **kwargs) -> Dict[str, Any]:
        start = time.time()
        time.sleep(0.01)  # simulate small delay
        return {
            "success": True,
            "prediction": f"mock_{model_name}_result",
            "confidence": 0.5,
            "model_used": model_name,
            "processing_time": time.time() - start,
        }


def create_inference_engine(ai_manager=None) -> InferenceEngine:
    """Factory function for compatibility."""
    return InferenceEngine(ai_manager)
