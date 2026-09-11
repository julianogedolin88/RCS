from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas import BroadcastRequest, BroadcastResult, RichCardRequest, SendResult
from app.services.google_rcs import GoogleRCSClient, RCSApiError, RCSConfigurationError


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
client = GoogleRCSClient(settings)
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "rcs_region": settings.rcs_api_region,
        "agent_configured": bool(settings.rcs_agent_id.strip()),
        "credentials_configured": bool(
            settings.google_service_account_file.strip()
            or settings.google_service_account_json.strip()
        ),
    }


def send_one(payload: RichCardRequest) -> SendResult:
    try:
        message_id, response = client.send_rich_card(
            phone=payload.phone,
            title=payload.title,
            description=payload.description,
            image_url=str(payload.image_url),
            button_text=payload.button_text,
            button_url=str(payload.button_url),
            postback_data=payload.postback_data,
            traffic_type=payload.traffic_type.value,
        )
        return SendResult(
            phone=payload.phone,
            success=True,
            message_id=message_id,
            status_code=200,
            response=response,
        )
    except RCSApiError as exc:
        return SendResult(
            phone=payload.phone,
            success=False,
            status_code=exc.status_code,
            error=str(exc),
            response=exc.body,
        )
    except RCSConfigurationError as exc:
        return SendResult(phone=payload.phone, success=False, error=str(exc))
    except Exception as exc:  # proteção do lote: um número não interrompe os demais
        return SendResult(phone=payload.phone, success=False, error=f"Erro inesperado: {exc}")


@app.get("/api/v1/rcs/capabilities/{phone:path}")
def capabilities(phone: str):
    phone = phone.strip()
    if not phone.startswith("+"):
        raise HTTPException(status_code=422, detail="Use o telefone em E.164, ex.: +5518999999999")
    try:
        return client.get_capabilities(phone)
    except RCSConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RCSApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": str(exc), "body": exc.body}) from exc


@app.post("/api/v1/rcs/send", response_model=SendResult)
def send_rich_card(payload: RichCardRequest):
    result = send_one(payload)
    if not result.success and result.status_code:
        raise HTTPException(status_code=result.status_code, detail=result.model_dump())
    if not result.success:
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result


@app.post("/api/v1/rcs/broadcast", response_model=BroadcastResult)
def broadcast(payload: BroadcastRequest):
    if len(payload.phones) > settings.max_broadcast_recipients:
        raise HTTPException(
            status_code=422,
            detail=f"Máximo de {settings.max_broadcast_recipients} destinatários por lote neste MVP",
        )

    results: list[SendResult] = []
    for phone in payload.phones:
        item = RichCardRequest(
            phone=phone,
            title=payload.title,
            description=payload.description,
            image_url=payload.image_url,
            button_text=payload.button_text,
            button_url=payload.button_url,
            postback_data=payload.postback_data,
            traffic_type=payload.traffic_type,
        )
        results.append(send_one(item))

    sent = sum(1 for result in results if result.success)
    return BroadcastResult(
        total=len(results),
        sent=sent,
        failed=len(results) - sent,
        results=results,
    )


@app.post("/api/v1/rcs/webhook")
async def webhook(request: Request):
    # Endpoint inicial para receber mensagens, eventos de entrega/leitura e postbacks.
    # A validação/decodificação específica do webhook será ligada ao agente real.
    try:
        payload = await request.json()
    except Exception:
        payload = {"raw": (await request.body()).decode("utf-8", errors="replace")}
    return {"received": True, "payload": payload}
