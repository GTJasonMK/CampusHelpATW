from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any = None


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmailSendCodeRequest(StrictRequestModel):
    campus_email: str = Field(
        min_length=3,
        max_length=128,
        validation_alias=AliasChoices("campus_email", "campusEmail"),
    )

    @field_validator("campus_email")
    @classmethod
    def validate_campus_email(cls, value: str) -> str:
        if value.count("@") != 1:
            raise ValueError("invalid campus email format")
        local_part, domain = value.split("@", 1)
        if not local_part or not domain:
            raise ValueError("invalid campus email format")
        return value


class EmailVerifyRequest(StrictRequestModel):
    campus_email: str = Field(
        min_length=3,
        max_length=128,
        validation_alias=AliasChoices("campus_email", "campusEmail"),
    )
    code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("campus_email")
    @classmethod
    def validate_campus_email(cls, value: str) -> str:
        if value.count("@") != 1:
            raise ValueError("invalid campus email format")
        local_part, domain = value.split("@", 1)
        if not local_part or not domain:
            raise ValueError("invalid campus email format")
        return value


class UserProfileUpdateRequest(StrictRequestModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=64)
    avatar_url: str | None = None
    college_name: str | None = Field(default=None, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campus_email: str
    nickname: str
    avatar_url: str | None = None
    school_name: str | None = None
    college_name: str | None = None
    reputation_score: int
    help_points_balance: int
    honor_points_balance: int
    status: str


class TaskCreateRequest(StrictRequestModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=32)
    location_text: str | None = Field(default=None, max_length=255)
    reward_amount: Decimal = Decimal("0.00")
    reward_type: str = "NONE"
    deadline_at: datetime


class TaskUpdateRequest(StrictRequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1, max_length=32)
    location_text: str | None = Field(default=None, max_length=255)
    reward_amount: Decimal | None = None
    reward_type: str | None = None
    deadline_at: datetime | None = None


class TaskActionReasonRequest(StrictRequestModel):
    reason: str | None = Field(default=None, max_length=255)


class TaskReviewRequest(StrictRequestModel):
    reviewee_id: int
    rating: int = Field(ge=1, le=5)
    content: str | None = Field(default=None, max_length=500)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    publisher_id: int
    acceptor_id: int | None = None
    title: str
    description: str
    category: str
    location_text: str | None = None
    reward_amount: Decimal
    reward_type: str
    deadline_at: datetime
    status: str
    accepted_at: datetime | None = None
    completed_at: datetime | None = None
    canceled_at: datetime | None = None
    unread_count: int | None = None
    created_at: datetime
    updated_at: datetime


class TaskStatusLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    from_status: str | None
    to_status: str
    operator_user_id: int
    reason: str | None
    created_at: datetime


class ChatMessageCreateRequest(StrictRequestModel):
    message_type: str = "TEXT"
    content: str = Field(min_length=1)


class ChatReadMarkRequest(StrictRequestModel):
    last_read_message_id: int | None = Field(default=None, ge=0)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    sender_id: int
    message_type: str
    content: str
    created_at: datetime


class ReportCreateRequest(StrictRequestModel):
    target_type: str = Field(min_length=1, max_length=32)
    target_id: int
    reason_code: str = Field(min_length=1, max_length=32)
    reason_text: str | None = Field(default=None, max_length=500)


class ReportHandleRequest(StrictRequestModel):
    action: str = Field(min_length=1, max_length=32)
    result: str = Field(min_length=1, max_length=500)


class AdminArbitrateRequest(StrictRequestModel):
    decision: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=255)


class AdminPostStatusPatchRequest(StrictRequestModel):
    status: str = Field(min_length=1, max_length=16)
    reason: str | None = Field(default=None, max_length=255)

    @field_validator("status")
    @classmethod
    def validate_admin_post_status(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if normalized not in {"NORMAL", "HIDDEN", "DELETED"}:
            raise ValueError("status must be NORMAL/HIDDEN/DELETED")
        return normalized


class PostCreateRequest(StrictRequestModel):
    title: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1)
    category: str = Field(default="HELP", min_length=1, max_length=16)

    @field_validator("category")
    @classmethod
    def validate_post_category(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if normalized not in {"HELP", "SHARE", "RESOURCE", "ALERT"}:
            raise ValueError("category must be HELP/SHARE/RESOURCE/ALERT")
        return normalized


class PostCommentCreateRequest(StrictRequestModel):
    content: str = Field(min_length=1, max_length=1000)


class TaskCategoryCreateRequest(StrictRequestModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    sort_order: int = Field(default=0)
    is_active: bool = True


class TaskCategoryPatchRequest(StrictRequestModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    sort_order: int | None = None
    is_active: bool | None = None


class TaskCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SystemConfigUpsertRequest(StrictRequestModel):
    config_value: Any
    description: str | None = Field(default=None, max_length=255)


class SystemConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    config_key: str
    config_value: Any
    description: str | None = None
    created_at: datetime
    updated_at: datetime
