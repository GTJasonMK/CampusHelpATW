import copy
import re

from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.core.settings import get_settings
from app.db_models import (
    ChatMessage,
    Post,
    PostComment,
    Report,
    SystemConfig,
    Task,
    TaskCategory,
    TaskChat,
    TaskReview,
    TaskStatusLog,
    User,
)
from app.domain.task_state_machine import can_transition
from app.repositories.admin_repository import AdminRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.config_repository import ConfigRepository
from app.repositories.point_repository import PointRepository
from app.repositories.post_repository import PostRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UNSET, UserRepository
from app.schemas import (
    AdminArbitrateRequest,
    ChatReadMarkRequest,
    EmailVerifyRequest,
    PostCommentCreateRequest,
    PostCreateRequest,
    ReportCreateRequest,
    ReportHandleRequest,
    SystemConfigUpsertRequest,
    TaskActionReasonRequest,
    TaskCategoryCreateRequest,
    TaskCategoryPatchRequest,
    TaskCreateRequest,
    TaskReviewRequest,
    UserProfileUpdateRequest,
)

settings = get_settings()
TASK_STATUS_FILTER_SET = {
    "OPEN",
    "ACCEPTED",
    "IN_PROGRESS",
    "PENDING_CONFIRM",
    "DONE",
    "CANCELED",
    "DISPUTED",
}
TASK_SHARED_SORT_SET = {"latest", "deadline_asc", "reward_desc"}
POST_CATEGORY_SET = {"HELP", "SHARE", "RESOURCE", "ALERT"}
POST_SORT_SET = {"latest", "hot"}
ADMIN_POST_STATUS_SET = {"NORMAL", "HIDDEN", "DELETED"}
ADMIN_ROLE_CODE_SET = {"SUPER_ADMIN", "CONTENT_MODERATOR"}
TRANSACTION_CHANNEL_OPEN_STATUS_SET = {"ACCEPTED", "IN_PROGRESS", "PENDING_CONFIRM"}
TRANSACTION_CHANNEL_ARCHIVED_STATUS_SET = {"DONE", "CANCELED", "DISPUTED"}
SYSTEM_CONFIG_KEY_TRUST_LEVEL_RULES = "trust_level_rules"
SYSTEM_CONFIG_KEY_SCHOOL_BRANDING = "school_branding"
TRUST_LEVEL_STATUS_CLASS_SET = {
    "status-open",
    "status-processing",
    "status-done",
    "status-danger",
}
DEFAULT_TRUST_LEVEL_RULES = [
    {
        "key": "pillar",
        "label": "校园支柱",
        "description": "你已形成稳定可信的互助履约记录。",
        "status_class": "status-done",
        "min_reputation": 100,
        "min_honor_points": 120,
        "min_help_points": 0,
    },
    {
        "key": "steady",
        "label": "稳定互助者",
        "description": "你正在持续积累校园互助信用。",
        "status_class": "status-processing",
        "min_reputation": 50,
        "min_honor_points": 60,
        "min_help_points": 0,
    },
    {
        "key": "growth",
        "label": "成长互助者",
        "description": "继续完成任务闭环，可快速提升信用画像。",
        "status_class": "status-open",
        "min_reputation": 20,
        "min_honor_points": 0,
        "min_help_points": 50,
    },
    {
        "key": "newcomer",
        "label": "新手互助者",
        "description": "从清晰发布、及时确认、真实评价开始建立可信记录。",
        "status_class": "status-open",
        "min_reputation": 0,
        "min_honor_points": 0,
        "min_help_points": 0,
    },
]
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SCHOOL_PATTERN_TYPE_SET = {"none", "dots", "grid", "diagonal", "wave", "oil"}
DEFAULT_UI_THEME_TOKENS = {
    "paper_bg": "#f6fbf7",
    "paper_dot": "#d7e7dc",
    "ink": "#1f2f28",
    "card_bg": "#ffffff",
    "postit_bg": "#e8f5ec",
    "accent_bg": "#0f6a4c",
    "secondary_bg": "#dcece1",
    "secondary_text": "#1f2f28",
    "status_open_bg": "#eef8f0",
    "status_processing_bg": "#dceee3",
    "status_done_bg": "#d6f0df",
    "status_danger_bg": "#ffd9d9",
    "muted_text": "#4f5d56",
    "sub_title_text": "#304238",
    "error_text": "#c43d3d",
}
DEFAULT_SCHOOL_BRANDING_DEFAULTS = {
    "short_name": "中石大互助",
    "emblem_text": "油",
    "badge_text": "CUP",
    "slogan": "能源报国，互助同行",
    "accent_color": "#005f3c",
    "badge_bg_color": "#e8f5ec",
    "badge_text_color": "#103b2d",
    "pattern_type": "oil",
    "pattern_color": "#0f6a4c",
    "pattern_opacity": 0.18,
    "pattern_size": 22,
    "sticker_text": "石油特色",
    "sticker_bg_color": "#fff3cd",
    "sticker_text_color": "#2d2d2d",
    "ribbon_text": "中国石油大学",
    "ui_tokens": DEFAULT_UI_THEME_TOKENS,
}
DEFAULT_SCHOOL_BRANDING_SCHOOLS = [
    {
        "school_name": "中国石油大学",
        "aliases": ["中石大"],
        "short_name": "中石大",
        "emblem_text": "油",
        "badge_text": "CUP",
        "slogan": "能源报国，互助同行",
        "accent_color": "#005f3c",
        "badge_bg_color": "#e8f5ec",
        "badge_text_color": "#103b2d",
        "pattern_type": "oil",
        "pattern_color": "#0f6a4c",
        "pattern_opacity": 0.18,
        "pattern_size": 22,
        "sticker_text": "石油特色",
        "sticker_bg_color": "#fff3cd",
        "sticker_text_color": "#2d2d2d",
        "ribbon_text": "中国石油大学",
        "ui_tokens": DEFAULT_UI_THEME_TOKENS,
    },
    {
        "school_name": "中国石油大学（华东）",
        "aliases": ["中国石油大学(华东)", "中石大华东", "石大华东"],
        "short_name": "中石大华东",
        "emblem_text": "油",
        "badge_text": "CUP-EAST",
        "slogan": "立足能源，服务同学",
        "accent_color": "#006a43",
        "badge_bg_color": "#e8f5ec",
        "badge_text_color": "#103b2d",
        "pattern_type": "diagonal",
        "pattern_color": "#0b7b50",
        "pattern_opacity": 0.2,
        "pattern_size": 20,
        "sticker_text": "华东校区",
        "sticker_bg_color": "#fff1b8",
        "sticker_text_color": "#2d2d2d",
        "ribbon_text": "中国石油大学（华东）",
        "ui_tokens": {
            **DEFAULT_UI_THEME_TOKENS,
            "accent_bg": "#0b7b50",
            "secondary_bg": "#d6ebe0",
            "status_processing_bg": "#d2e9dc",
            "sub_title_text": "#2f4b3e",
        },
    },
    {
        "school_name": "中国石油大学（北京）",
        "aliases": ["中国石油大学(北京)", "中石大北京", "石大北京"],
        "short_name": "中石大北京",
        "emblem_text": "油",
        "badge_text": "CUP-BJ",
        "slogan": "求实创新，互助有温度",
        "accent_color": "#0a7a4b",
        "badge_bg_color": "#e7f4ed",
        "badge_text_color": "#103b2d",
        "pattern_type": "grid",
        "pattern_color": "#0d7449",
        "pattern_opacity": 0.16,
        "pattern_size": 18,
        "sticker_text": "北京校区",
        "sticker_bg_color": "#ffe7ba",
        "sticker_text_color": "#2d2d2d",
        "ribbon_text": "中国石油大学（北京）",
        "ui_tokens": {
            **DEFAULT_UI_THEME_TOKENS,
            "accent_bg": "#0d7449",
            "secondary_bg": "#d3e8dc",
            "postit_bg": "#f5efc9",
            "status_processing_bg": "#d7eadf",
        },
    },
    {
        "school_name": "CampusHelpATW",
        "aliases": [],
        "short_name": "中石大预览",
        "emblem_text": "油",
        "badge_text": "CUP-Preview",
        "slogan": "中国石油大学主题预览",
        "accent_color": "#005f3c",
        "badge_bg_color": "#e8f5ec",
        "badge_text_color": "#103b2d",
        "pattern_type": "oil",
        "pattern_color": "#0f6a4c",
        "pattern_opacity": 0.18,
        "pattern_size": 22,
        "sticker_text": "石油特色",
        "sticker_bg_color": "#fff3cd",
        "sticker_text_color": "#2d2d2d",
        "ribbon_text": "中国石油大学",
        "ui_tokens": DEFAULT_UI_THEME_TOKENS,
    }
]


