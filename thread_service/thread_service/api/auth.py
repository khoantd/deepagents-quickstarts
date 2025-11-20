"""Authentication API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    create_access_token,
    generate_email_verification_token,
    generate_password_reset_token,
    get_token_expiry,
    hash_password,
    verify_password,
)
from ..db import get_session
from ..email import send_email_verification, send_password_reset
from ..middleware import get_current_user
from ..models import User
from ..repositories import (
    create_email_verification_token,
    create_oauth_account,
    create_password_reset_token,
    create_user,
    delete_password_reset_token,
    get_oauth_account,
    get_user_by_email,
    get_user_by_id,
    update_user_password,
    verify_email_token,
    verify_password_reset_token,
    verify_user_email,
)
from ..schemas import (
    EmailVerificationRequest,
    LoginRequest,
    OAuthUserInfo,
    PasswordResetConfirm,
    PasswordResetRequest,
    SignupRequest,
    TokenResponse,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Register a new user with email and password.

    Args:
        payload: Signup request data
        session: Database session

    Returns:
        Token response with user data

    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = await get_user_by_email(session, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    password_hash = hash_password(payload.password)
    user = await create_user(
        session,
        email=payload.email,
        password_hash=password_hash,
        name=payload.name,
    )

    # Generate email verification token
    token = generate_email_verification_token()
    expires_at = get_token_expiry(hours=24)
    await create_email_verification_token(
        session,
        user_id=user.id,
        token=token,
        expires_at=expires_at,
    )

    # Send verification email
    try:
        await send_email_verification(user.email, user.name or "User", token)
    except Exception:
        # Log error but don't fail signup
        pass

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return TokenResponse(
        access_token=access_token,
        user=UserRead.model_validate(user, from_attributes=True),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Authenticate user with email and password.

    Args:
        payload: Login request data
        session: Database session

    Returns:
        Token response with user data

    Raises:
        HTTPException: If credentials are invalid
    """
    user = await get_user_by_email(session, payload.email)
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return TokenResponse(
        access_token=access_token,
        user=UserRead.model_validate(user, from_attributes=True),
    )


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Get current user profile.

    Args:
        current_user: Current authenticated user

    Returns:
        User profile data
    """
    return UserRead.model_validate(current_user, from_attributes=True)


@router.put("/me", response_model=UserRead)
async def update_current_user_profile(
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRead:
    """Update current user profile.

    Args:
        payload: User update data
        current_user: Current authenticated user
        session: Database session

    Returns:
        Updated user profile data
    """
    if payload.name is not None:
        current_user.name = payload.name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url

    await session.commit()
    await session.refresh(current_user)

    return UserRead.model_validate(current_user, from_attributes=True)


@router.post("/verify-email")
async def verify_email(
    payload: EmailVerificationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Verify user email with token.

    Args:
        payload: Email verification request
        session: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid or expired
    """
    verification_token = await verify_email_token(session, payload.token)
    if not verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user = await verify_user_email(session, verification_token.user_id)
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Resend email verification token.

    Args:
        current_user: Current authenticated user
        session: Database session

    Returns:
        Success message
    """
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    # Generate new verification token
    token = generate_email_verification_token()
    expires_at = get_token_expiry(hours=24)
    await create_email_verification_token(
        session,
        user_id=current_user.id,
        token=token,
        expires_at=expires_at,
    )

    # Send verification email
    try:
        await send_email_verification(
            current_user.email,
            current_user.name or "User",
            token,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return {"message": "Verification email sent"}


@router.post("/forgot-password")
async def forgot_password(
    payload: PasswordResetRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Request password reset.

    Args:
        payload: Password reset request
        session: Database session

    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    user = await get_user_by_email(session, payload.email)
    if user:
        # Generate reset token
        token = generate_password_reset_token()
        expires_at = get_token_expiry(hours=1)
        await create_password_reset_token(
            session,
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )

        # Send reset email
        try:
            await send_password_reset(user.email, user.name or "User", token)
        except Exception:
            # Log error but don't reveal it
            pass

    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    payload: PasswordResetConfirm,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Reset password with token.

    Args:
        payload: Password reset confirmation
        session: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid or expired
    """
    reset_token = await verify_password_reset_token(session, payload.token)
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password
    password_hash = hash_password(payload.new_password)
    await update_user_password(session, reset_token.user_id, password_hash)

    # Delete used token
    await delete_password_reset_token(session, payload.token)

    return {"message": "Password reset successfully"}


