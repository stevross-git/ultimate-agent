#!/usr/bin/env python3
"""
ultimate_agent/ai/local_models/local_ai_manager.py
Local AI Manager with Ollama and Quantized Models for Most Hardware
"""

import asyncio
import aiohttp
import json
import time
import psutil
import platform
import subprocess
import os
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

DEFAULT_MODEL_DOWNLOAD_TIMEOUT = 60  # seconds

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️ ollama-python not available. Install with: pip install ollama")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class HardwareType(Enum):
    """Hardware detection types"""
    HIGH_END_GPU = "high_end_gpu"        # RTX 4090, A100, etc.
    MID_RANGE_GPU = "mid_range_gpu"      # RTX 3060, 4060, etc.
    LOW_END_GPU = "low_end_gpu"          # GTX 1660, RTX 3050, etc.
    APPLE_SILICON = "apple_silicon"      # M1, M2, M3 chips
    HIGH_END_CPU = "high_end_cpu"        # 16+ cores, 32GB+ RAM
    MID_RANGE_CPU = "mid_range_cpu"      # 8-16 cores, 16-32GB RAM
    LOW_END_CPU = "low_end_cpu"          # 4-8 cores, 8-16GB RAM
    MINIMAL_HARDWARE = "minimal"         # <4 cores, <8GB RAM


@dataclass
class QuantizedModel:
    """Represents a quantized model configuration"""
    name: str
    size: str  # e.g., "7b", "13b", "70b"
    quantization: str  # e.g., "q4_0", "q8_0", "f16"
    memory_gb: float
    min_cores: int
    min_ram_gb: int
    hardware_types: List[HardwareType]
    tags: List[str] = field(default_factory=list)
    description: str = ""
    download_size_gb: float = 0.0
    aliases: List[str] = field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        """Get full model name for Ollama"""
        return f"{self.name}:{self.size}-{self.quantization}"
    
    @property
    def display_name(self) -> str:
        """Get human-readable name"""
        return f"{self.name.title()} {self.size.upper()} ({self.quantization.upper()})"


