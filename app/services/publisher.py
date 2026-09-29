from app.services.adapters.base import (
    PublishResult,
    SocialPublisher,
)

from app.services.adapters.discord import (
    DiscordPublisher,
)

from app.services.adapters.mock_linkedin import (
    MockLinkedInPublisher,
)

from app.services.adapters.mock_x import (
    MockXPublisher,
)

from app.services.database import (
    create_publish_history,
    get_publish_history_by_key,
    get_schedule_by_variant,
    get_variant,
)


class PublishingError(Exception):
    """
    Error raised when a variant cannot be published.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def get_publishers() -> dict[str, SocialPublisher]:
    """
    Return the available platform adapters.
    """

    return {
        "discord": DiscordPublisher(),
        "x": MockXPublisher(),
        "linkedin": MockLinkedInPublisher(),
    }


def publish_variant(
    variant_id: int,
) -> dict:
    """
    Publish an approved, scheduled variant.

    Publishing is idempotent using the schedule's
    idempotency key.
    """

    variant = get_variant(variant_id)

    if variant is None:
        raise PublishingError(
            f"Variant {variant_id} does not exist."
        )

    if variant["status"] != "approved":
        raise PublishingError(
            f"Variant {variant_id} cannot be published. "
            f"Current status is '{variant['status']}'. "
            "Only approved variants can be published."
        )

    schedule = get_schedule_by_variant(
        variant_id
    )

    if schedule is None:
        raise PublishingError(
            f"Variant {variant_id} has no schedule."
        )

    idempotency_key = schedule["idempotency_key"]

    previous_publish = get_publish_history_by_key(
        idempotency_key
    )

    if previous_publish is not None:
        return {
            "variant_id": variant_id,
            "platform": variant["platform"],
            "status": "already_published",
            "idempotency_key": idempotency_key,
        }

    publishers = get_publishers()

    platform = variant["platform"]

    publisher = publishers.get(platform)

    if publisher is None:
        raise PublishingError(
            f"No publisher is configured for "
            f"platform '{platform}'."
        )

    result: PublishResult = publisher.publish(
        variant["content"]
    )

    if not result.success:
        create_publish_history(
            variant_id=variant_id,
            platform=platform,
            idempotency_key=idempotency_key,
            result="failed",
            error_message=result.error_message,
        )

        raise PublishingError(
            f"Publishing to {platform} failed: "
            f"{result.error_message}"
        )

    create_publish_history(
        variant_id=variant_id,
        platform=platform,
        idempotency_key=idempotency_key,
        result="success",
    )

    return {
        "variant_id": variant_id,
        "platform": platform,
        "status": "published",
        "idempotency_key": idempotency_key,
        "message_id": result.message_id,
    }