import os; from datetime import datetime, timezone; import pytest; from dotenv import load_dotenv; from app.services.database import (create_post,create_variant,get_publish_history_by_key,get_variant,); from app.services.publisher import publish_variant; from app.services.schedule import schedule_variant;

load_dotenv()

@pytest.mark.integration
def test_real_discord_publish_is_idempotent():
    """
    Gate E integration test.

    ```
    Verifies that:
    1. An approved Discord variant can be scheduled.
    2. The first publish creates a real Discord message.
    3. A repeated publish call does not create another message.
    4. Only one successful publish-history record exists.
    """

    if not os.getenv("DISCORD_WEBHOOK_URL"):
        pytest.fail(
            "DISCORD_WEBHOOK_URL is not configured. "
            "Add it to your .env file before running this test."
        )

    # Create a dedicated test post.
    post_id = create_post(
        source_url=None,
        source_type="markdown",
        content=(
            "Phase 4 Gate E integration test. "
            "This message verifies real Discord publishing "
            "and idempotency in the Social Media Studio."
        ),
    )

    # Create the Discord variant as a draft.
    variant_id = create_variant(
        post_id=post_id,
        platform="discord",
        content=(
            "Hello from Social Media Studio — "
            "this is the Phase 4 Gate E Discord integration test."
        ),
        status="draft",
    )

    variant = get_variant(variant_id)

    assert variant is not None
    assert variant["status"] == "draft"

    # Approval is intentional here because this test is exercising
    # the real publish path after the approval gate.
    from app.services.database import get_connection

    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE variants
            SET status = 'approved'
            WHERE id = ?
            """,
            (variant_id,),
        )
        connection.commit()
    finally:
        connection.close()

    variant = get_variant(variant_id)

    assert variant["status"] == "approved"

    # Use a deterministic UTC timestamp for the schedule.
    scheduled_at = datetime.now(timezone.utc)

    schedule_id = schedule_variant(
        variant_id=variant_id,
        scheduled_at=scheduled_at,
    )

    assert schedule_id is not None

    # First publish: this should create ONE real Discord message.
    first_result = publish_variant(variant_id)

    assert first_result["status"] == "published"
    assert first_result["platform"] == "discord"
    assert first_result["variant_id"] == variant_id

    idempotency_key = first_result["idempotency_key"]

    # Second publish: must not send another Discord message.
    second_result = publish_variant(variant_id)

    assert second_result["status"] == "already_published"
    assert second_result["variant_id"] == variant_id
    assert second_result["idempotency_key"] == idempotency_key

    # Exactly one successful publish record should exist for this key.
    history = get_publish_history_by_key(idempotency_key)

    assert history is not None
    assert history["variant_id"] == variant_id
    assert history["platform"] == "discord"
    assert history["result"] == "success"
    assert history["idempotency_key"] == idempotency_key
