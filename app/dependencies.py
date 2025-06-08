from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import redis
from app.database import SessionLocal, get_db
from app.config import settings

# Security
security = HTTPBearer()

def get_database() -> Generator:
    """
    Database dependency that yields a database session.
    This ensures proper session management and cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_redis_client():
    """
    Redis dependency for caching and session management.
    Returns a Redis client instance.
    """
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Test connection
        redis_client.ping()
        return redis_client
    except redis.ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service unavailable"
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_database)
):
    """
    JWT token validation dependency.
    For now, this is a placeholder for future authentication.
    """
    # Placeholder for JWT validation
    # In production, you would validate the JWT token here
    # and return the current user from the database
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # For development, we'll skip JWT validation
        # In production, implement proper JWT validation
        if not credentials.credentials:
            raise credentials_exception
            
        # Mock user for development
        return {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "is_active": True
        }
        
    except JWTError:
        raise credentials_exception

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_database)
):
    """
    Optional user dependency for endpoints that work with or without authentication.
    """
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None

def validate_pagination(
    skip: int = 0,
    limit: int = 100
) -> dict:
    """
    Pagination validation dependency.
    Ensures pagination parameters are within acceptable ranges.
    """
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be >= 0"
        )
    
    if limit <= 0 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit parameter must be between 1 and 1000"
        )
    
    return {"skip": skip, "limit": limit}

def validate_date_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> dict:
    """
    Date range validation dependency for analytics endpoints.
    """
    from datetime import datetime
    
    result = {"start_date": None, "end_date": None}
    
    if start_date:
        try:
            result["start_date"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    if end_date:
        try:
            result["end_date"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    if result["start_date"] and result["end_date"]:
        if result["start_date"] >= result["end_date"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )
    
    return result

class RateLimiter:
    """
    Rate limiting dependency for API endpoints.
    Uses Redis to track request counts per IP/user.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def __call__(
        self,
        request,
        redis_client = Depends(get_redis_client)
    ):
        # Get client IP
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        try:
            # Get current request count
            current_requests = redis_client.get(key)
            
            if current_requests is None:
                # First request in window
                redis_client.setex(key, self.window_seconds, 1)
                return True
            
            if int(current_requests) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds"
                )
            
            # Increment counter
            redis_client.incr(key)
            return True
            
        except redis.RedisError:
            # If Redis is down, allow the request
            return True

# Pre-configured rate limiters for different endpoint types
scraper_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 10 requests per minute
analytics_rate_limiter = RateLimiter(max_requests=50, window_seconds=300)  # 50 requests per 5 minutes
general_rate_limiter = RateLimiter(max_requests=100, window_seconds=3600)  # 100 requests per hour
