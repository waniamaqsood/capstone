import pytest; from datetime import datetime, timezone; from pathlib import Path; from app.services.database import (create_post, create_variant, get_connection, get_publish_history_by_key, get_variant,); from app.services.generator import generate_variants; from app.services.publisher import PublishingError, publish_variant; from app.services.schedule import schedule_variant


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "content_repurposer.db"


def unique_test_content() -> str:
    return (
        "Python is a versatile programming language used for web development, "
        "automation, data analysis, and artificial intelligence. "
        "Learning Python also provides a strong foundation for building "
        "backend applications and working with modern AI systems."
    )


def create_test_post() -> int:
    return create_post(
        content=unique_test_content(),
        source_type="markdown",
        source_url=None,
    )


def get_successful_history_count(idempotency_key: str) -> int:
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM publish_history
            WHERE idempotency_key = ?
              AND result = 'success'
            """,
            (idempotency_key,),
        )
        return cursor.fetchone()[0]
    finally:
        connection.close()


def test_ollama_generates_valid_variants():
    variants = generate_variants(unique_test_content())

    assert len(variants) == 2

    platforms = {variant.platform for variant in variants}

    assert platforms == {"linkedin", "instagram"}

    for variant in variants:
        assert variant.valid is True
        assert variant.status == "draft"
        assert variant.content.strip() != ""
        assert variant.errors == []

    linkedin = next(
        variant
        for variant in variants
        if variant.platform == "linkedin"
    )

    instagram = next(
        variant
        for variant in variants
        if variant.platform == "instagram"
    )

    assert 150 <= len(linkedin.content) <= 3000
    assert len(instagram.content) <= 2200


def test_unapproved_variant_cannot_be_scheduled():
    post_id = create_test_post()

    variant_id = create_variant(
        post_id=post_id,
        platform="linkedin",
        content=(
            "This is a test LinkedIn post that is intentionally "
            "left unapproved so scheduling should fail."
        ),
    )

    scheduled_at = datetime.now(timezone.utc)

    with pytest.raises(Exception) as error:
        schedule_variant(
            variant_id=variant_id,
            scheduled_at=scheduled_at,
        )

    assert "Only approved variants can be scheduled" in str(error.value)


def test_approved_variant_can_be_scheduled():
    post_id = create_test_post()

    variant_id = create_variant(
        post_id=post_id,
        platform="linkedin",
        content=(
            "This is an approved LinkedIn test post for verifying "
            "the scheduling workflow."
        ),
    )

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

    scheduled_at = datetime.now(timezone.utc)

    schedule_id = schedule_variant(
        variant_id=variant_id,
        scheduled_at=scheduled_at,
    )

    assert schedule_id is not None


def test_unapproved_variant_cannot_be_published():
    post_id = create_test_post()

    variant_id = create_variant(
        post_id=post_id,
        platform="linkedin",
        content=(
            "This variant has not been approved and therefore "
            "must not be published."
        ),
    )

    with pytest.raises(PublishingError) as error:
        publish_variant(variant_id)

    assert "Only approved variants can be published" in str(error.value)


def test_first_publish_and_repeated_publish_are_idempotent():
    post_id = create_test_post()

    variant_id = create_variant(
        post_id=post_id,
        platform="linkedin",
        content=(
            "Python is a versatile programming language used for "
            "web development, automation, data analysis, and AI."
        ),
    )

    # Approve the variant.
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

    assert variant is not None
    assert variant["status"] == "approved"

    # Schedule the variant.
    scheduled_at = datetime.now(timezone.utc)

    schedule_id = schedule_variant(
        variant_id=variant_id,
        scheduled_at=scheduled_at,
    )

    assert schedule_id is not None

    # First publish.
    first_result = publish_variant(variant_id)

    assert first_result["variant_id"] == variant_id
    assert first_result["platform"] == "linkedin"
    assert first_result["status"] == "published"
    assert first_result["idempotency_key"]

    idempotency_key = first_result["idempotency_key"]

    # Verify successful publish was recorded.
    history = get_publish_history_by_key(idempotency_key)

    assert history is not None
    assert history["variant_id"] == variant_id
    assert history["platform"] == "linkedin"
    assert history["idempotency_key"] == idempotency_key
    assert history["result"] == "success"

    assert get_successful_history_count(idempotency_key) == 1

    # Second publish.
    second_result = publish_variant(variant_id)

    assert second_result["variant_id"] == variant_id
    assert second_result["platform"] == "linkedin"
    assert second_result["status"] == "already_published"
    assert second_result["idempotency_key"] == idempotency_key

    # Confirm no duplicate history record exists.
    assert get_successful_history_count(idempotency_key) == 1


def test_idempotency_key_is_unique_in_schedules():
    post_id = create_test_post()

    variant_id = create_variant(
        post_id=post_id,
        platform="linkedin",
        content="Testing database-level idempotency key uniqueness.",
    )

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

    scheduled_at = datetime.now(timezone.utc)

    schedule_variant(
        variant_id=variant_id,
        scheduled_at=scheduled_at,
    )

    # The same variant + same slot generates the same key.
    with pytest.raises(Exception):
        schedule_variant(
            variant_id=variant_id,
            scheduled_at=scheduled_at,
        )


def test_ollama_variants_can_be_stored_in_database():
    post_id = create_test_post()

    generated_variants = generate_variants(unique_test_content())

    assert len(generated_variants) == 2

    stored_variant_ids = []

    for generated in generated_variants:
        assert generated.valid is True

        variant_id = create_variant(
            post_id=post_id,
            platform=generated.platform,
            content=generated.content,
        )

        stored_variant_ids.append(variant_id)

    assert len(stored_variant_ids) == 2

    for variant_id in stored_variant_ids:
        variant = get_variant(variant_id)

        assert variant is not None
        assert variant["status"] == "draft"
        assert variant["content"].strip() != ""