class HardwareDetector:
    """Detects hardware capabilities and recommends optimal models"""
    
    def __init__(self):
        self.system_info = self._detect_system()
        self.hardware_type = self._classify_hardware()
        self.recommended_models = self._get_recommended_models()
        
    def _detect_system(self) -> Dict[str, Any]:
        """Detect system hardware specifications"""
        info = {
            'platform': platform.system(),
            'architecture': platform.machine(),
            'cpu_count': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'cpu_brand': self._get_cpu_brand(),
            'gpu_info': self._detect_gpu(),
            'apple_silicon': self._is_apple_silicon()
        }
        return info
    
    def _get_cpu_brand(self) -> str:
        """Get CPU brand information"""
        try:
            if platform.system() == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                winreg.CloseKey(key)
                return cpu_name
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], 
                                      capture_output=True, text=True)
                return result.stdout.strip()
            else:  # Linux
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            return line.split(':')[1].strip()
        except Exception:
            pass
        return "Unknown CPU"
    
    def _detect_gpu(self) -> Dict[str, Any]:
        """Detect GPU capabilities"""
        gpu_info = {
            'available': False,
            'name': 'None',
            'memory_gb': 0.0,
            'cuda_available': False,
            'metal_available': False,
            'opencl_available': False
        }
        
        # Check CUDA (NVIDIA)
        if TORCH_AVAILABLE:
            if torch.cuda.is_available():
                gpu_info['cuda_available'] = True
                gpu_info['available'] = True
                gpu_info['name'] = torch.cuda.get_device_name(0)
                gpu_info['memory_gb'] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
        # Check Metal (Apple Silicon)
        if TORCH_AVAILABLE and hasattr(torch.backends, 'mps'):
            if torch.backends.mps.is_available():
                gpu_info['metal_available'] = True
                gpu_info['available'] = True
                if not gpu_info['name'] or gpu_info['name'] == 'None':
                    gpu_info['name'] = 'Apple Silicon GPU'
        
        # Fallback: Try to detect GPU via system commands
        if not gpu_info['available']:
            gpu_info.update(self._detect_gpu_fallback())
        
        return gpu_info
    
    def _detect_gpu_fallback(self) -> Dict[str, Any]:
        """Fallback GPU detection using system commands"""
        gpu_info = {'available': False, 'name': 'None', 'memory_gb': 0.0}
        
        try:
            if platform.system() == "Linux":
                # Try nvidia-smi
                result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', 
                                       '--format=csv,noheader'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines and lines[0]:
                        parts = lines[0].split(', ')
                        gpu_info['name'] = parts[0]
                        gpu_info['memory_gb'] = float(parts[1].split()[0]) / 1024
                        gpu_info['available'] = True
                        
            elif platform.system() == "Windows":
                # Try wmic
                result = subprocess.run(['wmic', 'path', 'win32_VideoController', 
                                       'get', 'name'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                    if len(lines) > 1:  # Skip header
                        gpu_info['name'] = lines[1]
                        gpu_info['available'] = True
                        
        except Exception as e:
            logging.debug(f"GPU detection fallback failed: {e}")
            
        return gpu_info
    
    def _is_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon"""
        return (platform.system() == "Darwin" and 
                platform.machine() in ["arm64", "aarch64"])
    
    def _classify_hardware(self) -> HardwareType:
        """Classify hardware type based on detected specifications"""
        gpu = self.system_info['gpu_info']
        memory_gb = self.system_info['memory_gb']
        cpu_count = self.system_info['cpu_count']
        
        # Apple Silicon
        if self.system_info['apple_silicon']:
            return HardwareType.APPLE_SILICON
        
        # GPU-based classification
        if gpu['available']:
            if gpu['cuda_available'] and gpu['memory_gb'] >= 20:
                return HardwareType.HIGH_END_GPU
            elif gpu['cuda_available'] and gpu['memory_gb'] >= 8:
                return HardwareType.MID_RANGE_GPU
            elif gpu['cuda_available'] and gpu['memory_gb'] >= 4:
                return HardwareType.LOW_END_GPU
        
        # CPU-based classification
        if memory_gb >= 32 and cpu_count >= 16:
            return HardwareType.HIGH_END_CPU
        elif memory_gb >= 16 and cpu_count >= 8:
            return HardwareType.MID_RANGE_CPU
        elif memory_gb >= 8 and cpu_count >= 4:
            return HardwareType.LOW_END_CPU
        else:
            return HardwareType.MINIMAL_HARDWARE
    
    def _get_recommended_models(self) -> List[QuantizedModel]:
        """Get recommended models for detected hardware"""
        all_models = get_quantized_model_catalog()
        
        recommended = []
        for model in all_models:
            if (self.hardware_type in model.hardware_types and
                model.min_ram_gb <= self.system_info['memory_gb'] and
                model.min_cores <= self.system_info['cpu_count']):
                recommended.append(model)
        
        # Sort by memory requirement (ascending)
        return sorted(recommended, key=lambda m: m.memory_gb)
    
    def get_optimal_model(self, task_type: str = "general") -> Optional[QuantizedModel]:
        """Get the best model for specific task and hardware"""
        suitable_models = [m for m in self.recommended_models 
                          if task_type in m.tags or "general" in m.tags]
        
        if not suitable_models:
            return self.recommended_models[0] if self.recommended_models else None
        
        # Return the largest model that fits
        return suitable_models[-1]


def get_quantized_model_catalog() -> List[QuantizedModel]:
    """Get catalog of available quantized models"""
    return [
        # Llama 2 Models
        QuantizedModel(
            name="llama2",
            size="7b",
            quantization="q4_0",
            memory_gb=4.0,
            min_cores=4,
            min_ram_gb=8,
            hardware_types=[HardwareType.LOW_END_CPU, HardwareType.MID_RANGE_CPU, 
                          HardwareType.HIGH_END_CPU, HardwareType.APPLE_SILICON,
                          HardwareType.LOW_END_GPU, HardwareType.MID_RANGE_GPU],
            tags=["general", "chat", "reasoning"],
            description="Lightweight Llama 2 7B with 4-bit quantization",
            download_size_gb=3.8
        ),
        QuantizedModel(
            name="llama2",
            size="7b",
            quantization="q8_0",
            memory_gb=7.0,
            min_cores=6,
            min_ram_gb=12,
            hardware_types=[HardwareType.MID_RANGE_CPU, HardwareType.HIGH_END_CPU, 
                          HardwareType.APPLE_SILICON, HardwareType.MID_RANGE_GPU],
            tags=["general", "chat", "reasoning", "quality"],
            description="Higher quality Llama 2 7B with 8-bit quantization",
            download_size_gb=6.7
        ),
        QuantizedModel(
            name="llama2",
            size="13b",
            quantization="q4_0",
            memory_gb=8.0,
            min_cores=6,
            min_ram_gb=16,
            hardware_types=[HardwareType.MID_RANGE_CPU, HardwareType.HIGH_END_CPU, 
                          HardwareType.APPLE_SILICON, HardwareType.LOW_END_GPU, 
                          HardwareType.MID_RANGE_GPU],
            tags=["general", "chat", "reasoning", "complex"],
            description="Llama 2 13B with 4-bit quantization for better reasoning",
            download_size_gb=7.3
        ),
        
        # Code Llama Models
        QuantizedModel(
            name="codellama",
            size="7b",
            quantization="q4_0",
            memory_gb=4.0,
            min_cores=4,
            min_ram_gb=8,
            hardware_types=[HardwareType.LOW_END_CPU, HardwareType.MID_RANGE_CPU, 
                          HardwareType.HIGH_END_CPU, HardwareType.APPLE_SILICON,
                          HardwareType.LOW_END_GPU, HardwareType.MID_RANGE_GPU],
            tags=["coding", "programming", "technical", "development"],
            description="Code-specialized Llama model for programming tasks",
            download_size_gb=3.8
        ),
        QuantizedModel(
            name="codellama",
            size="13b",
            quantization="q4_0",
            memory_gb=8.0,
            min_cores=6,
            min_ram_gb=16,
            hardware_types=[HardwareType.MID_RANGE_CPU, HardwareType.HIGH_END_CPU, 
                          HardwareType.APPLE_SILICON, HardwareType.MID_RANGE_GPU],
            tags=["coding", "programming", "technical", "development", "complex"],
            description="Larger Code Llama for complex programming tasks",
            download_size_gb=7.3
        ),
        
        # Mistral Models
        QuantizedModel(
            name="mistral",
            size="7b",
            quantization="q4_0",
            memory_gb=4.0,
            min_cores=4,
            min_ram_gb=8,
            hardware_types=[HardwareType.LOW_END_CPU, HardwareType.MID_RANGE_CPU,
                          HardwareType.HIGH_END_CPU, HardwareType.APPLE_SILICON,
                          HardwareType.LOW_END_GPU, HardwareType.MID_RANGE_GPU],
            tags=["general", "chat", "fast", "efficient"],
            description="Fast and efficient Mistral 7B model",
            download_size_gb=4.1,
            aliases=[
                "mistral",
                "mistral:latest",
                "mistral:7b-instruct",
                "mistral:7b-instruct-v0.2-q4_0",
            ]
        ),
        
        # Smaller models for minimal hardware
        QuantizedModel(
            name="tinyllama",
            size="1.1b",
            quantization="q4_0",
            memory_gb=1.0,
            min_cores=2,
            min_ram_gb=4,
            hardware_types=[HardwareType.MINIMAL_HARDWARE, HardwareType.LOW_END_CPU,
                          HardwareType.MID_RANGE_CPU],
            tags=["general", "lightweight", "minimal", "chat"],
            description="Ultra-lightweight model for minimal hardware",
            download_size_gb=0.7
        ),
        
        # Phi-3 Models (Microsoft)
        QuantizedModel(
            name="phi3",
            size="mini",
            quantization="q4_0",
            memory_gb=2.5,
            min_cores=4,
            min_ram_gb=6,
            hardware_types=[HardwareType.MINIMAL_HARDWARE, HardwareType.LOW_END_CPU,
                          HardwareType.MID_RANGE_CPU, HardwareType.APPLE_SILICON],
            tags=["general", "efficient", "small", "chat"],
            description="Microsoft Phi-3 Mini - efficient and capable",
            download_size_gb=2.2
        ),

        # DeepSeek R1 model - try latest then 1.5b
        QuantizedModel(
            name="deepseek-r1",
            size="latest",
            quantization="",
            memory_gb=2.5,
            min_cores=4,
            min_ram_gb=8,
            hardware_types=[HardwareType.LOW_END_CPU, HardwareType.MID_RANGE_CPU,
                          HardwareType.LOW_END_GPU, HardwareType.MID_RANGE_GPU],
            tags=["general", "chat", "efficient"],
            description="DeepSeek R1 model",
            download_size_gb=2.5,
            aliases=["deepseek-r1:1.5b"]
        ),
        
        # Specialized models for specific hardware
        QuantizedModel(
            name="llama2",
            size="70b",
            quantization="q4_0",
            memory_gb=40.0,
            min_cores=16,
            min_ram_gb=64,
            hardware_types=[HardwareType.HIGH_END_GPU, HardwareType.HIGH_END_CPU],
            tags=["general", "reasoning", "complex", "research"],
            description="Large Llama 2 70B for high-end hardware",
            download_size_gb=39.0
        ),
    ]


class LocalAIManager:
    """Enhanced Local AI Manager with automatic model selection and optimization"""
    
    def __init__(self, config_manager=None):
        self.config = config_manager
        self.hardware_detector = HardwareDetector()
        self.ollama_client = None
        self.loaded_models: Dict[str, QuantizedModel] = {}
        self.model_catalog = get_quantized_model_catalog()
        self.current_model: Optional[QuantizedModel] = None

        # Performance tracking
        self.inference_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'avg_response_time': 0.0,
            'tokens_per_second': 0.0
        }

        # Configuration defaults
        self.max_concurrent_requests = 3
        self.auto_model_management = True
        self.preload_models = True
        self.download_timeout = DEFAULT_MODEL_DOWNLOAD_TIMEOUT


        if self.config:
            self.auto_model_management = self.config.getboolean(
                'LOCAL_AI', 'auto_model_management', fallback=True
            )
            self.preload_models = self.config.getboolean(
                'LOCAL_AI', 'preload_models', fallback=True
            )
            self.max_concurrent_requests = self.config.getint(
                'LOCAL_AI', 'max_concurrent_requests', fallback=3
            )


        self._initialize()
    
    def _initialize(self):
        """Initialize the local AI manager"""
        try:
            if OLLAMA_AVAILABLE:
                self.ollama_client = ollama.Client()
                logging.info("✅ Ollama client initialized")
            else:
                logging.warning("⚠️ Ollama not available, using fallback mode")
            
            # Auto-select optimal model
            if self.auto_model_management:
                self._setup_optimal_model()
                
        except Exception as e:
            logging.error(f"❌ Failed to initialize Local AI Manager: {e}")
    
    def _setup_optimal_model(self):
        """Automatically setup the optimal model for the hardware"""
        try:
            optimal_model = self.hardware_detector.get_optimal_model("general")
            if optimal_model:
                logging.info(f"🎯 Selected optimal model: {optimal_model.display_name}")
                
                # Check if model is available
                if self._is_model_available(optimal_model):
                    self.current_model = optimal_model
                    logging.info(f"✅ Model {optimal_model.display_name} is ready")
                else:
                    logging.info(f"📥 Model {optimal_model.display_name} needs to be downloaded")
                    if self.preload_models:
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            loop = None
                        if loop and loop.is_running():
                            loop.create_task(self._download_model_async(optimal_model))
                        else:
                            threading.Thread(
                                target=lambda: asyncio.run(
                                    self._download_model_async(optimal_model)
                                ),
                                daemon=True,
                            ).start()
            else:
                logging.warning("⚠️ No suitable model found for this hardware")
                
        except Exception as e:
            logging.error(f"❌ Failed to setup optimal model: {e}")
    
    def _is_model_available(self, model: QuantizedModel) -> bool:
        """Check if model is available locally"""
        try:
            if not self.ollama_client:
                return False
                
            models = self.ollama_client.list()
            available_models = [m['name'] for m in models.get('models', [])]
            return model.full_name in available_models
            
        except Exception as e:
            logging.debug(f"Model availability check failed: {e}")
            return False
    
    async def _download_model_async(self, model: QuantizedModel) -> bool:
        """Download model asynchronously"""
        try:
            logging.info(
                f"📥 Downloading {model.display_name} ({model.download_size_gb:.1f}GB)"
            )

            async def try_pull(name: str) -> bool:
                def download_model():
                    try:
                        self.ollama_client.pull(name)
                        return True
                    except Exception as e:
                        logging.error(f"Failed to download {name}: {e}")
                        return False


                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    future = loop.run_in_executor(executor, download_model)
                    try:
                        return await asyncio.wait_for(
                            future, timeout=self.download_timeout
                        )
                    except asyncio.TimeoutError:
                        logging.error(
                            f"Download timed out for {name} after {self.download_timeout}s"
                        )
                        return False

                with ThreadPoolExecutor() as executor:
                    return await asyncio.get_event_loop().run_in_executor(
                        executor, download_model
                    )


            for name in [model.full_name, *model.aliases]:
                success = await try_pull(name)
                if success:
                    self.loaded_models[model.full_name] = model
                    if not self.current_model:
                        self.current_model = model
                    logging.info(f"✅ Successfully downloaded {name}")
                    return True

            logging.error(f"❌ Failed to download {model.display_name}")
            return False
                
        except Exception as e:
            logging.error(f"❌ Download error for {model.display_name}: {e}")
            return False
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """Get detailed hardware information"""
        return {
            'hardware_type': self.hardware_detector.hardware_type.value,
            'system_info': self.hardware_detector.system_info,
            'recommended_models': [
                {
                    'name': m.display_name,
                    'full_name': m.full_name,
                    'memory_gb': m.memory_gb,
                    'tags': m.tags,
                    'description': m.description,
                    'available': self._is_model_available(m)
                }
                for m in self.hardware_detector.recommended_models
            ],
            'current_model': {
                'name': self.current_model.display_name,
                'full_name': self.current_model.full_name,
                'memory_gb': self.current_model.memory_gb,
                'tags': self.current_model.tags
            } if self.current_model else None
        }
    
    async def ensure_model_ready(self, task_type: str = "general") -> bool:
        """Ensure appropriate model is ready for the task"""
        try:
            # Get optimal model for task
            optimal_model = self.hardware_detector.get_optimal_model(task_type)
            if not optimal_model:
                logging.error("No suitable model found for hardware")
                return False
            
            # Check if we need to switch models
            if (not self.current_model or 
                self.current_model.full_name != optimal_model.full_name):
                
                # Check if model is available
                if not self._is_model_available(optimal_model):
                    logging.info(f"Downloading required model: {optimal_model.display_name}")
                    success = await self._download_model_async(optimal_model)
                    if not success:
                        return False
                
                self.current_model = optimal_model
                logging.info(f"Switched to model: {optimal_model.display_name}")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to ensure model ready: {e}")
            return False
    
    async def generate_response(self, prompt: str, **options) -> Dict[str, Any]:
        """Generate response using optimal local model"""
        start_time = time.time()
        
        try:
            # Ensure model is ready
            task_type = options.get('task_type', 'general')
            if not await self.ensure_model_ready(task_type):
                return {
                    'success': False,
                    'error': 'No suitable model available',
                    'hardware_info': self.get_hardware_info()
                }
            
            # Prepare generation options
            generation_options = {
                'temperature': options.get('temperature', 0.7),
                'max_tokens': options.get('max_tokens', 1000),
                'top_p': options.get('top_p', 0.9),
                'repeat_penalty': options.get('repeat_penalty', 1.1),
            }
            
            # Generate response
            response = await self._generate_with_ollama(prompt, generation_options)
            
            # Calculate metrics
            processing_time = time.time() - start_time
            self._update_stats(processing_time, response)
            
            return {
                'success': True,
                'response': response['response'],
                'model_used': self.current_model.display_name,
                'model_full_name': self.current_model.full_name,
                'processing_time': processing_time,
                'tokens_generated': response.get('eval_count', 0),
                'tokens_per_second': response.get('eval_count', 0) / processing_time if processing_time > 0 else 0,
                'hardware_type': self.hardware_detector.hardware_type.value,
                'memory_used_gb': self.current_model.memory_gb,
                'context_length': response.get('prompt_eval_count', 0)
            }
            
        except Exception as e:
            logging.error(f"Generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'model_attempted': self.current_model.display_name if self.current_model else None
            }
    
    async def _generate_with_ollama(self, prompt: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using Ollama"""
        try:
            def ollama_generate():
                return self.ollama_client.generate(
                    model=self.current_model.full_name,
                    prompt=prompt,
                    options=options
                )
            
            # Run in executor to avoid blocking
            with ThreadPoolExecutor() as executor:
                response = await asyncio.get_event_loop().run_in_executor(
                    executor, ollama_generate
                )
            
            return response
            
        except Exception as e:
            logging.error(f"Ollama generation failed: {e}")
            raise
    
    async def generate_stream(self, prompt: str, **options) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response"""
        try:
            # Ensure model is ready
            task_type = options.get('task_type', 'general')
            if not await self.ensure_model_ready(task_type):
                yield {
                    'success': False,
                    'error': 'No suitable model available',
                    'done': True
                }
                return
            
            # Prepare options
            generation_options = {
                'temperature': options.get('temperature', 0.7),
                'max_tokens': options.get('max_tokens', 1000),
                'top_p': options.get('top_p', 0.9),
            }
            
            start_time = time.time()
            full_response = ""
            
            def ollama_stream():
                return self.ollama_client.generate(
                    model=self.current_model.full_name,
                    prompt=prompt,
                    options=generation_options,
                    stream=True
                )
            
            # Stream response
            with ThreadPoolExecutor() as executor:
                stream = await asyncio.get_event_loop().run_in_executor(
                    executor, ollama_stream
                )
                
                for chunk in stream:
                    response_text = chunk.get('response', '')
                    full_response += response_text
                    done = chunk.get('done', False)
                    
                    yield {
                        'success': True,
                        'response': response_text,
                        'full_response': full_response,
                        'done': done,
                        'model_used': self.current_model.display_name,
                        'processing_time': time.time() - start_time
                    }
                    
                    if done:
                        # Final metrics
                        total_time = time.time() - start_time
                        self._update_stats(total_time, chunk)
                        break
            
        except Exception as e:
            logging.error(f"Streaming generation failed: {e}")
            yield {
                'success': False,
                'error': str(e),
                'done': True
            }
    
    def _update_stats(self, processing_time: float, response: Dict[str, Any]):
        """Update performance statistics"""
        self.inference_stats['total_requests'] += 1
        self.inference_stats['successful_requests'] += 1
        
        # Update average response time
        current_avg = self.inference_stats['avg_response_time']
        total_requests = self.inference_stats['successful_requests']
        self.inference_stats['avg_response_time'] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
        
        # Calculate tokens per second
        eval_count = response.get('eval_count', 0)
        eval_duration = response.get('eval_duration', 0)
        if eval_duration > 0:
            tokens_per_second = eval_count / (eval_duration / 1_000_000_000)
            self.inference_stats['tokens_per_second'] = tokens_per_second
    
    async def download_model(self, model_name: str) -> Dict[str, Any]:
        """Download a specific model"""
        try:
            # Find model in catalog
            model = None
            for m in self.model_catalog:
                if m.name == model_name or m.full_name == model_name:
                    model = m
                    break
            
            if not model:
                return {
                    'success': False,
                    'error': f'Model {model_name} not found in catalog'
                }
            
            # Check hardware compatibility
            if self.hardware_detector.hardware_type not in model.hardware_types:
                return {
                    'success': False,
                    'error': f'Model {model.display_name} not compatible with {self.hardware_detector.hardware_type.value}',
                    'recommended_models': [m.display_name for m in self.hardware_detector.recommended_models]
                }
            
            # Download model
            success = await self._download_model_async(model)
            
            return {
                'success': success,
                'model': model.display_name,
                'size_gb': model.download_size_gb,
                'hardware_compatible': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_available_models(self) -> Dict[str, Any]:
        """List all available and recommended models"""
        try:
            # Get Ollama models
            ollama_models = []
            if self.ollama_client:
                try:
                    models_response = self.ollama_client.list()
                    ollama_models = [m['name'] for m in models_response.get('models', [])]
                except Exception as e:
                    logging.debug(f"Failed to get Ollama models: {e}")
            
            # Categorize models
            compatible_models = []
            recommended_models = []
            all_models = []
            
            for model in self.model_catalog:
                model_info = {
                    'name': model.display_name,
                    'full_name': model.full_name,
                    'size_gb': model.download_size_gb,
                    'memory_gb': model.memory_gb,
                    'tags': model.tags,
                    'description': model.description,
                    'available': model.full_name in ollama_models,
                    'hardware_compatible': self.hardware_detector.hardware_type in model.hardware_types
                }
                
                all_models.append(model_info)
                
                if model_info['hardware_compatible']:
                    compatible_models.append(model_info)
                    
                if model in self.hardware_detector.recommended_models:
                    recommended_models.append(model_info)
            
            return {
                'hardware_type': self.hardware_detector.hardware_type.value,
                'system_info': {
                    'cpu_cores': self.hardware_detector.system_info['cpu_count'],
                    'memory_gb': round(self.hardware_detector.system_info['memory_gb'], 1),
                    'gpu_available': self.hardware_detector.system_info['gpu_info']['available'],
                    'gpu_name': self.hardware_detector.system_info['gpu_info']['name'],
                    'apple_silicon': self.hardware_detector.system_info['apple_silicon']
                },
                'current_model': self.current_model.display_name if self.current_model else None,
                'recommended_models': recommended_models,
                'compatible_models': compatible_models,
                'all_models': all_models,
                'total_models': len(all_models),
                'compatible_count': len(compatible_models)
            }
            
        except Exception as e:
            logging.error(f"Failed to list models: {e}")
            return {
                'error': str(e),
                'hardware_type': self.hardware_detector.hardware_type.value
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'inference_stats': self.inference_stats,
            'hardware_info': {
                'type': self.hardware_detector.hardware_type.value,
                'cpu_cores': self.hardware_detector.system_info['cpu_count'],
                'memory_gb': round(self.hardware_detector.system_info['memory_gb'], 1),
                'gpu_available': self.hardware_detector.system_info['gpu_info']['available'],
                'gpu_memory_gb': round(self.hardware_detector.system_info['gpu_info']['memory_gb'], 1)
            },
            'current_model': {
                'name': self.current_model.display_name,
                'memory_usage_gb': self.current_model.memory_gb,
                'tags': self.current_model.tags
            } if self.current_model else None,
            'loaded_models_count': len(self.loaded_models),
            'ollama_available': OLLAMA_AVAILABLE and self.ollama_client is not None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall status"""
        return {
            'local_ai_enabled': True,
            'ollama_available': OLLAMA_AVAILABLE and self.ollama_client is not None,
            'hardware_type': self.hardware_detector.hardware_type.value,
            'current_model': self.current_model.display_name if self.current_model else None,
            'models_loaded': len(self.loaded_models),
            'auto_management': self.auto_model_management,
            'performance': self.inference_stats
        }


# Integration with existing conversation manager
class LocalAIConversationManager:
    """Enhanced conversation manager with local AI integration"""
    
    def __init__(self, local_ai_manager: LocalAIManager, config_manager=None):
        self.local_ai = local_ai_manager
        self.config = config_manager
        self.conversations = {}
        
    async def process_message(self, conversation_id: str, message: str, 
                            context_aware: bool = True, **options) -> Dict[str, Any]:
        """Process message using local AI"""
        try:
            # Determine task type from message
            task_type = self._analyze_task_type(message)
            
            # Build context if needed
            context = ""
            if context_aware and conversation_id in self.conversations:
                context = self._build_context(conversation_id)
            
            # Prepare full prompt
            if context:
                full_prompt = f"Context:\n{context}\n\nUser: {message}\nAssistant:"
            else:
                full_prompt = f"User: {message}\nAssistant:"
            
            # Generate response using local AI
            response = await self.local_ai.generate_response(
                full_prompt, 
                task_type=task_type,
                **options
            )
            
            if response['success']:
                # Store conversation
                self._store_message(conversation_id, 'user', message)
                self._store_message(conversation_id, 'assistant', response['response'])
                
                return {
                    'success': True,
                    'conversation_id': conversation_id,
                    'response': response['response'],
                    'model_used': response['model_used'],
                    'processing_time': response['processing_time'],
                    'tokens_per_second': response.get('tokens_per_second', 0),
                    'hardware_type': response.get('hardware_type'),
                    'local_ai': True
                }
            else:
                return response
                
        except Exception as e:
            logging.error(f"Local AI conversation processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'conversation_id': conversation_id
            }
    
    def _analyze_task_type(self, message: str) -> str:
        """Analyze message to determine task type"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['code', 'programming', 'function', 'debug', 'python', 'javascript']):
            return "coding"
        elif any(word in message_lower for word in ['creative', 'story', 'poem', 'imagine', 'write']):
            return "creative"
        elif any(word in message_lower for word in ['technical', 'explain', 'how does', 'what is']):
            return "technical"
        else:
            return "general"
    
    def _build_context(self, conversation_id: str, max_messages: int = 10) -> str:
        """Build conversation context"""
        if conversation_id not in self.conversations:
            return ""
        
        messages = self.conversations[conversation_id][-max_messages:]
        context_parts = []
        
        for msg in messages:
            role = "User" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def _store_message(self, conversation_id: str, role: str, content: str):
        """Store message in conversation history"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        self.conversations[conversation_id].append({
            'role': role,
            'content': content,
            'timestamp': time.time()
        })