@router.get("/oauth/{provider}")
async def oauth_redirect(provider: str) -> dict[str, str]:
    """Redirect to OAuth provider.

    Args:
        provider: OAuth provider name (google, github)

    Returns:
        OAuth authorization URL

    Raises:
        HTTPException: If provider is not supported
    """
    from ..settings import get_settings

    settings = get_settings()
    frontend_url = settings.frontend_url

    if provider == "google":
        client_id = settings.oauth_google_client_id
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth not configured",
            )
        redirect_uri = f"{frontend_url}/api/auth/callback/google"
        scope = "openid email profile"
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
        )
        return {"auth_url": auth_url}

    elif provider == "github":
        client_id = settings.oauth_github_client_id
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="GitHub OAuth not configured",
            )
        redirect_uri = f"{frontend_url}/api/auth/callback/github"
        scope = "user:email"
        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
        )
        return {"auth_url": auth_url}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Handle OAuth callback and create/login user.

    Args:
        provider: OAuth provider name
        code: OAuth authorization code
        session: Database session

    Returns:
        Token response with user data

    Raises:
        HTTPException: If OAuth flow fails
    """
    from ..settings import get_settings

    settings = get_settings()

    if provider == "google":
        client_id = settings.oauth_google_client_id
        client_secret = settings.oauth_google_client_secret
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth not configured",
            )

        # Exchange code for token
        import httpx

        frontend_url = settings.frontend_url
        redirect_uri = f"{frontend_url}/api/auth/callback/google"

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange OAuth code",
                )
            token_data = token_response.json()
            access_token = token_data["access_token"]

            # Get user info
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch user info",
                )
            user_info = user_response.json()

        provider_user_id = user_info["id"]
        email = user_info["email"]
        name = user_info.get("name")
        avatar_url = user_info.get("picture")

    elif provider == "github":
        client_id = settings.oauth_github_client_id
        client_secret = settings.oauth_github_client_secret
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="GitHub OAuth not configured",
            )

        # Exchange code for token
        import httpx

        frontend_url = settings.frontend_url
        redirect_uri = f"{frontend_url}/api/auth/callback/github"

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange OAuth code",
                )
            token_data = token_response.json()
            access_token = token_data["access_token"]

            # Get user info
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch user info",
                )
            user_info = user_response.json()

            # Get email (may need to fetch from emails endpoint)
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            emails = email_response.json() if email_response.status_code == 200 else []
            primary_email = next((e["email"] for e in emails if e.get("primary")), None)
            email = primary_email or user_info.get("email") or f"{user_info['login']}@users.noreply.github.com"

        provider_user_id = str(user_info["id"])
        name = user_info.get("name") or user_info.get("login")
        avatar_url = user_info.get("avatar_url")

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    # Check if OAuth account exists
    oauth_account = await get_oauth_account(session, provider=provider, provider_user_id=provider_user_id)

    if oauth_account:
        # Existing user - login
        user = await get_user_by_id(session, oauth_account.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth account linked to non-existent user",
            )
    else:
        # Check if user with email exists
        user = await get_user_by_email(session, email)
        if user:
            # Link OAuth account to existing user
            await create_oauth_account(
                session,
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
            )
        else:
            # Create new user
            user = await create_user(
                session,
                email=email,
                password_hash=None,  # OAuth users don't have passwords
                name=name,
                avatar_url=avatar_url,
            )
            user.email_verified = True  # OAuth emails are pre-verified
            await session.commit()

            # Create OAuth account
            await create_oauth_account(
                session,
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
            )

    # Create access token
    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return TokenResponse(
        access_token=jwt_token,
        user=UserRead.model_validate(user, from_attributes=True),
    )


@router.post("/oauth/sync", response_model=TokenResponse)
async def oauth_sync(
    payload: OAuthUserInfo,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Sync OAuth user from NextAuth with backend.

    This endpoint is called by NextAuth after OAuth completes to create/login
    the user in the backend and get a backend JWT token.

    Args:
        payload: OAuth user information from NextAuth
        session: Database session

    Returns:
        Token response with user data and backend JWT token

    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Check if OAuth account exists
        oauth_account = await get_oauth_account(
            session,
            provider=payload.provider,
            provider_user_id=payload.provider_user_id,
        )

        if oauth_account:
            # Existing user - login
            user = await get_user_by_id(session, oauth_account.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OAuth account linked to non-existent user",
                )
        else:
            # Check if user with email exists
            user = await get_user_by_email(session, payload.email)
            if user:
                # Link OAuth account to existing user
                await create_oauth_account(
                    session,
                    user_id=user.id,
                    provider=payload.provider,
                    provider_user_id=payload.provider_user_id,
                    access_token=None,  # Not storing access token from NextAuth
                )
            else:
                # Create new user
                user = await create_user(
                    session,
                    email=payload.email,
                    password_hash=None,  # OAuth users don't have passwords
                    name=payload.name,
                    avatar_url=payload.avatar_url,
                )
                user.email_verified = True  # OAuth emails are pre-verified
                await session.commit()
                await session.refresh(user)

                # Create OAuth account
                await create_oauth_account(
                    session,
                    user_id=user.id,
                    provider=payload.provider,
                    provider_user_id=payload.provider_user_id,
                    access_token=None,  # Not storing access token from NextAuth
                )

        # Refresh user to ensure we have latest data
        await session.refresh(user)

        # Create access token
        jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email})

        return TokenResponse(
            access_token=jwt_token,
            user=UserRead.model_validate(user, from_attributes=True),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Error in OAuth sync: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync OAuth user: {str(e)}",
        ) from e

