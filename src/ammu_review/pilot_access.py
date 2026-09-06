"""Private pilot access control.

This is a controlled-pilot gate, not a user-account system: one shared
access code, supplied via a server-side environment variable, protects the
entire application entry point so a deployed instance is not an
unauthenticated public LLM endpoint. See .ai/PRODUCTION_READINESS.md.

Fail-closed by design: if the access code isn't configured in the
environment, ``get_pilot_access_code()`` returns ``None`` and the caller
(``ui/app.py``) must treat that as "block everyone", never as "no gate
needed" -- a missing secret must never accidentally make the app public.
"""

from __future__ import annotations

import hmac
import os

ACCESS_CODE_ENV_VAR = "AMMU_PILOT_ACCESS_CODE"


def get_pilot_access_code() -> str | None:
    """The configured pilot access secret, or None if unset.

    Never logged, never persisted -- read fresh from the environment on
    every call rather than cached anywhere.
    """
    return os.getenv(ACCESS_CODE_ENV_VAR) or None


def check_access_code(candidate: str, expected: str) -> bool:
    """Constant-time comparison, so a valid code can't be inferred from
    response-time differences between a near-miss and a wildly wrong guess.
    """
    return hmac.compare_digest(candidate, expected)
