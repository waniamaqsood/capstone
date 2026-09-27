from dataclasses import dataclass; import re

@dataclass(frozen=True)
class ConstraintProfile:
    min_chars: int | None = None
    max_chars: int | None = None
    max_hashtags: int | None = None

@dataclass
class GeneratedVariant:
    platform: str
    content: str
    status: str = "draft"

CONSTRAINT_PROFILES = {
    "linkedin": ConstraintProfile(
        min_chars=150,
        max_chars=3000,
        max_hashtags=5,
    ),
    "instagram": ConstraintProfile(
        max_chars=2200,
        max_hashtags=10,
    ),
}

def clean_content(content: str) -> str:
    if not isinstance(content, str):
        raise TypeError("Post content must be a string.")

    content = content.strip()

    if not content:
        raise ValueError("Post content cannot be empty.")

    content = re.sub(r"^#{1,6}\s*", "", content, flags=re.MULTILINE,)
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content,)
    content = re.sub(r"[*_`]", "", content,)
    content = re.sub(r"[ \t]+", " ", content,)
    content = re.sub(r"\n\s*\n+", "\n\n", content,)
    content = re.sub(r"[ \t]*\n[ \t]*", "\n", content,)
    return content.strip()


def normalize_line_breaks(content: str) -> str:
    content = re.sub(r"[ \t]+\n", "\n", content,)
    content = re.sub(r"\n{3,}", "\n\n", content,)
    return content.strip()

def extract_first_sentence(content: str) -> tuple[str, str]:
    match = re.search(r"^(.+?[.!?])(?:\s+|$)", content, flags=re.DOTALL,)

    if match:
        first_sentence = match.group(1).strip()
        remaining_body = content[match.end():].strip()

        return first_sentence, remaining_body
    return content.strip(), ""

def create_linkedin_variant(hook: str, body: str,) -> str:
    sections = [
        f"One important takeaway: {hook}",
    ]

    if body:
        sections.append(body)

    sections.append(
        "The key takeaway is that practical implementation "
        "matters as much as the idea itself."
    )

    sections.append(
        "#Technology #Innovation"
    )

    return "\n\n".join(sections)


def create_instagram_variant(hook: str, body: str,) -> str:
    sections = [
        "Here's something worth knowing 👇",
        hook,
    ]

    if body:
        sections.append(body)

    sections.append(
        "What do you think? Share your thoughts below."
    )

    sections.append(
        "#Technology #Innovation #AI"
    )

    return "\n\n".join(sections)

def count_hashtags(content: str) -> int:
    return len(
        re.findall(
            r"(?<!\w)#\w+",
            content,
        )
    )

def validate_variant(platform: str, content: str,) -> tuple[bool, list[str]]:
    if platform not in CONSTRAINT_PROFILES:
        raise ValueError(
            f"Unsupported platform: {platform}. "
            f"Supported platforms: "
            f"{', '.join(CONSTRAINT_PROFILES)}"
        )

    profile = CONSTRAINT_PROFILES[platform]

    errors = []

    character_count = len(content)
    hashtag_count = count_hashtags(content)

    if (
        profile.min_chars is not None
        and character_count < profile.min_chars
    ):
        errors.append(
            f"{platform.capitalize()} requires at least "
            f"{profile.min_chars} characters; "
            f"received {character_count}."
        )

    if (
        profile.max_chars is not None
        and character_count > profile.max_chars
    ):
        errors.append(
            f"{platform.capitalize()} allows a maximum of "
            f"{profile.max_chars} characters; "
            f"received {character_count}."
        )

    if (
        profile.max_hashtags is not None
        and hashtag_count > profile.max_hashtags
    ):
        errors.append(
            f"{platform.capitalize()} allows a maximum of "
            f"{profile.max_hashtags} hashtags; "
            f"received {hashtag_count}."
        )

    return len(errors) == 0, errors

def generate_variant(content: str, platform: str,) -> GeneratedVariant:
    if platform not in CONSTRAINT_PROFILES:
        raise ValueError(
            f"Unsupported platform: {platform}. "
            f"Supported platforms: "
            f"{', '.join(CONSTRAINT_PROFILES)}"
        )

    cleaned_content = clean_content(content)
    hook, body = extract_first_sentence(
        cleaned_content
    )
    if platform == "linkedin":
        generated_content = create_linkedin_variant(
            hook,
            body,
        )

    elif platform == "instagram":
        generated_content = create_instagram_variant(
            hook,
            body,
        )

    else:
        raise ValueError(
            f"Unsupported platform: {platform}"
        )

    generated_content = normalize_line_breaks(
        generated_content
    )

    is_valid, errors = validate_variant(
        platform,
        generated_content,
    )

    if not is_valid:
        raise ValueError(
            f"Validation failed for {platform} variant:\n- "
            + "\n- ".join(errors)
        )

    return GeneratedVariant(
        platform=platform,
        content=generated_content,
        status="draft",
    )

def generate_variants(content: str,) -> list[GeneratedVariant]:
    platforms = (
        "linkedin",
        "instagram",
    )

    variants = []

    for platform in platforms:
        variant = generate_variant(
            content,
            platform,
        )

        variants.append(variant)

    return variants

# Example usage

if __name__ == "__main__":

    sample_post = """
    Artificial intelligence is changing the way businesses
    build software. Modern development teams can use AI to
    automate repetitive tasks, improve productivity, and
    create new types of applications.
    """

    try:
        variants = generate_variants(sample_post)

        for variant in variants:
            print("=" * 60)
            print(f"Platform: {variant.platform}")
            print(f"Status: {variant.status}")
            print("-" * 60)
            print(variant.content)
            print()

    except (ValueError, TypeError) as error:
        print(f"Error: {error}")