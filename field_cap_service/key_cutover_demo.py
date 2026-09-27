from __future__ import annotations

import json
import uuid

from .infrai_client import InfraiClient


def main() -> None:
    infrai = InfraiClient()
    created = infrai.account_keys_create(
        name="field-service-cutover-demo",
        scopes=["account.budget.get", "account.usage", "ai.cost.estimate"],
        idempotency_key=str(uuid.uuid4()),
    )
    key_id = created["id"]
    rotated = infrai.account_keys_rotate(
        key_id,
        grace_hours=1,
        idempotency_key=str(uuid.uuid4()),
    )
    revoked = infrai.account_keys_revoke(key_id)
    print(
        json.dumps(
            {
                "created": created,
                "rotated": rotated,
                "revoked": revoked,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
