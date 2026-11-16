from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import UserCreate, UserLogin, UserResponse, Token
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.api.v1.deps import get_current_user, require_roles
from backend.app.core.logging import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Registers a new platform user with specified role (ADMIN, REVIEWER, or VIEWER).
    Enforces email uniqueness and secure bcrypt password hashing.
    """
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{user_in.email}' already exists."
        )

    # Validate role
    role = user_in.role.upper() if user_in.role else UserRole.REVIEWER
    if role not in UserRole.ALL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{role}'. Allowed roles: {UserRole.ALL}"
        )

    new_user = User(
        email=user_in.email.lower().strip(),
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Registered new user account: {new_user.email} (Role: {new_user.role})")
    return new_user


@router.post("/login", response_model=Token)
def login_user(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticates user credentials and issues a signed JWT Bearer access token.
    """
    user = db.query(User).filter(User.email == credentials.email.lower().strip()).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Please contact an administrator."
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        extra_claims={"email": user.email, "name": user.full_name}
    )

    logger.info(f"Successful login for user '{user.email}' (Role: {user.role})")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Returns the profile and role details of the currently authenticated user."""
    return current_user


@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    admin_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Lists all user accounts in the system. Restricted to ADMIN role only."""
    return db.query(User).order_by(User.created_at.desc()).all()