# Factory function for easy integration
def create_local_ai_manager(config_manager=None) -> LocalAIManager:
    """Factory function to create local AI manager"""
    return LocalAIManager(config_manager)


def create_local_ai_conversation_manager(config_manager=None) -> LocalAIConversationManager:
    """Factory function to create local AI conversation manager"""
    local_ai = create_local_ai_manager(config_manager)
    return LocalAIConversationManager(local_ai, config_manager)


# CLI utility for testing
if __name__ == "__main__":
    async def test_local_ai():
        print("🧪 Testing Local AI Manager...")
        
        # Create manager
        manager = LocalAIManager()
        
        # Show hardware info
        hw_info = manager.get_hardware_info()
        print(f"\n🖥️ Hardware Type: {hw_info['hardware_type']}")
        print(f"💾 Memory: {hw_info['system_info']['memory_gb']:.1f}GB")
        print(f"⚙️ CPU Cores: {hw_info['system_info']['cpu_count']}")
        print(f"🎮 GPU: {hw_info['system_info']['gpu_info']['name']}")
        
        # Show recommended models
        print(f"\n📋 Recommended Models:")
        for model in hw_info['recommended_models'][:3]:
            status = "✅ Available" if model['available'] else "📥 Need Download"
            print(f"  {model['name']} - {model['memory_gb']}GB - {status}")
        
        # Test inference
        if manager.current_model or hw_info['recommended_models']:
            print(f"\n🧠 Testing inference...")
            response = await manager.generate_response(
                "Explain what machine learning is in simple terms."
            )
            
            if response['success']:
                print(f"✅ Response generated successfully!")
                print(f"📝 Model: {response['model_used']}")
                print(f"⏱️ Time: {response['processing_time']:.2f}s")
                print(f"🚀 Speed: {response.get('tokens_per_second', 0):.1f} tokens/s")
                print(f"💭 Response: {response['response'][:200]}...")
            else:
                print(f"❌ Inference failed: {response['error']}")
        
        # Show final stats
        stats = manager.get_stats()
        print(f"\n📊 Stats: {stats}")
    
    # Run test
    if OLLAMA_AVAILABLE:
        asyncio.run(test_local_ai())
    else:
        print("❌ Ollama not available. Install with: pip install ollama")
        print("💡 Then install Ollama: https://ollama.ai/download")