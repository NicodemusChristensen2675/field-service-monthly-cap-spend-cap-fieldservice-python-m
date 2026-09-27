from __future__ import annotations

import argparse
import json
from typing import Any

from .follow_up_guard import FollowUpGuardService
from .infrai_client import InfraiClient
from .models import BudgetSnapshot, FieldWorkOrder


class InfraiCostEstimator:
    def __init__(self, infrai: InfraiClient):
        self.infrai = infrai

    def estimate_follow_up_cost(self, work_order: FieldWorkOrder) -> float:
        prompt = build_summary_prompt(work_order)
        data = self.infrai.ai_cost_estimate(
            model="auto",
            messages=[{"role": "user", "content": prompt}],
        )
        if isinstance(data, dict):
            for key in ("estimated_cost_usd", "cost_usd", "usd"):
                value = data.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
        raise ValueError("Cost estimate response did not include a numeric USD amount")


class InfraiFollowUpWriter:
    def __init__(self, infrai: InfraiClient):
        self.client = infrai.openai_client()

    def draft_follow_up(self, work_order: FieldWorkOrder) -> str:
        prompt = build_summary_prompt(work_order)
        completion = self.client.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": "Write a brief field-service follow-up. Keep it operational. Avoid personal detail.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content or ""


def build_summary_prompt(work_order: FieldWorkOrder) -> str:
    photo_lines = "\n".join(f"- {photo.note}" for photo in work_order.photos)
    return (
        f"Work order {work_order.work_order_id}\n"
        f"Dispatch status: {work_order.dispatch_status}\n"
        f"Technician follow-up required: {work_order.technician_follow_up_required}\n"
        f"Photo notes:\n{photo_lines}\n"
        "Draft a short follow-up for the technician. Keep it to service status and next step."
    )


def load_budget(infrai: InfraiClient) -> BudgetSnapshot:
    data = infrai.account_budget_get()
    return BudgetSnapshot.model_validate(data)


def current_usage_usd(infrai: InfraiClient) -> float:
    data = infrai.account_usage()
    if isinstance(data, dict):
        for key in ("usd", "total_usd", "usage_usd"):
            value = data.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    raise ValueError("Usage response did not include a numeric USD amount")


def run_review(raw: dict[str, Any], infrai: InfraiClient) -> dict[str, Any]:
    work_order = FieldWorkOrder.model_validate(raw)
    budget = load_budget(infrai)
    if work_order.monthly_spend_usd == 0:
        work_order.monthly_spend_usd = current_usage_usd(infrai)
    service = FollowUpGuardService(InfraiCostEstimator(infrai), InfraiFollowUpWriter(infrai))
    return service.review(work_order, budget).model_dump()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pause field-service AI follow-up when the monthly cap would be crossed.")
    parser.add_argument("--set-budget", type=float, help="Set the account monthly hard cap in USD and exit.")
    args = parser.parse_args()

    infrai = InfraiClient()

    if args.set_budget is not None:
        result = infrai.account_budget_set(hard_cap_usd=args.set_budget, period="monthly")
        print(json.dumps(result, indent=2))
        return

    raw = json.load(fp=__import__("sys").stdin)
    print(json.dumps(run_review(raw, infrai), indent=2))


if __name__ == "__main__":
    main()
