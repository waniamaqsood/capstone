import json; import re; from dataclasses import dataclass; import requests

@dataclass
class ConstraintProfile:
    platform: str
    min_chars: int
    max_chars: int
    max_hashtags: int


@dataclass
class GeneratedVariant:
    platform: str
    content: str
    status: str
    valid: bool
    errors: list[str]


PROFILES = {
    "linkedin": ConstraintProfile(
        platform="linkedin",
        min_chars=150,
        max_chars=3000,
        max_hashtags=5,
    ),
    "instagram": ConstraintProfile(
        platform="instagram",
        min_chars=1,
        max_chars=2200,
        max_hashtags=10,
    ),
}

OLLAMA_MODEL = "llama3.2:latest"

OLLAMA_URL = "http://localhost:11434/api/generate"

MAX_GENERATION_ATTEMPTS = 3


class OllamaGenerationError(Exception):
    """Raised when Ollama cannot generate valid variants."""

    pass

def clean_markdown(content: str) -> str:
    """Remove basic Markdown formatting."""

    content = re.sub(
        r"^#{1,6}\s*",
        "",
        content,
        flags=re.MULTILINE,
    )

    content = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        content,
    )

    content = re.sub(
        r"[*_`]",
        "",
        content,
    )

    content = re.sub(
        r"\n{3,}",
        "\n\n",
        content,
    )

    return content.strip()


def count_hashtags(content: str) -> int:
    return len(
        re.findall(
            r"#\w+",
            content,
        )
    )

def validate_content(
    content: str,
    profile: ConstraintProfile,
) -> list[str]:

    errors = []

    character_count = len(content)
    hashtag_count = count_hashtags(content)

    if character_count < profile.min_chars:
        errors.append(
            f"{profile.platform} content is too short: "
            f"{character_count} characters. "
            f"Minimum is {profile.min_chars}."
        )

    if character_count > profile.max_chars:
        errors.append(
            f"{profile.platform} content is too long: "
            f"{character_count} characters. "
            f"Maximum is {profile.max_chars}."
        )

    if hashtag_count > profile.max_hashtags:
        errors.append(
            f"{profile.platform} has too many hashtags: "
            f"{hashtag_count}. "
            f"Maximum is {profile.max_hashtags}."
        )

    return errors


def build_variant(
    platform: str,
    content: str,
) -> GeneratedVariant:

    profile = PROFILES[platform]

    content = content.strip()

    errors = validate_content(
        content,
        profile,
    )

    return GeneratedVariant(
        platform=platform,
        content=content,
        status="draft" if not errors else "rejected",
        valid=not errors,
        errors=errors,
    )

def generate_with_ollama(content: str,) -> list[GeneratedVariant]:

    base_prompt = f"""
    You are a social media content repurposing assistant.

    Repurpose the following original content into TWO different
    social media posts.

    ORIGINAL CONTENT:
    -----------------
    {content}
    -----------------

    Create:

    1. LinkedIn post
    2. Instagram post

    Requirements:

    LINKEDIN:
    - Minimum 150 characters.
    - Maximum 3000 characters.
    - Maximum 5 hashtags.
    - Professional but natural.
    - Do not invent facts that are not present in the original content.
    - Use paragraphs for readability.
    - LinkedIn MUST contain no more than 5 hashtags total.

    INSTAGRAM:
    - Minimum 1 character.
    - Maximum 2200 characters.
    - Maximum 10 hashtags.
    - More conversational and engaging than LinkedIn.
    - Do not invent facts that are not present in the original content.
    - Use paragraphs for readability.
    - Instagram MUST contain no more than 10 hashtags total.

    Return ONLY valid JSON in exactly this structure:

    {{
        "linkedin": "LinkedIn post text",
        "instagram": "Instagram post text"
    }}
    """

    last_errors = []

    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):

        prompt = base_prompt

        if last_errors:
            prompt += f"""

    IMPORTANT:
    Your previous response failed platform validation.

    The validation errors were:

    {chr(10).join(f"- {error}" for error in last_errors)}

    Generate a corrected response that fixes ALL of these problems.
    Do not repeat the validation errors.
    """

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=120,
            )

            response.raise_for_status()

        except requests.exceptions.RequestException as error:
            raise OllamaGenerationError(
                f"Ollama API request failed: {error}"
            ) from error

        try:
            data = response.json()

            generated_text = data["response"]

            generated_posts = json.loads(
                generated_text
            )

        except (KeyError, TypeError, ValueError) as error:
            raise OllamaGenerationError(
                f"Could not parse Ollama response: {error}"
            ) from error

        linkedin_content = generated_posts.get(
            "linkedin"
        )

        instagram_content = generated_posts.get(
            "instagram"
        )

        if not isinstance(linkedin_content, str):
            raise OllamaGenerationError(
                "Ollama response does not contain valid "
                "LinkedIn content."
            )

        if not isinstance(instagram_content, str):
            raise OllamaGenerationError(
                "Ollama response does not contain valid "
                "Instagram content."
            )

        linkedin = build_variant(
            platform="linkedin",
            content=linkedin_content,
        )

        instagram = build_variant(
            platform="instagram",
            content=instagram_content,
        )

        variants = [
            linkedin,
            instagram,
        ]

        invalid_variants = [
            variant
            for variant in variants
            if not variant.valid
        ]

        if not invalid_variants:
            return variants

        last_errors = [
            error
            for variant in invalid_variants
            for error in variant.errors
        ]

    raise OllamaGenerationError(
        "Ollama failed to generate valid variants after "
        f"{MAX_GENERATION_ATTEMPTS} attempts: "
        + " | ".join(last_errors)
    )

def generate_variants(
    content: str,
) -> list[GeneratedVariant]:

    cleaned_content = clean_markdown(
        content
    )

    if not cleaned_content:
        raise OllamaGenerationError(
            "Cannot generate variants from empty content."
        )

    return generate_with_ollama(
        cleaned_content
    )