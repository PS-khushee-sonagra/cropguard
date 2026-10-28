import logging
import time

from google.genai.errors import ServerError

MAX_ATTEMPTS = 3


class GeminiServiceUnavailableError(RuntimeError):
    """Raised when Gemini remains unavailable after retrying."""


def generate_content_with_retry(generate_content, **request):
    """Execute Gemini request with exponential backoff (2s, 4s) on HTTP 503."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            return generate_content(**request)
        except ServerError as error:
            if error.code != 503:
                raise
            if attempt == MAX_ATTEMPTS - 1:
                raise GeminiServiceUnavailableError(
                    "Gemini is temporarily busy. Please try again in a few minutes."
                ) from error

            delay = 2 ** (attempt + 1)
            logging.warning("Gemini is busy; retrying in %s seconds.", delay)
            time.sleep(delay)
