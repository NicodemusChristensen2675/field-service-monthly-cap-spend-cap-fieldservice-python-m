from field_cap_service.follow_up_guard import BudgetPolicy, FollowUpGuardService
from field_cap_service.models import BudgetSnapshot, FieldWorkOrder, WorkOrderPhoto


class FixedEstimator:
    def __init__(self, value: float):
        self.value = value

    def estimate_follow_up_cost(self, work_order: FieldWorkOrder) -> float:
        return self.value


class FixedWriter:
    def draft_follow_up(self, work_order: FieldWorkOrder) -> str:
        return "Follow up with technician on next visit window."


def make_work_order(monthly_spend_usd: float) -> FieldWorkOrder:
    return FieldWorkOrder(
        work_order_id="wo-2048",
        dispatch_status="dispatched",
        technician_follow_up_required=True,
        monthly_spend_usd=monthly_spend_usd,
        photos=[WorkOrderPhoto(photo_id="ph-1", note="Boiler panel intact")],
    )


def test_pauses_work_order_when_projected_monthly_spend_crosses_cap() -> None:
    service = FollowUpGuardService(FixedEstimator(0.30), FixedWriter(), BudgetPolicy())
    budget = BudgetSnapshot(hard_cap_usd=20.00, period="monthly")

    result = service.review(make_work_order(19.80), budget)

    assert result.decision == "paused_for_budget"
    assert result.next_action == "hold_work_order"
    assert result.follow_up_message is None


def test_generates_follow_up_when_projected_monthly_spend_stays_within_cap() -> None:
    service = FollowUpGuardService(FixedEstimator(0.12), FixedWriter(), BudgetPolicy())
    budget = BudgetSnapshot(hard_cap_usd=20.00, period="monthly")

    result = service.review(make_work_order(4.20), budget)

    assert result.decision == "approved"
    assert result.next_action == "send_follow_up"
    assert result.follow_up_message == "Follow up with technician on next visit window."
