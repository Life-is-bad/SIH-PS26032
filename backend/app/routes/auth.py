from fastapi import APIRouter, HTTPException, status
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse
from app.models.models import create_user, get_user_by_phone
from app.auth_utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest):
    existing = get_user_by_phone(payload.phone_number)
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    hashed = hash_password(payload.password)
    user_id = create_user(
        role=payload.role,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        password_hash=hashed,
        email=payload.email,
    )

    token = create_access_token(user_id=user_id, role=payload.role)
    return TokenResponse(access_token=token, role=payload.role, user_id=user_id)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = get_user_by_phone(payload.phone_number)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid phone number or password")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(user_id=user["user_id"], role=user["role"])
    return TokenResponse(access_token=token, role=user["role"], user_id=user["user_id"])