def _copy_default_trust_level_rules() -> list[dict]:
    return [dict(item) for item in DEFAULT_TRUST_LEVEL_RULES]


def _copy_default_school_branding() -> dict:
    return {
        "defaults": copy.deepcopy(DEFAULT_SCHOOL_BRANDING_DEFAULTS),
        "schools": copy.deepcopy(DEFAULT_SCHOOL_BRANDING_SCHOOLS),
    }


def _normalize_non_negative_int(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _normalize_int_range(value: object, fallback: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < min_value:
        return min_value
    if parsed > max_value:
        return max_value
    return parsed


def _normalize_float_range(value: object, fallback: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < min_value:
        parsed = min_value
    if parsed > max_value:
        parsed = max_value
    return round(parsed, 2)


def _normalize_single_trust_level_rule(item: object) -> dict | None:
    if not isinstance(item, dict):
        return None

    label = str(item.get("label") or "").strip()
    description = str(item.get("description") or "").strip()
    if not label or not description:
        return None

    key = str(item.get("key") or "").strip() or "custom"
    status_class = str(item.get("status_class") or "status-open").strip()
    if status_class not in TRUST_LEVEL_STATUS_CLASS_SET:
        status_class = "status-open"

    return {
        "key": key[:32],
        "label": label[:32],
        "description": description[:120],
        "status_class": status_class,
        "min_reputation": _normalize_non_negative_int(item.get("min_reputation")),
        "min_honor_points": _normalize_non_negative_int(item.get("min_honor_points")),
        "min_help_points": _normalize_non_negative_int(item.get("min_help_points")),
    }


def _normalize_trust_level_rules(raw_value: object) -> list[dict] | None:
    raw_rules = raw_value
    if isinstance(raw_value, dict):
        raw_rules = raw_value.get("rules")
    if not isinstance(raw_rules, list):
        return None

    normalized: list[dict] = []
    for item in raw_rules[:8]:
        parsed = _normalize_single_trust_level_rule(item)
        if parsed is not None:
            normalized.append(parsed)

    if not normalized:
        return None

    has_fallback_rule = any(
        item["min_reputation"] <= 0
        and item["min_honor_points"] <= 0
        and item["min_help_points"] <= 0
        for item in normalized
    )
    if not has_fallback_rule:
        normalized.append(dict(DEFAULT_TRUST_LEVEL_RULES[-1]))

    return normalized


def _normalize_hex_color(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    if HEX_COLOR_RE.match(text):
        return text.lower()
    return fallback


def _normalize_school_brand_field(value: object, fallback: str, max_len: int) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return text[:max_len]


def _normalize_ui_theme_tokens(raw_value: object, fallback_tokens: dict[str, str]) -> dict[str, str]:
    item = raw_value if isinstance(raw_value, dict) else {}
    return {
        key: _normalize_hex_color(item.get(key), fallback_tokens[key])
        for key in fallback_tokens
    }


def _normalize_school_brand_defaults(raw_value: object) -> dict:
    item = raw_value if isinstance(raw_value, dict) else {}
    fallback = DEFAULT_SCHOOL_BRANDING_DEFAULTS
    pattern_type = str(item.get("pattern_type") or fallback["pattern_type"]).strip().lower()
    if pattern_type not in SCHOOL_PATTERN_TYPE_SET:
        pattern_type = fallback["pattern_type"]
    return {
        "short_name": _normalize_school_brand_field(item.get("short_name"), fallback["short_name"], 16),
        "emblem_text": _normalize_school_brand_field(item.get("emblem_text"), fallback["emblem_text"], 4),
        "badge_text": _normalize_school_brand_field(item.get("badge_text"), fallback["badge_text"], 24),
        "slogan": _normalize_school_brand_field(item.get("slogan"), fallback["slogan"], 48),
        "accent_color": _normalize_hex_color(item.get("accent_color"), fallback["accent_color"]),
        "badge_bg_color": _normalize_hex_color(item.get("badge_bg_color"), fallback["badge_bg_color"]),
        "badge_text_color": _normalize_hex_color(item.get("badge_text_color"), fallback["badge_text_color"]),
        "pattern_type": pattern_type,
        "pattern_color": _normalize_hex_color(item.get("pattern_color"), fallback["pattern_color"]),
        "pattern_opacity": _normalize_float_range(item.get("pattern_opacity"), fallback["pattern_opacity"], 0.0, 0.4),
        "pattern_size": _normalize_int_range(item.get("pattern_size"), fallback["pattern_size"], 8, 64),
        "sticker_text": _normalize_school_brand_field(item.get("sticker_text"), fallback["sticker_text"], 18),
        "sticker_bg_color": _normalize_hex_color(item.get("sticker_bg_color"), fallback["sticker_bg_color"]),
        "sticker_text_color": _normalize_hex_color(item.get("sticker_text_color"), fallback["sticker_text_color"]),
        "ribbon_text": _normalize_school_brand_field(item.get("ribbon_text"), fallback["ribbon_text"], 24),
        "ui_tokens": _normalize_ui_theme_tokens(item.get("ui_tokens"), fallback["ui_tokens"]),
    }


def _normalize_school_aliases(raw_aliases: object) -> list[str]:
    if not isinstance(raw_aliases, list):
        return []
    result: list[str] = []
    for item in raw_aliases[:20]:
        text = str(item or "").strip()[:64]
        if text and text not in result:
            result.append(text)
    return result


def _normalize_single_school_brand_item(item: object, defaults: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    school_name = str(item.get("school_name") or "").strip()[:64]
    if not school_name:
        return None
    pattern_type = str(item.get("pattern_type") or defaults["pattern_type"]).strip().lower()
    if pattern_type not in SCHOOL_PATTERN_TYPE_SET:
        pattern_type = defaults["pattern_type"]
    return {
        "school_name": school_name,
        "aliases": _normalize_school_aliases(item.get("aliases")),
        "short_name": _normalize_school_brand_field(item.get("short_name"), defaults["short_name"], 16),
        "emblem_text": _normalize_school_brand_field(item.get("emblem_text"), defaults["emblem_text"], 4),
        "badge_text": _normalize_school_brand_field(item.get("badge_text"), defaults["badge_text"], 24),
        "slogan": _normalize_school_brand_field(item.get("slogan"), defaults["slogan"], 48),
        "accent_color": _normalize_hex_color(item.get("accent_color"), defaults["accent_color"]),
        "badge_bg_color": _normalize_hex_color(item.get("badge_bg_color"), defaults["badge_bg_color"]),
        "badge_text_color": _normalize_hex_color(item.get("badge_text_color"), defaults["badge_text_color"]),
        "pattern_type": pattern_type,
        "pattern_color": _normalize_hex_color(item.get("pattern_color"), defaults["pattern_color"]),
        "pattern_opacity": _normalize_float_range(item.get("pattern_opacity"), defaults["pattern_opacity"], 0.0, 0.4),
        "pattern_size": _normalize_int_range(item.get("pattern_size"), defaults["pattern_size"], 8, 64),
        "sticker_text": _normalize_school_brand_field(item.get("sticker_text"), defaults["sticker_text"], 18),
        "sticker_bg_color": _normalize_hex_color(item.get("sticker_bg_color"), defaults["sticker_bg_color"]),
        "sticker_text_color": _normalize_hex_color(item.get("sticker_text_color"), defaults["sticker_text_color"]),
        "ribbon_text": _normalize_school_brand_field(item.get("ribbon_text"), defaults["ribbon_text"], 24),
        "ui_tokens": _normalize_ui_theme_tokens(item.get("ui_tokens"), defaults["ui_tokens"]),
    }


def _normalize_school_branding(raw_value: object) -> dict | None:
    if not isinstance(raw_value, dict):
        return None

    defaults = _normalize_school_brand_defaults(raw_value.get("defaults"))
    raw_schools = raw_value.get("schools")
    schools: list[dict] = []
    if isinstance(raw_schools, list):
        seen_school_keys: set[str] = set()
        for item in raw_schools[:200]:
            parsed = _normalize_single_school_brand_item(item, defaults)
            if parsed is None:
                continue
            dedupe_key = parsed["school_name"].strip().lower()
            if dedupe_key in seen_school_keys:
                continue
            seen_school_keys.add(dedupe_key)
            schools.append(parsed)

    return {
        "defaults": defaults,
        "schools": schools,
    }


def _to_auth_payload(user: User, token: str) -> dict:
    return {
        "token": token,
        "user": {
            "id": user.id,
            "campus_email": user.campus_email,
            "nickname": user.nickname,
        },
    }


def _raise_if_invalid_transition(from_status: str, to_status: str) -> None:
    if not can_transition(from_status, to_status):
        raise AppError(
            code=4009,
            message=f"invalid task status transition: {from_status} -> {to_status}",
        )


async def verify_email_login(db, payload: EmailVerifyRequest) -> dict:
    if payload.code != settings.dev_verify_code and settings.app_env != "prod":
        raise AppError(code=4001, message="dev code mismatch")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(payload.campus_email)
    if user is None:
        raise AppError(code=4004, message="user not found")
    if user.status != "ACTIVE":
        raise AppError(code=4003, message="user not active", http_status=401)
    if not verify_password(payload.password, user.password_hash):
        raise AppError(code=4001, message="password mismatch", http_status=401)

    token = create_access_token(user.id)
    return _to_auth_payload(user, token)


async def update_profile(db, user: User, payload: UserProfileUpdateRequest) -> User:
    user_repo = UserRepository(db)
    provided_fields = set(getattr(payload, "model_fields_set", set()))
    nickname = payload.nickname if "nickname" in provided_fields else UNSET
    avatar_url = payload.avatar_url if "avatar_url" in provided_fields else UNSET
    college_name = payload.college_name if "college_name" in provided_fields else UNSET
    return await user_repo.update_profile(
        user=user,
        nickname=nickname,
        avatar_url=avatar_url,
        college_name=college_name,
    )


def _normalize_role_codes(role_codes: list[str] | None) -> list[str]:
    normalized = {
        str(item or "").strip().upper()
        for item in (role_codes or [])
        if str(item or "").strip()
    }
    return sorted(normalized)


async def get_user_permissions(db, user: User) -> dict:
    role_codes = _normalize_role_codes(await UserRepository(db).list_role_codes(user.id))
    is_admin = any(item in ADMIN_ROLE_CODE_SET for item in role_codes)
    return {
        "is_admin": bool(is_admin),
        "can_manage_community": bool(is_admin),
        "role_codes": role_codes,
    }


def _to_user_brief(user: User) -> dict:
    return {
        "id": int(user.id),
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "school_name": user.school_name,
        "college_name": user.college_name,
        "status": user.status,
    }


async def get_user_public_profile(db, current_user: User, target_user_id: int) -> dict:
    target_user = await UserRepository(db).get_by_id(target_user_id)
    if target_user is None:
        raise AppError(code=4004, message="user not found", http_status=404)
    if target_user.status != "ACTIVE":
        raise AppError(code=4004, message="user not active", http_status=404)

    review_count, review_avg_rating = await TaskRepository(db).get_user_review_stats(target_user_id)
    common_task_count = 0
    if int(current_user.id) != int(target_user_id):
        common_task_count = await TaskRepository(db).count_shared_tasks_between_users(
            int(current_user.id),
            int(target_user_id),
        )

    return {
        "id": int(target_user.id),
        "nickname": target_user.nickname,
        "avatar_url": target_user.avatar_url,
        "campus_email": target_user.campus_email,
        "school_name": target_user.school_name,
        "college_name": target_user.college_name,
        "status": target_user.status,
        "reputation_score": int(target_user.reputation_score or 0),
        "help_points_balance": int(target_user.help_points_balance or 0),
        "honor_points_balance": int(target_user.honor_points_balance or 0),
        "review_count": int(review_count),
        "review_avg_rating": round(float(review_avg_rating or 0.0), 2),
        "shared_stats": {
            "common_task_count": int(common_task_count),
        },
    }


async def list_shared_tasks_between_users(
    db,
    current_user: User,
    target_user_id: int,
    page: int,
    page_size: int,
    status: str | None = None,
    sort: str = "latest",
) -> dict:
    target_user = await UserRepository(db).get_by_id(target_user_id)
    if target_user is None or target_user.status != "ACTIVE":
        raise AppError(code=4004, message="user not found", http_status=404)

    normalized_status = str(status or "").strip().upper() or None
    if normalized_status and normalized_status not in TASK_STATUS_FILTER_SET:
        raise AppError(
            code=4001,
            message=(
                "status must be OPEN/ACCEPTED/IN_PROGRESS/PENDING_CONFIRM/"
                "DONE/CANCELED/DISPUTED"
            ),
        )
    normalized_sort = str(sort or "latest").strip().lower() or "latest"
    if normalized_sort not in TASK_SHARED_SORT_SET:
        raise AppError(code=4001, message="sort must be latest/deadline_asc/reward_desc")

    if int(current_user.id) == int(target_user_id):
        return {
            "list": [],
            "page": page,
            "page_size": page_size,
            "total": 0,
            "target_user_id": int(target_user_id),
            "status": normalized_status,
            "sort": normalized_sort,
        }

    task_repo = TaskRepository(db)
    items, total = await task_repo.list_shared_tasks_between_users(
        user_id_a=int(current_user.id),
        user_id_b=int(target_user_id),
        page=page,
        page_size=page_size,
        status=normalized_status,
        sort=normalized_sort,
    )
    users = await UserRepository(db).list_by_ids([int(current_user.id), int(target_user_id)])
    user_map = {int(item.id): item for item in users}

    rows = []
    for item in items:
        rows.append(
            {
                "id": int(item.id),
                "title": item.title,
                "description": item.description,
                "category": item.category,
                "location_text": item.location_text,
                "reward_amount": item.reward_amount,
                "reward_type": item.reward_type,
                "deadline_at": item.deadline_at.isoformat() if item.deadline_at else None,
                "status": item.status,
                "publisher_id": int(item.publisher_id),
                "acceptor_id": int(item.acceptor_id) if item.acceptor_id else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "publisher_user": _to_user_brief(user_map.get(int(item.publisher_id))),
                "acceptor_user": (
                    _to_user_brief(user_map.get(int(item.acceptor_id))) if item.acceptor_id else None
                ),
            }
        )

    return {
        "list": rows,
        "page": page,
        "page_size": page_size,
        "total": total,
        "target_user_id": int(target_user_id),
        "status": normalized_status,
        "sort": normalized_sort,
    }


async def create_task(db, user: User, payload: TaskCreateRequest) -> Task:
    task_repo = TaskRepository(db)
    task = await task_repo.create(
        publisher_id=user.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        location_text=payload.location_text,
        reward_amount=payload.reward_amount,
        reward_type=payload.reward_type,
        deadline_at=payload.deadline_at,
    )

    publish_cost = max(0, int(settings.task_publish_help_cost))
    if publish_cost <= 0:
        return task

    try:
        await _add_points(
            db=db,
            user_id=user.id,
            point_type="HELP",
            change_amount=-publish_cost,
            biz_type="TASK_PUBLISH",
            biz_id=task.id,
            remark="task publish fee",
        )
    except AppError as exc:
        # 若发单扣点失败，回滚任务创建，避免“任务已发布但积分未扣”的不一致。
        await TaskRepository(db).delete_by_id(task.id)
        if "insufficient HELP points" in exc.message:
            raise AppError(code=4009, message="insufficient HELP points to publish task") from exc
        raise

    return task


async def list_tasks(
    db,
    status: str | None,
    category: str | None,
    page: int,
    page_size: int,
    current_user: User | None = None,
    include_unread: bool = True,
    keyword: str | None = None,
    publisher_id: int | None = None,
    acceptor_id: int | None = None,
    participant_id: int | None = None,
) -> dict:
    task_repo = TaskRepository(db)
    items, total = await task_repo.list(
        status=status,
        category=category,
        page=page,
        page_size=page_size,
        keyword=keyword,
        publisher_id=publisher_id,
        acceptor_id=acceptor_id,
        participant_id=participant_id,
    )
    data = {"list": items, "page": page, "page_size": page_size, "total": total}
    if include_unread and current_user is not None:
        unread_items = await ChatRepository(db).list_unread_counts_by_user(current_user.id)
        unread_map = {int(item["task_id"]): int(item["unread_count"]) for item in unread_items}
        data["task_unread_map"] = unread_map
        data["total_unread"] = sum(unread_map.values())
    return data


async def get_task_or_404(db, task_id: int) -> Task:
    task = await TaskRepository(db).get_by_id(task_id)
    if task is None:
        raise AppError(code=4004, message="task not found", http_status=404)
    return task


async def update_task(db, task_id: int, operator: User, payload) -> Task:
    task = await get_task_or_404(db, task_id)
    if int(task.publisher_id) != int(operator.id):
        raise AppError(code=4003, message="仅发布者可编辑任务", http_status=403)
    if str(task.status or "").upper() != "OPEN":
        raise AppError(code=4009, message="仅待接单状态可编辑", http_status=409)
    fields = {}
    data = payload.model_dump(exclude_unset=True)
    for key in ("title", "description", "category", "location_text", "reward_amount", "reward_type", "deadline_at"):
        if key in data and data[key] is not None:
            fields[key] = data[key]
    if not fields:
        return task
    return await TaskRepository(db).update(task, **fields)


async def get_task_unread_summary(db, user: User, task_id: int) -> dict:
    item = await ChatRepository(db).get_unread_count_by_user_and_task(user_id=user.id, task_id=task_id)
    if item is not None:
        return item
    return {
        "task_id": int(task_id),
        "chat_id": 0,
        "unread_count": 0,
        "latest_message_id": 0,
        "last_read_message_id": 0,
    }


async def list_task_status_logs(db, task_id: int) -> list[TaskStatusLog]:
    await get_task_or_404(db, task_id)
    return await TaskRepository(db).list_status_logs(task_id)


async def list_admin_tasks(
    db,
    status: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    task_repo = TaskRepository(db)
    items, total = await task_repo.list_for_admin(
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        keyword=keyword,
    )
    return {"list": items, "page": page, "page_size": page_size, "total": total}


async def _transition_task(db, task: Task, to_status: str, operator_user_id: int, reason: str) -> None:
    _raise_if_invalid_transition(task.status, to_status)
    task_repo = TaskRepository(db)
    try:
        await task_repo.transition(
            task_id=task.id,
            to_status=to_status,
            operator_user_id=operator_user_id,
            reason=reason,
        )
    except Exception as exc:
        await db.rollback()
        raise AppError(code=4009, message=f"task transition failed: {exc}") from exc


async def _add_points(
    db,
    user_id: int,
    point_type: str,
    change_amount: int,
    biz_type: str,
    biz_id: int,
    remark: str,
) -> None:
    point_repo = PointRepository(db)
    try:
        await point_repo.add_points(
            user_id=user_id,
            point_type=point_type,
            change_amount=change_amount,
            biz_type=biz_type,
            biz_id=biz_id,
            remark=remark,
        )
    except Exception as exc:
        await db.rollback()
        raise AppError(code=4009, message=f"point update failed: {exc}") from exc


async def accept_task(db, task_id: int, operator: User, payload: TaskActionReasonRequest) -> None:
    task = await get_task_or_404(db, task_id)
    if task.status != "OPEN":
        raise AppError(code=4009, message="task is not open")
    if task.publisher_id == operator.id:
        raise AppError(code=4009, message="publisher cannot accept own task")

    if task.acceptor_id is None:
        await TaskRepository(db).set_acceptor(task_id=task.id, acceptor_id=operator.id)
        task.acceptor_id = operator.id

    await _transition_task(
        db=db,
        task=task,
        to_status="ACCEPTED",
        operator_user_id=operator.id,
        reason=payload.reason or "accept task",
    )


async def start_task(db, task_id: int, operator: User, payload: TaskActionReasonRequest) -> None:
    task = await get_task_or_404(db, task_id)
    if task.acceptor_id != operator.id:
        raise AppError(code=4009, message="only acceptor can start task")
    await _transition_task(
        db=db,
        task=task,
        to_status="IN_PROGRESS",
        operator_user_id=operator.id,
        reason=payload.reason or "start task",
    )


async def submit_task_completion(db, task_id: int, operator: User, payload: TaskActionReasonRequest) -> None:
    task = await get_task_or_404(db, task_id)
    if task.acceptor_id != operator.id:
        raise AppError(code=4009, message="only acceptor can submit completion")
    await _transition_task(
        db=db,
        task=task,
        to_status="PENDING_CONFIRM",
        operator_user_id=operator.id,
        reason=payload.reason or "submit completion",
    )


async def confirm_task_completion(db, task_id: int, operator: User, payload: TaskActionReasonRequest) -> None:
    task = await get_task_or_404(db, task_id)
    if task.publisher_id != operator.id:
        raise AppError(code=4009, message="only publisher can confirm completion")
    if task.acceptor_id is None:
        raise AppError(code=4009, message="task has no acceptor")

    await _transition_task(
        db=db,
        task=task,
        to_status="DONE",
        operator_user_id=operator.id,
        reason=payload.reason or "confirm completion",
    )

    await _add_points(
        db=db,
        user_id=task.acceptor_id,
        point_type="HELP",
        change_amount=settings.default_help_reward,
        biz_type="TASK_COMPLETE",
        biz_id=task.id,
        remark="task complete reward",
    )
    await _add_points(
        db=db,
        user_id=task.acceptor_id,
        point_type="HONOR",
        change_amount=settings.default_honor_reward,
        biz_type="TASK_COMPLETE",
        biz_id=task.id,
        remark="task complete reward",
    )
    await _add_points(
        db=db,
        user_id=task.publisher_id,
        point_type="HONOR",
        change_amount=settings.default_confirm_honor_reward,
        biz_type="TASK_CONFIRM",
        biz_id=task.id,
        remark="task confirm reward",
    )


async def dispute_task(db, task_id: int, operator: User, payload: TaskActionReasonRequest) -> None:
    task = await get_task_or_404(db, task_id)
    if operator.id not in {task.publisher_id, task.acceptor_id}:
        raise AppError(code=4009, message="only participants can dispute")
    await _transition_task(
        db=db,
        task=task,
        to_status="DISPUTED",
        operator_user_id=operator.id,
        reason=payload.reason or "dispute task",
    )


async def cancel_task(db, task_id: int, operator: User, payload: TaskActionReasonRequest) -> None:
    task = await get_task_or_404(db, task_id)
    if task.status == "OPEN":
        if operator.id != task.publisher_id:
            raise AppError(code=4009, message="only publisher can cancel open task")
    elif task.status in {"ACCEPTED", "IN_PROGRESS"}:
        if operator.id not in {task.publisher_id, task.acceptor_id}:
            raise AppError(code=4009, message="only participants can cancel task")
    else:
        raise AppError(code=4009, message=f"task cannot be canceled in status {task.status}")

    await _transition_task(
        db=db,
        task=task,
        to_status="CANCELED",
        operator_user_id=operator.id,
        reason=payload.reason or "cancel task",
    )


async def create_task_review(db, task_id: int, operator: User, payload: TaskReviewRequest) -> TaskReview:
    task = await get_task_or_404(db, task_id)
    if task.status != "DONE":
        raise AppError(code=4009, message="task is not done")
    if operator.id not in {task.publisher_id, task.acceptor_id}:
        raise AppError(code=4009, message="only participants can review")

    try:
        return await TaskRepository(db).create_review(
            task_id=task.id,
            reviewer_id=operator.id,
            reviewee_id=payload.reviewee_id,
            rating=payload.rating,
            content=payload.content,
        )
    except Exception as exc:
        await db.rollback()
        raise AppError(code=4009, message=f"create review failed: {exc}") from exc


async def list_user_reviews(
    db,
    user_id: int,
    page: int,
    page_size: int,
    rating: int | None = None,
    with_content: bool | None = None,
) -> dict:
    items, total = await TaskRepository(db).list_user_reviews(
        reviewee_id=user_id,
        page=page,
        page_size=page_size,
        rating=rating,
        with_content=with_content,
    )
    return {
        "list": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "rating": rating,
        "with_content": bool(with_content),
    }


async def list_my_points(db, user_id: int, point_type: str | None, page: int, page_size: int) -> dict:
    items, total = await PointRepository(db).list_user_points(
        user_id=user_id,
        point_type=point_type,
        page=page,
        page_size=page_size,
    )
    return {"list": items, "page": page, "page_size": page_size, "total": total}


async def create_post(db, author: User, payload: PostCreateRequest) -> Post:
    normalized_category = str(payload.category or "").strip().upper()
    if normalized_category not in POST_CATEGORY_SET:
        raise AppError(code=4001, message="category must be HELP/SHARE/RESOURCE/ALERT")
    return await PostRepository(db).create(
        author_id=author.id,
        title=payload.title,
        content=payload.content,
        category=normalized_category,
    )


async def list_posts(
    db,
    page: int,
    page_size: int,
    current_user: User,
    category: str | None = None,
    sort: str = "latest",
    keyword: str | None = None,
) -> dict:
    normalized_category = str(category or "").strip().upper()
    if normalized_category == "ALL":
        normalized_category = ""
    if normalized_category and normalized_category not in POST_CATEGORY_SET:
        raise AppError(code=4001, message="category must be HELP/SHARE/RESOURCE/ALERT")

    normalized_sort = str(sort or "latest").strip().lower() or "latest"
    if normalized_sort not in POST_SORT_SET:
        raise AppError(code=4001, message="sort must be latest/hot")

    normalized_keyword = str(keyword or "").strip()
    repo = PostRepository(db)
    items, total = await repo.list(
        page=page,
        page_size=page_size,
        category=normalized_category or None,
        sort=normalized_sort,
        keyword=normalized_keyword or None,
    )
    liked_post_ids = await repo.list_liked_post_ids(
        user_id=int(current_user.id),
        post_ids=[int(item.id) for item in items],
    )
    return {
        "list": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "category": normalized_category or None,
        "sort": normalized_sort,
        "keyword": normalized_keyword or None,
        "liked_post_ids": sorted(liked_post_ids),
    }


async def list_my_posts(
    db,
    current_user: User,
    page: int,
    page_size: int,
    category: str | None = None,
    sort: str = "latest",
    keyword: str | None = None,
) -> dict:
    normalized_category = str(category or "").strip().upper()
    if normalized_category == "ALL":
        normalized_category = ""
    if normalized_category and normalized_category not in POST_CATEGORY_SET:
        raise AppError(code=4001, message="category must be HELP/SHARE/RESOURCE/ALERT")

    normalized_sort = str(sort or "latest").strip().lower() or "latest"
    if normalized_sort not in POST_SORT_SET:
        raise AppError(code=4001, message="sort must be latest/hot")

    normalized_keyword = str(keyword or "").strip()
    repo = PostRepository(db)
    items, total = await repo.list(
        page=page,
        page_size=page_size,
        category=normalized_category or None,
        sort=normalized_sort,
        keyword=normalized_keyword or None,
        author_id=int(current_user.id),
    )
    liked_post_ids = await repo.list_liked_post_ids(
        user_id=int(current_user.id),
        post_ids=[int(item.id) for item in items],
    )
    return {
        "list": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "category": normalized_category or None,
        "sort": normalized_sort,
        "keyword": normalized_keyword or None,
        "liked_post_ids": sorted(liked_post_ids),
    }


async def get_post_or_404(db, post_id: int) -> Post:
    post = await PostRepository(db).get_by_id(post_id)
    if post is None or str(post.status or "").upper() != "NORMAL":
        raise AppError(code=4004, message="post not found", http_status=404)
    return post


async def get_post_detail(db, post_id: int, current_user: User) -> dict:
    repo = PostRepository(db)
    post = await get_post_or_404(db, post_id)
    await repo.increase_view_count(post)
    liked = await repo.get_like(post_id=post.id, user_id=current_user.id)
    return {
        "post": post,
        "liked_by_me": liked is not None,
    }


async def list_post_comments(db, post_id: int, page: int, page_size: int) -> dict:
    await get_post_or_404(db, post_id)
    items, total = await PostRepository(db).list_comments(
        post_id=post_id,
        page=page,
        page_size=page_size,
    )
    return {"list": items, "page": page, "page_size": page_size, "total": total}


async def create_post_comment(db, post_id: int, author: User, payload: PostCommentCreateRequest) -> PostComment:
    post = await get_post_or_404(db, post_id)
    return await PostRepository(db).create_comment(post=post, author_id=author.id, content=payload.content)


async def like_post(db, post_id: int, user: User) -> None:
    repo = PostRepository(db)
    post = await get_post_or_404(db, post_id)
    existing = await repo.get_like(post_id=post.id, user_id=user.id)
    if existing is None:
        await repo.create_like(post=post, user_id=user.id)


async def unlike_post(db, post_id: int, user: User) -> None:
    repo = PostRepository(db)
    post = await get_post_or_404(db, post_id)
    existing = await repo.get_like(post_id=post.id, user_id=user.id)
    if existing is not None:
        await repo.remove_like(post=post, like=existing)


async def delete_post(db, post_id: int, user: User) -> None:
    repo = PostRepository(db)
    post = await get_post_or_404(db, post_id)
    if int(post.author_id) != int(user.id):
        raise AppError(code=4009, message="only post author can delete", http_status=403)
    await repo.soft_delete(post)


async def list_admin_posts(
    db,
    page: int,
    page_size: int,
    status: str | None = None,
    category: str | None = None,
    sort: str = "latest",
    keyword: str | None = None,
    author_id: int | None = None,
) -> dict:
    normalized_status = str(status or "").strip().upper()
    if normalized_status == "ALL":
        normalized_status = ""
    if normalized_status and normalized_status not in ADMIN_POST_STATUS_SET:
        raise AppError(code=4001, message="status must be NORMAL/HIDDEN/DELETED")

    normalized_category = str(category or "").strip().upper()
    if normalized_category == "ALL":
        normalized_category = ""
    if normalized_category and normalized_category not in POST_CATEGORY_SET:
        raise AppError(code=4001, message="category must be HELP/SHARE/RESOURCE/ALERT")

    normalized_sort = str(sort or "latest").strip().lower() or "latest"
    if normalized_sort not in POST_SORT_SET:
        raise AppError(code=4001, message="sort must be latest/hot")

    normalized_keyword = str(keyword or "").strip()
    normalized_author_id = int(author_id) if author_id is not None else None
    if normalized_author_id is not None and normalized_author_id <= 0:
        raise AppError(code=4001, message="author_id must be positive")

    items, total = await PostRepository(db).list_for_admin(
        page=page,
        page_size=page_size,
        status=normalized_status or None,
        category=normalized_category or None,
        sort=normalized_sort,
        keyword=normalized_keyword or None,
        author_id=normalized_author_id,
    )
    return {
        "list": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "status": normalized_status or None,
        "category": normalized_category or None,
        "sort": normalized_sort,
        "keyword": normalized_keyword or None,
        "author_id": normalized_author_id,
    }


async def patch_admin_post_status(
    db,
    post_id: int,
    admin: User,
    status: str,
    reason: str | None = None,
) -> Post:
    repo = PostRepository(db)
    post = await repo.get_by_id(post_id)
    if post is None:
        raise AppError(code=4004, message="post not found", http_status=404)

    normalized_status = str(status or "").strip().upper()
    if normalized_status not in ADMIN_POST_STATUS_SET:
        raise AppError(code=4001, message="status must be NORMAL/HIDDEN/DELETED")

    old_status = str(post.status or "").strip().upper()
    if old_status != normalized_status:
        post = await repo.update_status(post=post, status=normalized_status)

    detail = f"{old_status}->{normalized_status}"
    normalized_reason = str(reason or "").strip()
    if normalized_reason:
        detail = f"{detail}; reason={normalized_reason}"
    await AdminRepository(db).add_operation_log(
        admin_user_id=admin.id,
        operation_type="POST_MODERATE",
        target_type="POST",
        target_id=int(post.id),
        detail=detail,
    )
    return post


def get_transaction_channel_state(task: Task | None) -> dict:
    if task is None:
        return {
            "task_status": "",
            "channel_open": False,
            "channel_archived": False,
            "channel_available": False,
            "reason": "task_not_found",
        }

    status = str(task.status or "").upper()
    if status == "OPEN":
        return {
            "task_status": status,
            "channel_open": True,
            "channel_archived": False,
            "channel_available": True,
            "reason": "open_for_seekers",
        }

    publisher_id = int(task.publisher_id or 0)
    acceptor_id = int(task.acceptor_id or 0)
    has_counterparty = acceptor_id > 0 and acceptor_id != publisher_id
    channel_open = has_counterparty and status in TRANSACTION_CHANNEL_OPEN_STATUS_SET
    channel_archived = has_counterparty and status in TRANSACTION_CHANNEL_ARCHIVED_STATUS_SET
    channel_available = channel_open or channel_archived

    if not has_counterparty:
        reason = "not_accepted"
    elif channel_open:
        reason = "active"
    elif channel_archived:
        reason = "archived"
    else:
        reason = "unsupported_status"

    return {
        "task_status": status,
        "channel_open": channel_open,
        "channel_archived": channel_archived,
        "channel_available": channel_available,
        "reason": reason,
    }


def can_user_access_task_chat(task: Task, user_id: int) -> bool:
    uid = int(user_id or 0)
    if uid <= 0:
        return False
    status = str(task.status or "").upper()
    if status == "OPEN":
        return True
    return uid in {int(task.publisher_id or 0), int(task.acceptor_id or 0)}


def _ensure_transaction_channel_available(task: Task) -> None:
    state = get_transaction_channel_state(task)
    if state["channel_available"]:
        return
    reason = state["reason"]
    if reason == "not_accepted":
        raise AppError(code=4009, message="transaction channel not opened yet")
    raise AppError(code=4009, message=f"transaction channel unavailable in status {state['task_status']}")


def _ensure_transaction_channel_writable(task: Task) -> None:
    state = get_transaction_channel_state(task)
    if state["channel_open"]:
        return
    if state["channel_archived"]:
        raise AppError(code=4009, message="transaction channel archived; cannot send new message")
    if state["reason"] == "not_accepted":
        raise AppError(code=4009, message="transaction channel not opened yet")
    raise AppError(code=4009, message=f"transaction channel unavailable in status {state['task_status']}")


async def get_task_chat(db, task_id: int, operator: User) -> TaskChat:
    task = await get_task_or_404(db, task_id)
    if not can_user_access_task_chat(task, operator.id):
        raise AppError(code=4009, message="only participants can access chat")
    _ensure_transaction_channel_available(task)
    return await ChatRepository(db).get_or_create_by_task_id(task.id)


async def _get_chat_or_forbidden(db, chat_id: int, user: User) -> TaskChat:
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_by_chat_id(chat_id)
    if chat is None:
        raise AppError(code=4004, message="chat not found", http_status=404)
    task = await get_task_or_404(db, chat.task_id)
    if not can_user_access_task_chat(task, user.id):
        raise AppError(code=4009, message="only participants can access chat", http_status=403)
    _ensure_transaction_channel_available(task)
    return chat


async def list_chat_messages(db, chat_id: int, cursor: int, page_size: int, operator: User) -> list[ChatMessage]:
    await _get_chat_or_forbidden(db=db, chat_id=chat_id, user=operator)
    return await ChatRepository(db).list_messages(chat_id=chat_id, cursor=cursor, page_size=page_size)


async def create_chat_message(
    db,
    chat_id: int,
    sender: User,
    message_type: str,
    content: str,
) -> ChatMessage:
    chat = await _get_chat_or_forbidden(db=db, chat_id=chat_id, user=sender)
    task = await get_task_or_404(db, chat.task_id)
    _ensure_transaction_channel_writable(task)
    chat_repo = ChatRepository(db)
    return await chat_repo.create_message(
        chat_id=chat_id,
        sender_id=sender.id,
        message_type=message_type,
        content=content,
    )


async def list_my_chat_unread(db, user: User) -> dict:
    items = await ChatRepository(db).list_unread_counts_by_user(user.id)
    total_unread = sum(max(0, int(item["unread_count"])) for item in items)
    return {"total_unread": total_unread, "items": items}


async def mark_chat_read(
    db,
    chat_id: int,
    operator: User,
    payload: ChatReadMarkRequest | None,
) -> dict:
    chat = await _get_chat_or_forbidden(db=db, chat_id=chat_id, user=operator)
    chat_repo = ChatRepository(db)
    latest_message_id = await chat_repo.get_latest_message_id(chat.id)

    requested_last_read = (
        payload.last_read_message_id
        if payload is not None and payload.last_read_message_id is not None
        else latest_message_id
    )
    target_last_read = min(max(0, int(requested_last_read)), int(latest_message_id))
    cursor = await chat_repo.touch_read_cursor(
        chat_id=chat.id,
        user_id=operator.id,
        last_read_message_id=target_last_read,
    )
    return {
        "chat_id": chat.id,
        "task_id": chat.task_id,
        "latest_message_id": latest_message_id,
        "last_read_message_id": int(cursor.last_read_message_id),
    }


async def create_report(db, reporter: User, payload: ReportCreateRequest) -> Report:
    return await ReportRepository(db).create(
        reporter_id=reporter.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason_code=payload.reason_code,
        reason_text=payload.reason_text,
    )


async def list_my_reports(db, reporter_id: int, page: int, page_size: int) -> dict:
    items, total = await ReportRepository(db).list_by_reporter(
        reporter_id=reporter_id,
        page=page,
        page_size=page_size,
    )
    return {"list": items, "page": page, "page_size": page_size, "total": total}


async def require_admin(db, user: User) -> None:
    permissions = await get_user_permissions(db, user)
    if not bool(permissions.get("is_admin")):
        raise AppError(code=4003, message="admin role required", http_status=403)


async def list_admin_reports(db, status: str | None, page: int, page_size: int) -> dict:
    items, total = await ReportRepository(db).list_for_admin(
        status=status,
        page=page,
        page_size=page_size,
    )
    return {"list": items, "page": page, "page_size": page_size, "total": total}


async def handle_report(db, report_id: int, admin: User, payload: ReportHandleRequest) -> Report:
    report_repo = ReportRepository(db)
    report = await report_repo.get_by_id(report_id)
    if report is None:
        raise AppError(code=4004, message="report not found", http_status=404)

    normalized_action = str(payload.action or "").strip().upper()
    handled = await report_repo.handle(
        report=report,
        admin_id=admin.id,
        action=normalized_action,
        result=payload.result,
    )

    detail = f"{normalized_action}: {payload.result}"
    target_type = str(report.target_type or "").strip().upper()
    target_id = int(report.target_id or 0)
    if normalized_action == "RESOLVE" and target_type == "POST" and target_id > 0:
        post_repo = PostRepository(db)
        target_post = await post_repo.get_by_id(target_id)
        if target_post is not None and str(target_post.status or "").upper() == "NORMAL":
            await post_repo.update_status(post=target_post, status="HIDDEN")
            detail = f"{detail}; auto_hide_post={target_id}"

    await AdminRepository(db).add_operation_log(
        admin_user_id=admin.id,
        operation_type="REPORT_REVIEW",
        target_type="REPORT",
        target_id=report.id,
        detail=detail,
    )
    return handled


async def arbitrate_task(db, task_id: int, admin: User, payload: AdminArbitrateRequest) -> None:
    task = await get_task_or_404(db, task_id)
    to_status = "DONE" if payload.decision.upper() == "MARK_DONE" else "CANCELED"
    await _transition_task(
        db=db,
        task=task,
        to_status=to_status,
        operator_user_id=admin.id,
        reason=payload.reason,
    )
    await AdminRepository(db).add_operation_log(
        admin_user_id=admin.id,
        operation_type="TASK_ARBITRATE",
        target_type="TASK",
        target_id=task_id,
        detail=f"{payload.decision}: {payload.reason}",
    )


async def list_admin_task_categories(
    db,
    page: int,
    page_size: int,
    is_active: bool | None = None,
) -> dict:
    items, total = await ConfigRepository(db).list_task_categories(
        page=page,
        page_size=page_size,
        is_active=is_active,
    )
    return {"list": items, "page": page, "page_size": page_size, "total": total}


async def create_admin_task_category(
    db,
    admin: User,
    payload: TaskCategoryCreateRequest,
) -> TaskCategory:
    repo = ConfigRepository(db)
    normalized_code = payload.code.strip().upper()
    existing = await repo.get_task_category_by_code(normalized_code)
    if existing is not None:
        raise AppError(code=4009, message="task category code already exists")

    try:
        item = await repo.create_task_category(
            code=normalized_code,
            name=payload.name,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
    except Exception as exc:
        await db.rollback()
        raise AppError(code=4009, message=f"create task category failed: {exc}") from exc

    await AdminRepository(db).add_operation_log(
        admin_user_id=admin.id,
        operation_type="TASK_CATEGORY_CREATE",
        target_type="TASK_CATEGORY",
        target_id=item.id,
        detail=f"{item.code}:{item.name}",
    )
    return item


async def patch_admin_task_category(
    db,
    category_id: int,
    admin: User,
    payload: TaskCategoryPatchRequest,
) -> TaskCategory:
    if (
        payload.code is None
        and payload.name is None
        and payload.sort_order is None
        and payload.is_active is None
    ):
        raise AppError(code=4001, message="at least one field is required")

    repo = ConfigRepository(db)
    item = await repo.get_task_category_by_id(category_id)
    if item is None:
        raise AppError(code=4004, message="task category not found", http_status=404)

    normalized_code = payload.code.strip().upper() if payload.code is not None else None
    if normalized_code is not None and normalized_code != item.code:
        existing = await repo.get_task_category_by_code(normalized_code)
        if existing is not None and existing.id != item.id:
            raise AppError(code=4009, message="task category code already exists")

    try:
        updated = await repo.update_task_category(
            item=item,
            code=normalized_code,
            name=payload.name,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
    except Exception as exc:
        await db.rollback()
        raise AppError(code=4009, message=f"patch task category failed: {exc}") from exc

    await AdminRepository(db).add_operation_log(
        admin_user_id=admin.id,
        operation_type="TASK_CATEGORY_UPDATE",
        target_type="TASK_CATEGORY",
        target_id=updated.id,
        detail=f"{updated.code}:{updated.name}",
    )
    return updated


async def list_admin_system_configs(db, page: int, page_size: int) -> dict:
    items, total = await ConfigRepository(db).list_system_configs(page=page, page_size=page_size)
    return {"list": items, "page": page, "page_size": page_size, "total": total}


async def put_admin_system_config(
    db,
    admin: User,
    config_key: str,
    payload: SystemConfigUpsertRequest,
) -> SystemConfig:
    normalized_key = config_key.strip()
    if not normalized_key:
        raise AppError(code=4001, message="config_key cannot be empty")

    try:
        item = await ConfigRepository(db).upsert_system_config(
            config_key=normalized_key,
            config_value=payload.config_value,
            description=payload.description,
        )
    except Exception as exc:
        await db.rollback()
        raise AppError(code=4009, message=f"put system config failed: {exc}") from exc

    await AdminRepository(db).add_operation_log(
        admin_user_id=admin.id,
        operation_type="SYSTEM_CONFIG_UPSERT",
        target_type="SYSTEM_CONFIG",
        target_id=item.id,
        detail=item.config_key,
    )
    return item


async def get_admin_school_branding_config(db) -> dict:
    return await get_meta_school_branding(db=db)


async def put_admin_school_branding_config(
    db,
    admin: User,
    payload: SystemConfigUpsertRequest,
) -> dict:
    normalized = _normalize_school_branding(payload.config_value)
    if normalized is None:
        raise AppError(code=4001, message="invalid school branding payload")

    try:
        item = await ConfigRepository(db).upsert_system_config(
            config_key=SYSTEM_CONFIG_KEY_SCHOOL_BRANDING,
            config_value=normalized,
            description=payload.description or "学校专属样式配置",
        )
    except Exception as exc:
        await db.rollback()
        raise AppError(code=4009, message=f"put school branding failed: {exc}") from exc

    await AdminRepository(db).add_operation_log(
        admin_user_id=admin.id,
        operation_type="SCHOOL_BRANDING_UPSERT",
        target_type="SYSTEM_CONFIG",
        target_id=item.id,
        detail=SYSTEM_CONFIG_KEY_SCHOOL_BRANDING,
    )
    return await get_meta_school_branding(db=db)


async def list_meta_task_categories(db) -> list[TaskCategory]:
    items, _ = await ConfigRepository(db).list_task_categories(
        page=None,
        page_size=None,
        is_active=True,
    )
    return items


async def get_meta_trust_level_rules(db) -> dict:
    item = await ConfigRepository(db).get_system_config_by_key(SYSTEM_CONFIG_KEY_TRUST_LEVEL_RULES)
    if item is None:
        return {
            "config_key": SYSTEM_CONFIG_KEY_TRUST_LEVEL_RULES,
            "source": "default",
            "rules": _copy_default_trust_level_rules(),
        }

    normalized = _normalize_trust_level_rules(item.config_value)
    if normalized is None:
        return {
            "config_key": SYSTEM_CONFIG_KEY_TRUST_LEVEL_RULES,
            "source": "system_config_invalid",
            "rules": _copy_default_trust_level_rules(),
        }

    return {
        "config_key": SYSTEM_CONFIG_KEY_TRUST_LEVEL_RULES,
        "source": "system_config",
        "rules": normalized,
    }


async def get_meta_school_branding(db) -> dict:
    item = await ConfigRepository(db).get_system_config_by_key(SYSTEM_CONFIG_KEY_SCHOOL_BRANDING)
    if item is None:
        return {
            "config_key": SYSTEM_CONFIG_KEY_SCHOOL_BRANDING,
            "source": "default",
            **_copy_default_school_branding(),
        }

    normalized = _normalize_school_branding(item.config_value)
    if normalized is None:
        return {
            "config_key": SYSTEM_CONFIG_KEY_SCHOOL_BRANDING,
            "source": "system_config_invalid",
            **_copy_default_school_branding(),
        }

    return {
        "config_key": SYSTEM_CONFIG_KEY_SCHOOL_BRANDING,
        "source": "system_config",
        **normalized,
    }


async def update_task_acceptor(db, task_id: int, acceptor_id: int) -> None:
    await TaskRepository(db).set_acceptor(task_id=task_id, acceptor_id=acceptor_id)
