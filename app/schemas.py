from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class TrafficType(str, Enum):
    AUTHENTICATION = "AUTHENTICATION"
    TRANSACTION = "TRANSACTION"
    PROMOTION = "PROMOTION"
    SERVICEREQUEST = "SERVICEREQUEST"
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"


class RichCardRequest(BaseModel):
    phone: str = Field(..., examples=["+5518999999999"])
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    image_url: HttpUrl
    button_text: str = Field(..., min_length=1, max_length=25)
    button_url: HttpUrl
    postback_data: str = Field(default="open_url", max_length=2048)
    traffic_type: TrafficType = TrafficType.PROMOTION

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not value.startswith("+") or not value[1:].isdigit() or len(value) < 8:
            raise ValueError("phone deve estar no formato E.164, por exemplo +5518999999999")
        return value


class BroadcastRequest(BaseModel):
    phones: list[str] = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    image_url: HttpUrl
    button_text: str = Field(..., min_length=1, max_length=25)
    button_url: HttpUrl
    postback_data: str = Field(default="open_url", max_length=2048)
    traffic_type: TrafficType = TrafficType.PROMOTION

    @field_validator("phones")
    @classmethod
    def validate_phones(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            phone = raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if not phone.startswith("+") or not phone[1:].isdigit() or len(phone) < 8:
                raise ValueError(f"telefone inválido: {raw}. Use E.164, ex.: +5518999999999")
            if phone not in seen:
                normalized.append(phone)
                seen.add(phone)
        return normalized


class SendResult(BaseModel):
    phone: str
    success: bool
    message_id: str | None = None
    status_code: int | None = None
    error: str | None = None
    response: dict | None = None


class BroadcastResult(BaseModel):
    total: int
    sent: int
    failed: int
    results: list[SendResult]
