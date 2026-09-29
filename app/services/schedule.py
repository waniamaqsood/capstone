from datetime import datetime; from app.services.database import (create_schedule, get_variant,)

class SchedulingError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def build_idempotency_key(variant_id: int, scheduled_at: datetime,) -> str:
    normalized_time = scheduled_at.isoformat()

    return (
        f"variant-{variant_id}:"
        f"slot-{normalized_time}"
    )


def schedule_variant(variant_id: int, scheduled_at: datetime,):
    variant = get_variant(variant_id)

    if variant is None:
        raise SchedulingError(
            f"Variant {variant_id} does not exist."
        )

    if variant["status"] != "approved":
        raise SchedulingError(
            f"Variant {variant_id} cannot be scheduled. "
            f"Current status is '{variant['status']}'. "
            f"Only approved variants can be scheduled."
        )

    idempotency_key = build_idempotency_key(
        variant_id=variant_id,
        scheduled_at=scheduled_at,
    )

    try:
        schedule_id = create_schedule(
            variant_id=variant_id,
            platform=variant["platform"],
            scheduled_at=scheduled_at,
            idempotency_key=idempotency_key,
        )

    except Exception as error:
        raise SchedulingError(
            f"Could not create schedule: {error}"
        ) from error

    return schedule_id