from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
from typing import Optional
import numpy as np
from facenet_utils import FaceNetEmbedder

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="KUBER Driver Verification Engine",
    description="Biometric identity authentication microservice using OpenCV and FaceNet facial embeddings"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


embedder = FaceNetEmbedder(embedding_dim=512)

# In-memory storage for registered driver baseline embeddings
registered_driver_embeddings: dict[str, np.ndarray] = {}

# Authentication threshold (Cosine similarity >= 0.70 indicates same person)
SIMILARITY_THRESHOLD = 0.70

class VerificationResponse(BaseModel):
    status: str
    is_authenticated: bool
    similarity_score: float
    verification_result: str
    message: str

@app.post("/verify/compare")
async def compare_faces(
    selfie: UploadFile = File(..., description="Live selfie image from driver app"),
    id_card: UploadFile = File(..., description="Registered government ID card photo")
):
    """
    Direct 2-image comparison: Extracts FaceNet embeddings from live selfie and ID card photo
    using OpenCV and computes facial match confidence score.
    """
    try:
        selfie_bytes = await selfie.read()
        id_bytes = await id_card.read()

        # Generate 512-D FaceNet embeddings
        emb_selfie = embedder.generate_embedding(selfie_bytes)
        emb_id = embedder.generate_embedding(id_bytes)

        # Compute Cosine Similarity
        similarity = embedder.compute_cosine_similarity(emb_selfie, emb_id)
        is_authenticated = similarity >= SIMILARITY_THRESHOLD

        verdict = "VERIFIED" if is_authenticated else "MATCH_FAILED"
        message = (
            f"Facial biometrics match verified successfully ({round(similarity * 100, 2)}% match)."
            if is_authenticated else
            f"Biometric mismatch detected ({round(similarity * 100, 2)}% match). Authentication denied."
        )

        return VerificationResponse(
            status="success",
            is_authenticated=is_authenticated,
            similarity_score=round(similarity, 4),
            verification_result=verdict,
            message=message
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Facial verification failed: {str(e)}")

@app.post("/verify/register/{driver_id}")
async def register_driver_profile(
    driver_id: str,
    id_card: UploadFile = File(..., description="Official driver license/ID card photo")
):
    """
    Registers a driver's baseline facial embedding from their official ID photo.
    """
    try:
        id_bytes = await id_card.read()
        embedding = embedder.generate_embedding(id_bytes)
        registered_driver_embeddings[driver_id] = embedding

        return {
            "status": "success",
            "driver_id": driver_id,
            "embedding_dim": len(embedding),
            "message": f"Biometric profile successfully registered for driver '{driver_id}'."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/verify/authenticate/{driver_id}")
async def authenticate_driver(
    driver_id: str,
    selfie: UploadFile = File(..., description="Live selfie before starting trip shift")
):
    """
    Authenticates a live selfie against the driver's pre-registered baseline facial profile.
    """
    if driver_id not in registered_driver_embeddings:
        raise HTTPException(status_code=404, detail=f"Driver '{driver_id}' is not registered in system.")

    try:
        selfie_bytes = await selfie.read()
        emb_selfie = embedder.generate_embedding(selfie_bytes)
        emb_registered = registered_driver_embeddings[driver_id]

        similarity = embedder.compute_cosine_similarity(emb_selfie, emb_registered)
        is_authenticated = similarity >= SIMILARITY_THRESHOLD

        verdict = "VERIFIED" if is_authenticated else "MATCH_FAILED"
        message = (
            "Driver identity verified. Shift access granted."
            if is_authenticated else
            "Face mismatch detected. Driver account locked for security review."
        )

        return VerificationResponse(
            status="success",
            is_authenticated=is_authenticated,
            similarity_score=round(similarity, 4),
            verification_result=verdict,
            message=message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
