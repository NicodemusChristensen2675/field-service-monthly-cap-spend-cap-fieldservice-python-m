import json

from field_cap_service.infrai_client import InfraiClient, InfraiError


class FakeResponse:
    def __init__(self, status_code: int, payload: dict, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers=None, json=None, params=None, timeout=None):
        self.calls.append({
            "method": method,
            "url": url,
            "headers": headers,
            "json": json,
            "params": params,
            "timeout": timeout,
        })
        return self.responses.pop(0)


def test_budget_set_uses_put_and_expected_fields() -> None:
    session = FakeSession([
        FakeResponse(200, {"ok": True, "data": {"hard_cap_usd": 25.0, "period": "monthly"}, "error": None, "metadata": {}})
    ])
    client = InfraiClient(api_key="test-key", session=session)

    result = client.account_budget_set(hard_cap_usd=25.0, period="monthly")

    assert result["hard_cap_usd"] == 25.0
    assert session.calls[0]["method"] == "PUT"
    assert session.calls[0]["url"].endswith("/v1/account/budget/set")
    assert session.calls[0]["json"] == {"hard_cap_usd": 25.0, "period": "monthly"}


def test_cost_estimate_uses_messages_field() -> None:
    session = FakeSession([
        FakeResponse(200, {"ok": True, "data": {"estimated_cost_usd": 0.01}, "error": None, "metadata": {}})
    ])
    client = InfraiClient(api_key="test-key", session=session)
    messages = [{"role": "user", "content": "Summarize this work order."}]

    client.ai_cost_estimate(model="auto", messages=messages)

    assert session.calls[0]["json"] == {"messages": messages, "model": "auto"}


def test_envelope_error_is_raised_before_status_handling() -> None:
    session = FakeSession([
        FakeResponse(400, {"ok": False, "data": None, "error": {"code": "INVALID_ARGUMENT"}, "metadata": {}})
    ])
    client = InfraiClient(api_key="test-key", session=session)

    try:
        client.account_budget_get()
    except InfraiError as exc:
        assert exc.code == "INVALID_ARGUMENT"
        assert exc.status_code == 400
    else:
        raise AssertionError("Expected InfraiError")
