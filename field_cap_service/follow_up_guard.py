from __future__ import annotations

from typing import Protocol

from .models import BudgetSnapshot, FieldWorkOrder, FollowUpDecision


class CostEstimator(Protocol):
    def estimate_follow_up_cost(self, work_order: FieldWorkOrder) -> float:
        ...


class FollowUpWriter(Protocol):
    def draft_follow_up(self, work_order: FieldWorkOrder) -> str:
        ...


class BudgetPolicy:
    def evaluate(
        self,
        work_order: FieldWorkOrder,
        budget: BudgetSnapshot,
        estimated_ai_cost_usd: float,
    ) -> FollowUpDecision:
        if work_order.dispatch_status != "dispatched" or not work_order.technician_follow_up_required:
            return FollowUpDecision(
                decision="no_action",
                work_order_id=work_order.work_order_id,
                reason="follow_up_not_required",
                estimated_ai_cost_usd=estimated_ai_cost_usd,
                budget_hard_cap_usd=budget.hard_cap_usd,
                next_action="none",
            )

        projected_total = work_order.monthly_spend_usd + estimated_ai_cost_usd
        if projected_total > budget.hard_cap_usd:
            return FollowUpDecision(
                decision="paused_for_budget",
                work_order_id=work_order.work_order_id,
                reason="monthly_cap_reached",
                estimated_ai_cost_usd=estimated_ai_cost_usd,
                budget_hard_cap_usd=budget.hard_cap_usd,
                next_action="hold_work_order",
            )

        return FollowUpDecision(
            decision="approved",
            work_order_id=work_order.work_order_id,
            reason="within_budget",
            estimated_ai_cost_usd=estimated_ai_cost_usd,
            budget_hard_cap_usd=budget.hard_cap_usd,
            next_action="send_follow_up",
        )


class FollowUpGuardService:
    def __init__(self, estimator: CostEstimator, writer: FollowUpWriter, policy: BudgetPolicy | None = None):
        self.estimator = estimator
        self.writer = writer
        self.policy = policy or BudgetPolicy()

    def review(self, work_order: FieldWorkOrder, budget: BudgetSnapshot) -> FollowUpDecision:
        estimated_cost = self.estimator.estimate_follow_up_cost(work_order)
        decision = self.policy.evaluate(work_order, budget, estimated_cost)
        if decision.decision == "approved":
            decision.follow_up_message = self.writer.draft_follow_up(work_order)
        return decision
