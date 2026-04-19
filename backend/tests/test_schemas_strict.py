import pytest
from pydantic import ValidationError

from app.schemas import EmailVerifyRequest, TaskCreateRequest


def test_email_verify_request_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        EmailVerifyRequest(
            campus_email="alice@campus.local",
            code="123456",
            password="ChangeMe123!",
            extra_field="x",
        )


def test_task_create_request_strip_whitespace() -> None:
    req = TaskCreateRequest(
        title="  代取快递  ",
        description="  今晚帮取  ",
        category="  ERRAND  ",
        location_text=" 东区驿站 ",
        reward_amount=5,
        reward_type="CASH",
        deadline_at="2026-03-01T19:00:00+08:00",
    )
    assert req.title == "代取快递"
    assert req.description == "今晚帮取"
    assert req.category == "ERRAND"
    assert req.location_text == "东区驿站"


def test_email_verify_request_accepts_camel_case_email_field() -> None:
    req = EmailVerifyRequest(
        campusEmail="alice@campus.local",
        code="123456",
        password="ChangeMe123!",
    )
    assert req.campus_email == "alice@campus.local"
