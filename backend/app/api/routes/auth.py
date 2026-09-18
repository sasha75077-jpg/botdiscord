from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta
import httpx
from ...core.config import settings
from ...core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, verify_token
from ...core.database import get_db, Database
from ...schemas import OwnerLogin, TokenResponse, DiscordAuthCallback, TokenRefresh

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/owner/login", response_model=TokenResponse)
async def owner_login(
    credentials: OwnerLogin,
    db: Database = Depends(get_db)
):
    """Owner логин через email и пароль"""

    # Проверить есть ли owner аккаунт
    owner = await db.fetch_one("SELECT * FROM owner_account WHERE id = 1")

    # Если аккаунта нет - создать из .env
    if not owner:
        from ...core.config import settings
        password_hash = get_password_hash(settings.OWNER_PASSWORD)
        await db.execute(
            "INSERT INTO owner_account (id, email, password_hash) VALUES (1, ?, ?)",
            (settings.OWNER_EMAIL, password_hash)
        )
        owner = await db.fetch_one("SELECT * FROM owner_account WHERE id = 1")

    # Проверить email
    if owner["email"] != credentials.email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Проверить пароль
    if not verify_password(credentials.password, owner["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Обновить last_login
    await db.execute(
        "UPDATE owner_account SET last_login = CURRENT_TIMESTAMP WHERE id = 1"
    )

    # Создать токены
    access_token = create_access_token(
        data={"user_type": "owner", "email": owner["email"]}
    )
    refresh_token = create_refresh_token(
        data={"user_type": "owner", "email": owner["email"]}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.get("/discord/url")
async def get_discord_oauth_url(guild_id: str = None):
    """Получить URL для Discord OAuth2"""
    scope = "identify guilds email"
    redirect_uri = settings.DISCORD_REDIRECT_URI

    state = f"guild:{guild_id}" if guild_id else "none"

    oauth_url = (
        f"{settings.DISCORD_API_ENDPOINT}/oauth2/authorize"
        f"?client_id={settings.DISCORD_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
    )

    return {"url": oauth_url}

@router.post("/discord/login")
async def discord_oauth_url(guild_id: str = None):
    """Получить URL для Discord OAuth2 (legacy)"""
    scope = "identify guilds"
    redirect_uri = settings.DISCORD_REDIRECT_URI

    state = f"guild:{guild_id}" if guild_id else "none"

    oauth_url = (
        f"{settings.DISCORD_API_ENDPOINT}/oauth2/authorize"
        f"?client_id={settings.DISCORD_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
    )

    return {"oauth_url": oauth_url}

@router.post("/discord/callback", response_model=TokenResponse)
async def discord_oauth_callback(
    callback: DiscordAuthCallback,
    db: Database = Depends(get_db)
):
    """Discord OAuth2 callback"""

    # Обменять code на access_token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{settings.DISCORD_API_ENDPOINT}/oauth2/token",
            data={
                "client_id": settings.DISCORD_CLIENT_ID,
                "client_secret": settings.DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": callback.code,
                "redirect_uri": settings.DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")

        token_data = token_response.json()
        discord_access_token = token_data["access_token"]

        # Получить информацию о пользователе
        user_response = await client.get(
            f"{settings.DISCORD_API_ENDPOINT}/users/@me",
            headers={"Authorization": f"Bearer {discord_access_token}"}
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_data = user_response.json()
        discord_id = user_data["id"]

        # Получить список серверов пользователя
        guilds_response = await client.get(
            f"{settings.DISCORD_API_ENDPOINT}/users/@me/guilds",
            headers={"Authorization": f"Bearer {discord_access_token}"}
        )

        if guilds_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get guilds")

        user_guilds = guilds_response.json()

    # Если guild_id указан, проверить что пользователь на этом сервере
    if callback.guild_id:
        guild_ids = [g["id"] for g in user_guilds]
        if callback.guild_id not in guild_ids:
            raise HTTPException(status_code=403, detail="You are not a member of this guild")

        target_guild_id = callback.guild_id
    else:
        # Найти первый зарегистрированный сервер
        registered_guilds = await db.fetch_all(
            "SELECT guild_id FROM guilds WHERE is_active = 1"
        )
        registered_guild_ids = [g["guild_id"] for g in registered_guilds]

        user_guild_ids = [g["id"] for g in user_guilds]
        common_guilds = [gid for gid in user_guild_ids if gid in registered_guild_ids]

        if not common_guilds:
            raise HTTPException(
                status_code=404,
                detail="You are not a member of any registered guild"
            )

        target_guild_id = common_guilds[0]

    # Получить права пользователя на сервере
    permission = await db.fetch_one(
        "SELECT role FROM permissions WHERE discord_id = ? AND guild_id = ?",
        (discord_id, target_guild_id)
    )

    role = permission["role"] if permission else "user"

    # Создать JWT токены
    access_token = create_access_token(
        data={
            "user_type": "discord",
            "discord_id": discord_id,
            "guild_id": target_guild_id,
            "role": role
        }
    )

    refresh_token = create_refresh_token(
        data={
            "user_type": "discord",
            "discord_id": discord_id,
            "guild_id": target_guild_id,
            "role": role
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_data: TokenRefresh,
    db: Database = Depends(get_db)
):
    """Обновить access token через refresh token"""

    payload = verify_token(refresh_data.refresh_token, "refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Создать новые токены
    user_type = payload.get("user_type")

    if user_type == "owner":
        access_token = create_access_token(
            data={"user_type": "owner", "email": payload.get("email")}
        )
        new_refresh_token = create_refresh_token(
            data={"user_type": "owner", "email": payload.get("email")}
        )
    elif user_type == "discord":
        # Обновить роль на случай если изменилась
        discord_id = payload.get("discord_id")
        guild_id = payload.get("guild_id")

        permission = await db.fetch_one(
            "SELECT role FROM permissions WHERE discord_id = ? AND guild_id = ?",
            (discord_id, guild_id)
        )

        role = permission["role"] if permission else "user"

        access_token = create_access_token(
            data={
                "user_type": "discord",
                "discord_id": discord_id,
                "guild_id": guild_id,
                "role": role
            }
        )
        new_refresh_token = create_refresh_token(
            data={
                "user_type": "discord",
                "discord_id": discord_id,
                "guild_id": guild_id,
                "role": role
            }
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid token payload")

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )

@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(lambda: None)  # Заполним позже
):
    """Получить информацию о текущем пользователе"""
    from ..dependencies import get_current_user
    user = await get_current_user()
    return user
