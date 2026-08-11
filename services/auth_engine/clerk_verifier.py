import json
import base64
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, UserRole

logger = logging.getLogger(__name__)

def decode_jwt_payload_unverified(token: str) -> Dict[str, Any]:
    """
    Safely decodes JWT payload claims (Clerk session token).
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Invalid JWT token format")
        
        # Add base64 padding if necessary
        payload_b64 = parts[1]
        missing_padding = len(payload_b64) % 4
        if missing_padding:
            payload_b64 += '=' * (4 - missing_padding)
            
        decoded_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded_bytes.decode('utf-8'))
    except Exception as e:
        logger.error(f"Error decoding JWT token: {e}")
        return {}

async def sync_clerk_user_to_db(
    clerk_user_id: str,
    email: str,
    full_name: str,
    role: UserRole,
    db: AsyncSession
) -> User:
    """
    Creates or updates a Clerk user in the Aiven MySQL database shard.
    """
    res = await db.execute(select(User).filter(User.user_id == clerk_user_id))
    existing_user = res.scalars().first()

    if existing_user:
        existing_user.email = email
        existing_user.full_name = full_name
        existing_user.role = role
        await db.commit()
        await db.refresh(existing_user)
        logger.info(f"[CLERK SYNC] Updated user '{clerk_user_id}' with role '{role.value}'")
        return existing_user
    else:
        new_user = User(
            user_id=clerk_user_id,
            email=email,
            hashed_password="CLERK_AUTHENTICATED_OAUTH",
            full_name=full_name,
            role=role
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"[CLERK SYNC] Created new user '{clerk_user_id}' with role '{role.value}'")
        return new_user
