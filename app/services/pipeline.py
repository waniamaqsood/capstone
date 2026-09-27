from app.services.database import (
    create_post,
    create_variant,
    init_db,
)

from app.services.generator import (
    clean_content,
    generate_variants,
)


def process_post(
    content: str,
    source_type: str,
    source_url: str | None = None,
):
    """
    Clean, store, generate, validate, and store variants.
    """

    # 1. Initialize database
    init_db()

    # 2. Clean source content
    cleaned_content = clean_content(content)

    # 3. Store original post
    post_id = create_post(
        content=cleaned_content,
        source_type=source_type,
        source_url=source_url,
    )

    # 4. Generate and validate variants
    variants = generate_variants(cleaned_content)

    # 5. Store variants
    stored_variants = []

    for variant in variants:
        variant_id = create_variant(
            post_id=post_id,
            platform=variant.platform,
            content=variant.content,
            status=variant.status,
        )

        stored_variants.append(
            {
                "id": variant_id,
                "platform": variant.platform,
                "content": variant.content,
                "status": variant.status,
            }
        )

    return {
        "post_id": post_id,
        "variants": stored_variants,
    }


if __name__ == "__main__":

    sample_post = """
    Artificial intelligence is changing the way businesses
    build software. Modern development teams can use AI to
    automate repetitive tasks, improve productivity, and
    create new types of applications.
    """

    result = process_post(
        content=sample_post,
        source_type="markdown",
    )

    print(result)