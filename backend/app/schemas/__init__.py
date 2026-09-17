from pydantic import BaseModel, EmailStr
from typing import Optional, Literal, Any
from datetime import datetime

# Auth Schemas
class OwnerLogin(BaseModel):
    email: EmailStr
    password: str

class DiscordAuthCallback(BaseModel):
    code: str
    guild_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefresh(BaseModel):
    refresh_token: str

# User Schemas
class UserBase(BaseModel):
    discord_id: str
    guild_id: str

class UserProfile(BaseModel):
    discord_id: str
    guild_id: str
    username: str
    avatar_url: Optional[str] = None
    current_rank_id: Optional[int] = None
    rank_name: Optional[str] = None
    surname_changed: int
    family_total: int
    tuning_total: int
    role: Literal["owner", "admin", "user"]

class UserStats(BaseModel):
    total_contracts: int
    pending_contracts: int
    approved_contracts: int
    rejected_contracts: int
    total_bonus_amount: float
    approved_bonus_reports: int

# Guild Schemas
class GuildBase(BaseModel):
    guild_id: str
    guild_name: str
    owner_id: Optional[str] = None
    icon_url: Optional[str] = None

class GuildDetail(GuildBase):
    is_active: bool
    added_at: datetime
    total_users: int
    total_contracts: int
    pending_contracts: int

class GuildSettings(BaseModel):
    settings: dict[str, str]

class GuildModules(BaseModel):
    modules: list[dict[str, Any]]

# Contract Schemas
class ContractBase(BaseModel):
    guild_id: str
    discord_id: str
    contract_type: str
    details: Optional[str] = None

class ContractDetail(BaseModel):
    id: int
    guild_id: str
    ts: str
    discord_id: str
    contract_type: str
    channel_id: Optional[str] = None
    discord_message_id: Optional[str] = None
    attachment_urls: Optional[str] = None
    msk_date: Optional[str] = None
    details: Optional[str] = None
    price: float
    confirm_status: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    reject_reason: Optional[str] = None

class ContractUpdate(BaseModel):
    confirm_status: Optional[str] = None
    reject_reason: Optional[str] = None

class ContractListResponse(BaseModel):
    contracts: list[ContractDetail]
    total: int
    page: int
    page_size: int

# Report Schemas
class BonusReportBase(BaseModel):
    guild_id: str
    discord_id: str
    week_start: str
    week_end: str

class BonusReportDetail(BaseModel):
    report_id: int
    guild_id: str
    discord_id: str
    week_start: str
    week_end: str
    total_amount: float
    contracts_json: Optional[str] = None
    submitted_at: str
    status: str
    taken_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None

class BonusReportApprove(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: Optional[str] = None

# Permission Schemas
class PermissionBase(BaseModel):
    guild_id: str
    discord_id: str
    role: Literal["owner", "admin", "user"]

class PermissionResponse(PermissionBase):
    id: int
    granted_at: datetime
    granted_by: Optional[str] = None
