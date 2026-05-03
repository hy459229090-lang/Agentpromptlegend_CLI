"""Shared HTTP helper for real provider adapters.

Uses ``urllib`` from the stdlib so the package adds zero runtime dependency
beyond PyYAML. Tests stub :func:`http_post_json` instead of patching urllib
directly to keep the seam stable.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from ouro_agent.providers.base import ProviderError


@dataclass
class HttpResponse:
    status: int
    body: dict
    headers: dict
    latency_ms: int


def http_post_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict,
    timeout: float = 30.0,
    max_retries: int = 1,
) -> HttpResponse:
    """POST a JSON body and parse a JSON response.

    Retries are coarse: only on connection errors and 5xx, with linear backoff.
    Authorization-bearing failures (4xx auth) are surfaced immediately so the
    caller can return a clear error to the player.
    """
    body = json.dumps(payload).encode("utf-8")
    merged_headers = {"content-type": "application/json", **headers}
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=body, headers=merged_headers, method="POST")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                latency_ms = int((time.perf_counter() - started) * 1000)
                try:
                    parsed = json.loads(raw) if raw else {}
                except json.JSONDecodeError as err:
                    raise ProviderError(
                        f"non-JSON response from {url}: {err}"
                    ) from err
                return HttpResponse(
                    status=resp.status,
                    body=parsed if isinstance(parsed, dict) else {"_raw": parsed},
                    headers=dict(resp.headers.items()),
                    latency_ms=latency_ms,
                )
        except urllib.error.HTTPError as err:
            latency_ms = int((time.perf_counter() - started) * 1000)
            err_text = ""
            try:
                err_text = err.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if 500 <= err.code < 600 and attempt < max_retries:
                last_err = err
                time.sleep(0.5 * (attempt + 1))
                continue
            raise ProviderError(
                f"HTTP {err.code} from {url}: {err_text[:400]}"
            ) from err
        except urllib.error.URLError as err:
            if attempt < max_retries:
                last_err = err
                time.sleep(0.5 * (attempt + 1))
                continue
            raise ProviderError(f"network error to {url}: {err}") from err
        except TimeoutError as err:
            raise ProviderError(f"timeout calling {url} after {timeout}s") from err

    if last_err is not None:
        raise ProviderError(f"exhausted retries to {url}: {last_err}")
    raise ProviderError(f"unknown failure calling {url}")


def safe_get(d: Any, *path: Any, default: Any = None) -> Any:
    """Pluck a nested value, returning default on any miss."""
    cur: Any = d
    for key in path:
        if isinstance(cur, list) and isinstance(key, int) and 0 <= key < len(cur):
            cur = cur[key]
            continue
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
            continue
        return default
    return cur if cur is not None else default
