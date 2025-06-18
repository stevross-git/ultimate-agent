#!/usr/bin/env python3
"""
ultimate_agent/ai/models/__init__.py
AI model management and training capabilities
"""

import time
import random
import threading
try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    class _DummyNumpy:
        class ndarray:
            pass

    np = _DummyNumpy()
from typing import Dict, Any, Callable, List
from ..training import AITrainingEngine
from ..inference import InferenceEngine


class AIModelManager:
    """Manages AI models and training capabilities"""

    def __init__(self, config):
        self.config = config  # ✅ store config
        self.models = {}
        self.gpu_available = self.check_gpu_availability()
        self.training_engine = None
        self.inference_engine = None
        self.model_cache = {}
        self.training_sessions = {}

        self.init_models()

    def check_gpu_availability(self) -> bool:
        """Check if GPU acceleration is available"""
        try:
            import torch
            if torch.cuda.is_available():
                print("🚀 GPU acceleration available")
                return True
            else:
                print("💻 Using CPU for AI computations")
                return False
        except ImportError:
            print("⚠️ PyTorch not available, using CPU simulation")
            return False

    def init_models(self):
        """Initialize AI models and engines"""
        try:
            # Core AI models
            self.models = {
                'sentiment': {'type': 'nlp', 'status': 'loaded', 'size': 'small', 'accuracy': 0.85},
                'classification': {'type': 'vision', 'status': 'loaded', 'size': 'medium', 'accuracy': 0.92},
                'regression': {'type': 'tabular', 'status': 'loaded', 'size': 'small', 'accuracy': 0.88},
                'transformer': {'type': 'nlp_advanced', 'status': 'loaded', 'size': 'large', 'accuracy': 0.94},
                'cnn': {'type': 'vision_advanced', 'status': 'loaded', 'size': 'large', 'accuracy': 0.96},
                'reinforcement': {'type': 'rl', 'status': 'loaded', 'size': 'medium', 'accuracy': 0.78},
                'neural_net': {'type': 'general', 'status': 'loaded', 'size': 'medium', 'accuracy': 0.90}
            }

            # Initialize training and inference engines
            self.training_engine = AITrainingEngine(self)
            self.inference_engine = InferenceEngine(self)

            print(f"🧐 AI models loaded: {len(self.models)} models")
            print(f"🎓 Training engine initialized: {len(self.training_engine.training_tasks)} task types")

        except Exception as e:
            print(f"⚠️ AI model initialization warning: {e}")

    def get_model(self, model_name: str) -> Dict[str, Any]:
        return self.models.get(model_name, {})

    def list_models(self) -> List[str]:
        return list(self.models.keys())

    def get_models_by_type(self, model_type: str) -> List[str]:
        return [name for name, info in self.models.items() if info.get('type') == model_type]

    def run_inference(self, model_name: str, input_data: Any) -> Dict[str, Any]:
        if self.inference_engine:
            return self.inference_engine.run_inference(model_name, input_data)

        try:
            if model_name in self.models:
                time.sleep(random.uniform(0.1, 0.5))
                return {
                    'success': True,
                    'prediction': random.uniform(0, 1),
                    'confidence': random.uniform(0.7, 0.99),
                    'model_used': model_name,
                    'processing_time': random.uniform(0.1, 0.5)
                }
            return {'success': False, 'error': 'Model not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def start_training(self, task_type: str, config: Dict, progress_callback: Callable) -> Dict[str, Any]:
        if self.training_engine:
            return self.training_engine.start_training(task_type, config, progress_callback)
        return {'success': False, 'error': 'Training engine not available'}

    def train_and_infer(self,
                        train_task: str,
                        train_config: Dict,
                        infer_model: str,
                        infer_input: Any,
                        progress_callback: Callable = lambda *_: True) -> Dict[str, Any]:
        """Run training and inference simultaneously."""
        if not self.training_engine or not self.inference_engine:
            return {'success': False, 'error': 'Training or inference engine not available'}

        results: Dict[str, Any] = {}
        exceptions: list[Exception] = []

        def _train():
            try:
                results['training'] = self.training_engine.start_training(train_task, train_config, progress_callback)
            except Exception as e:  # pragma: no cover - best effort
                exceptions.append(e)

        def _infer():
            try:
                results['inference'] = self.inference_engine.run_inference(infer_model, infer_input)
            except Exception as e:  # pragma: no cover - best effort
                exceptions.append(e)

        t_train = threading.Thread(target=_train, daemon=True)
        t_infer = threading.Thread(target=_infer, daemon=True)
        t_train.start()
        t_infer.start()
        t_train.join()
        t_infer.join()

        if exceptions:
            return {'success': False, 'error': str(exceptions[0])}

        return {'success': True, 'training': results.get('training'), 'inference': results.get('inference')}

    def get_training_capabilities(self) -> List[str]:
        if self.training_engine:
            return list(self.training_engine.training_tasks.keys())
        return []

    def get_model_stats(self) -> Dict[str, Any]:
        return {
            'total_models': len(self.models),
            'models_by_type': self._group_models_by_type(),
            'gpu_available': self.gpu_available,
            'training_sessions_active': len(self.training_sessions),
            'training_capabilities': self.get_training_capabilities(),
            'cache_size': len(self.model_cache),
            'models': self.models
        }

    def _group_models_by_type(self) -> Dict[str, int]:
        type_counts = {}
        for model_info in self.models.values():
            model_type = model_info.get('type', 'unknown')
            type_counts[model_type] = type_counts.get(model_type, 0) + 1
        return type_counts

    def get_status(self) -> Dict[str, Any]:
        return {
            'models_loaded': len(self.models),
            'gpu_available': self.gpu_available,
            'training_engine_active': self.training_engine is not None,
            'inference_engine_active': self.inference_engine is not None,
            'active_training_sessions': len(self.training_sessions),
            'model_types': list(set(info.get('type') for info in self.models.values())),
            'total_model_size': sum(1 for info in self.models.values() if info.get('size') == 'large')
        }

    def load_model(self, model_name: str, model_config: Dict[str, Any]) -> bool:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("Model name must be a non-empty string")

        if not isinstance(model_config, dict):
            raise ValueError("Model config must be a dictionary")

        valid_types = ['nlp', 'vision', 'tabular', 'rl', 'custom', 'nlp_advanced', 'vision_advanced', 'general']
        model_type = model_config.get('type', 'custom')
        if model_type not in valid_types:
            raise ValueError(f"Invalid model type: {model_type}")

        accuracy = model_config.get('accuracy', 0.0)
        if not isinstance(accuracy, (int, float)) or not 0.0 <= accuracy <= 1.0:
            raise ValueError("Accuracy must be a number between 0.0 and 1.0")

        try:
            self.models[model_name] = {
                'type': model_type,
                'status': 'loaded',
                'size': model_config.get('size', 'medium'),
                'accuracy': accuracy,
                'loaded_at': time.time()
            }
            print(f"✅ Model loaded: {model_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to load model {model_name}: {e}")
            return False

    def get_memory_usage(self) -> Dict[str, float]:
        total_memory = 0.0
        model_memory: Dict[str, float] = {}

        size_multipliers = {'small': 100, 'medium': 500, 'large': 2000}
        for model_name, model_info in self.models.items():
            estimated_mb = size_multipliers.get(model_info.get('size'), 500)
            model_memory[model_name] = float(estimated_mb)
            total_memory += estimated_mb

        return {'total_mb': float(total_memory), 'by_model': model_memory}

    def unload_model(self, model_name: str) -> bool:
        try:
            if model_name in self.models:
                del self.models[model_name]
                if model_name in self.model_cache:
                    del self.model_cache[model_name]
                print(f"✅ Model unloaded: {model_name}")
                return True
            return False
        except Exception as e:
            print(f"❌ Failed to unload model {model_name}: {e}")
            return False

    def optimize_models(self) -> Dict[str, Any]:
        try:
            optimized_count = 0
            for model_name, model_info in self.models.items():
                if model_info.get('status') == 'loaded':
                    model_info['optimized'] = True
                    optimized_count += 1

            return {
                'success': True,
                'optimized_models': optimized_count,
                'total_models': len(self.models)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def backup_models(self, backup_path: str) -> bool:
        try:
            import json
            backup_data = {
                'models': self.models,
                'backup_timestamp': time.time(),
                'gpu_available': self.gpu_available
            }
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)

            print(f"💾 Models backed up to {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Model backup failed: {e}")
            return False

    def restore_models(self, backup_path: str) -> bool:
        try:
            import json
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)

            self.models = backup_data.get('models', {})
            print(f"✅ Models restored from {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Model restore failed: {e}")
            return False

    def download_huggingface_model(self, repo_id: str, local_dir: str) -> bool:
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id=repo_id, local_dir=local_dir, local_dir_use_symlinks=False)
            print(f"✅ Hugging Face model downloaded to {local_dir}")
            return True
        except Exception as e:
            print(f"❌ Failed to download Hugging Face model: {e}")
            return False
