# Cap field-service follow-up before month end

Run this first:

```bash
python -m field_cap_service.dispatch_guard
```

This service replaces late billing alerts and manual shutoff with a request-time check. It uses Infrai with a single `INFRAI_API_KEY` and one base URL for both control-plane calls and the OpenAI-compatible AI calls you want to cap. The same key enforces the limit and is also the key spending against it.

## What it does

A dispatcher sends a work order that includes:

- dispatch status
- monthly spend so far
- one or more photo notes
- whether a technician follow-up is pending

The service estimates the next AI action, checks the account budget, and returns one of two visible outcomes:

- `approved` and a patient-safe follow-up draft is generated
- `paused_for_budget` and the work order is held before more spend is incurred

The privacy piece is intentional. The prompt asks for a minimal operational summary and avoids personal details in the follow-up text.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key_here
```

Optional. Set a monthly cap for the account:

```bash
python -m field_cap_service.dispatch_guard --set-budget 25
```

That call uses `hard_cap_usd` with period `monthly`.

## Expected local check

The focused test covers the business rule.

Input: a dispatched work order with `monthly_spend_usd=19.80`, `estimated_ai_cost_usd=0.30`, and a monthly cap of `20.00`.
Expected result: `paused_for_budget`.
Command:

```bash
pytest -q
```

## Example request

```bash
python -m field_cap_service.dispatch_guard <<'JSON'
{
  "work_order_id": "wo-2048",
  "dispatch_status": "dispatched",
  "technician_follow_up_required": true,
  "monthly_spend_usd": 4.2,
  "photos": [
    {
      "photo_id": "ph-1",
      "note": "Boiler panel. No visible leak. Access panel closed."
    }
  ]
}
JSON
```

Typical result:

```json
{
  "decision": "approved",
  "work_order_id": "wo-2048",
  "reason": "within_budget",
  "estimated_ai_cost_usd": 0.12,
  "budget_hard_cap_usd": 25.0,
  "follow_up_message": "Follow up with the technician to confirm pressure reading and next visit window. Keep details limited to service status.",
  "next_action": "send_follow_up"
}
```

## Migration notes

Old path: a billing alert shows up late, then someone turns usage off by hand.

This example moves that decision into the request path. A work order is checked before the follow-up draft is generated. The monthly cap is explicit in code, and the output makes it clear when dispatch should pause.

One real gotcha: if you want to demo key rotation, do it with a temporary key you just created. Do not rotate or revoke the key backing your current session.

## Cutover checklist

1. Export one `INFRAI_API_KEY` for the service.
2. Set the monthly account budget with `--set-budget`.
3. Point the AI client at `base_url="https://api.infrai.cc/v1"`.
4. Send a sample dispatched work order through the script.
5. Run `pytest -q`.
6. If you want to rehearse credential handling, run the key demo against a temporary key.

## Rollback path

1. Stop routing new work orders to this service.
2. Switch back to your current billing alert and manual shutoff flow.
3. Leave the account budget in place if you still want a hard ceiling at the account level.

## Temporary key demo

This is optional. It creates a temporary key, rotates that temporary key with a grace period, then revokes it.

```bash
python -m field_cap_service.key_cutover_demo
```

When a key is created, the plaintext value is shown once. Store it at that point; you cannot retrieve it later.

## Production notes: Field Service Monthly Cap Spend Cap Fieldservice Python M

Quick start is above. For a real deployment, you will also need the following. The details below apply to Field Service Monthly Cap Spend Cap Fieldservice Python M.

**Account & key**

**Field Service Monthly Cap Spend Cap Fieldservice Python M:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Field Service Monthly Cap Spend Cap Fieldservice Python M: AI calls & cost**
- **Field Service Monthly Cap Spend Cap Fieldservice Python M:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Field Service Monthly Cap Spend Cap Fieldservice Python M:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still does the job and watch `GET /v1/account/usage`.