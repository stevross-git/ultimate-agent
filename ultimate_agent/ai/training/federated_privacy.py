"""Utilities for privacy-preserving federated learning."""

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    class _DummyNumpy:
        class ndarray:
            pass

    np = _DummyNumpy()

from typing import Tuple

class SimpleEncryptor:
    """Lightweight additive encryption for simulation."""

    @staticmethod
    def generate_key(shape: Tuple[int, ...]) -> np.ndarray:
        return np.random.randn(*shape)

    @staticmethod
    def encrypt(data: np.ndarray, key: np.ndarray) -> np.ndarray:
        return data + key

    @staticmethod
    def decrypt(encrypted: np.ndarray, key: np.ndarray) -> np.ndarray:
        return encrypted - key


class CKKSApproxEncryptor:
    """Simulated CKKS-like homomorphic encryption."""

    @staticmethod
    def generate_key(shape: Tuple[int, ...]) -> np.ndarray:
        return np.random.uniform(0.5, 1.5, size=shape)

    @staticmethod
    def encrypt(data: np.ndarray, key: np.ndarray) -> np.ndarray:
        noise = np.random.normal(0, 1e-3, size=data.shape)
        return (data * key) + noise

    @staticmethod
    def decrypt(encrypted: np.ndarray, key: np.ndarray) -> np.ndarray:
        return encrypted / key

    @staticmethod
    def add(enc_a: np.ndarray, enc_b: np.ndarray) -> np.ndarray:
        return enc_a + enc_b

    @staticmethod
    def multiply(enc_a: np.ndarray, enc_b: np.ndarray, key: np.ndarray) -> np.ndarray:
        return (enc_a * enc_b) / key
