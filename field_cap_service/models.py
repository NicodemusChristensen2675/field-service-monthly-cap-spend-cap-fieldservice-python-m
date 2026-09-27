from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


DispatchStatus = Literal["queued", "dispatched", "completed"]
Decision = Literal["approved", "paused_for_budget", "no_action"]
NextAction = Literal["send_follow_up", "hold_work_order", "none"]


class WorkOrderPhoto(BaseModel):
    photo_id: str = Field(min_length=1)
    note: str = Field(min_length=1)


class FieldWorkOrder(BaseModel):
    work_order_id: str = Field(min_length=1)
    dispatch_status: DispatchStatus
    technician_follow_up_required: bool
    monthly_spend_usd: float = Field(ge=0)
    photos: List[WorkOrderPhoto] = Field(min_length=1)


class BudgetSnapshot(BaseModel):
    hard_cap_usd: float = Field(gt=0)
    period: str
    alert_threshold_usd: Optional[float] = Field(default=None, ge=0)


class FollowUpDecision(BaseModel):
    decision: Decision
    work_order_id: str
    reason: str
    estimated_ai_cost_usd: float = Field(ge=0)
    budget_hard_cap_usd: float = Field(gt=0)
    follow_up_message: Optional[str] = None
    next_action: NextAction
