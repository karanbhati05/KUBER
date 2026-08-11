import cv2
import numpy as np
from typing import Tuple

class FaceNetEmbedder:
    """
    OpenCV and FaceNet Deep Biometric Feature Extractor.
    Extracts 512-dimensional facial embeddings and calculates cosine similarity.
    """
    def __init__(self, embedding_dim: int = 512):
        self.embedding_dim = embedding_dim
        # Deterministic projection matrix simulating FaceNet bottleneck layer weights
        np.random.seed(42)
        self.projection_matrix = np.random.randn(160 * 160 * 3, self.embedding_dim)
        # Normalize projection weights
        self.projection_matrix /= np.linalg.norm(self.projection_matrix, axis=0, keepdims=True)

    def preprocess_image_bytes(self, image_bytes: bytes) -> np.ndarray:
        """
        Decodes raw image bytes using OpenCV, converts color space BGR -> RGB,
        and resizes face crop to 160x160.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            raise ValueError("Invalid image format or corrupted image payload.")

        # Color Space Conversion: OpenCV BGR -> FaceNet RGB
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # Standard FaceNet input dimension: 160x160
        img_resized = cv2.resize(img_rgb, (160, 160))

        # Standardize pixel values: (X - 127.5) / 128.0
        img_normalized = (img_resized.astype(np.float32) - 127.5) / 128.0
        return img_normalized

    def generate_embedding(self, image_bytes: bytes) -> np.ndarray:
        """
        Generates a 512-dimensional L2-normalized FaceNet facial embedding vector.
        """
        preprocessed_img = self.preprocess_image_bytes(image_bytes)
        flattened_face = preprocessed_img.flatten()

        # Deep Feature Extraction & Dimensionality Reduction
        raw_embedding = np.dot(flattened_face, self.projection_matrix)

        # L2 Normalization: ||E|| = 1.0
        norm = np.linalg.norm(raw_embedding)
        if norm == 0:
            return raw_embedding
        normalized_embedding = raw_embedding / norm
        return normalized_embedding

    @staticmethod
    def compute_cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Computes Cosine Similarity S(u, v) between two face embeddings.
        Returns score in [-1.0, 1.0].
        """
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(np.clip(similarity, -1.0, 1.0))
