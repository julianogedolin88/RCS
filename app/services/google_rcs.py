import json
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from app.config import Settings


SCOPES = ["https://www.googleapis.com/auth/rcsbusinessmessaging"]


class RCSConfigurationError(RuntimeError):
    pass


class RCSApiError(RuntimeError):
    def __init__(self, status_code: int, message: str, body: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body or {}


class GoogleRCSClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._session: AuthorizedSession | None = None

    def _credentials(self):
        if self.settings.google_service_account_json.strip():
            try:
                info = json.loads(self.settings.google_service_account_json)
            except json.JSONDecodeError as exc:
                raise RCSConfigurationError("GOOGLE_SERVICE_ACCOUNT_JSON não contém JSON válido") from exc
            return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

        if self.settings.google_service_account_file.strip():
            path = Path(self.settings.google_service_account_file)
            if not path.exists():
                raise RCSConfigurationError(
                    f"Arquivo da Service Account não encontrado: {path}"
                )
            return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)

        raise RCSConfigurationError(
            "Configure GOOGLE_SERVICE_ACCOUNT_FILE ou GOOGLE_SERVICE_ACCOUNT_JSON"
        )

    @property
    def session(self) -> AuthorizedSession:
        if self._session is None:
            self._session = AuthorizedSession(self._credentials())
        return self._session

    def _agent_id(self) -> str:
        agent_id = self.settings.rcs_agent_id.strip()
        if not agent_id:
            raise RCSConfigurationError("RCS_AGENT_ID não configurado")
        return agent_id

    def get_capabilities(self, phone: str) -> dict[str, Any]:
        encoded_phone = quote(phone, safe="+")
        url = f"{self.settings.rcs_base_url}/v1/phones/{encoded_phone}/capabilities"
        response = self.session.get(
            url,
            params={"agentId": self._agent_id()},
            timeout=self.settings.request_timeout_seconds,
        )
        return self._handle_response(response)

    def send_rich_card(
        self,
        *,
        phone: str,
        title: str,
        description: str,
        image_url: str,
        button_text: str,
        button_url: str,
        postback_data: str,
        traffic_type: str,
    ) -> tuple[str, dict[str, Any]]:
        message_id = str(uuid4())
        encoded_phone = quote(phone, safe="+")
        url = f"{self.settings.rcs_base_url}/v1/phones/{encoded_phone}/agentMessages"

        payload = {
            "contentMessage": {
                "richCard": {
                    "standaloneCard": {
                        "cardOrientation": "VERTICAL",
                        "cardContent": {
                            "title": title,
                            "description": description,
                            "media": {
                                "height": "MEDIUM",
                                "contentInfo": {
                                    "fileUrl": image_url,
                                    "forceRefresh": False,
                                },
                            },
                            "suggestions": [
                                {
                                    "action": {
                                        "text": button_text,
                                        "postbackData": postback_data,
                                        "openUrlAction": {"url": button_url},
                                    }
                                }
                            ],
                        },
                    }
                }
            },
            "messageTrafficType": traffic_type,
        }

        response = self.session.post(
            url,
            params={"messageId": message_id, "agentId": self._agent_id()},
            json=payload,
            timeout=self.settings.request_timeout_seconds,
        )
        return message_id, self._handle_response(response)

    @staticmethod
    def _handle_response(response) -> dict[str, Any]:
        try:
            body = response.json() if response.content else {}
        except ValueError:
            body = {"raw": response.text}

        if response.status_code >= 400:
            message = body.get("error", {}).get("message") if isinstance(body, dict) else None
            raise RCSApiError(
                response.status_code,
                message or f"Erro HTTP {response.status_code} na API RCS",
                body if isinstance(body, dict) else {},
            )
        return body if isinstance(body, dict) else {"data": body}
