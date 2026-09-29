import requests; from bs4 import BeautifulSoup; from urllib.parse import urlparse

REQUEST_TIMEOUT = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/153.0 Safari/537.36"
    )
}

def validate_url(url: str) -> None:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL cannot be empty.")

    parsed_url = urlparse(url)

    if parsed_url.scheme not in ("http", "https"):
        raise ValueError(
            "Invalid URL. URL must start with http:// or https://."
        )

    if not parsed_url.netloc:
        raise ValueError(
            "Invalid URL. A valid domain is required."
        )

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "nav",
            "footer",
            "header",
            "aside",
        ]
    ):
        element.decompose()

    text = soup.get_text(
        separator="\n",
        strip=True,
    )

    if not text:
        raise ValueError(
            "Could not extract readable text from the webpage."
        )

    return text

def fetch_and_extract(url: str) -> str:
    validate_url(url)
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "The request timed out while fetching the URL."
        ) from error

    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code

        raise RuntimeError(
            f"Failed to fetch URL. "
            f"The server returned HTTP {status_code}."
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Failed to fetch URL: {error}"
        ) from error
    return extract_text(response.text)