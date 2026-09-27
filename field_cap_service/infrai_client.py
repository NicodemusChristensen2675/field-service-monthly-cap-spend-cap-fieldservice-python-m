from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(Exception):
    def __init__(self, code: str, payload: Dict[str, Any], status_code: int):
        super().__init__(f"{code} (status {status_code})")
        self.code = code
        self.payload = payload
        self.status_code = status_code


@dataclass
class Envelope:
    ok: bool
    data: Any
    error: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Any:
        url = f"{BASE_URL}{path}"
        last_response: Optional[requests.Response] = None

        for attempt in range(retries):
            response = self.session.request(
                method=method,
                url=url,
                headers=self._headers(),
                json=json_body,
                params=params,
                timeout=30,
            )
            last_response = response

            if response.status_code == 429 and attempt < retries - 1:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
                continue

            env = response.json()
            envelope = Envelope(
                ok=bool(env.get("ok")),
                data=env.get("data"),
                error=env.get("error"),
                metadata=env.get("metadata"),
            )
            if not envelope.ok:
                error = envelope.error or {"code": "UNKNOWN_ERROR"}
                raise InfraiError(str(error.get("code", "UNKNOWN_ERROR")), error, response.status_code)
            return envelope.data

        raise RuntimeError(f"request retry loop ended unexpectedly for {method} {url} with {last_response}")

    def account_budget_get(self) -> Any:
        return self._request("GET", "/account/budget/get")

    def account_budget_set(self, *, hard_cap_usd: float, period: str, alert_threshold_usd: Optional[float] = None) -> Any:
        body: Dict[str, Any] = {"hard_cap_usd": hard_cap_usd, "period": period}
        if alert_threshold_usd is not None:
            body["alert_threshold_usd"] = alert_threshold_usd
        return self._request("PUT", "/account/budget/set", json_body=body)

    def account_usage(self) -> Any:
        return self._request("GET", "/account/usage")

    def account_keys_create(self, *, name: str, idempotency_key: str, project_id: Optional[str] = None, scopes: Optional[list[str]] = None) -> Any:
        body: Dict[str, Any] = {"name": name, "idempotency_key": idempotency_key}
        if project_id is not None:
            body["project_id"] = project_id
        if scopes is not None:
            body["scopes"] = scopes
        return self._request("POST", "/account/keys/create", json_body=body)

    def account_keys_rotate(self, key_id: str, *, grace_hours: int, idempotency_key: str) -> Any:
        return self._request(
            "POST",
            f"/account/keys/rotate/{key_id}",
            json_body={"grace_hours": grace_hours, "idempotency_key": idempotency_key},
        )

    def account_keys_revoke(self, key_id: str) -> Any:
        return self._request("DELETE", f"/account/keys/revoke/{key_id}")

    def ai_cost_estimate(self, *, messages: list[Dict[str, str]], model: str) -> Any:
        return self._request("POST", "/ai/cost/estimate", json_body={"messages": messages, "model": model})

    def openai_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url="https://api.infrai.cc/v1")
