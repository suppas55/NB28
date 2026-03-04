"""Google Vision API quick test (refactored).

A small, dependable smoke-test for a Google Cloud Vision API key.

Highlights:
- argparse-based CLI (works in CI / non-interactive runs)
- supports multiple feature types (label/text/etc.)
- clear errors + HTTP timeouts
- API key from env or --api-key
- image from local file, base64, or built-in 1x1 PNG

Examples:
  export GOOGLE_VISION_API_KEY="..."
  python test_google_vision2.py --feature LABEL_DETECTION --image ./cat.jpg
  python test_google_vision2.py --feature TEXT_DETECTION --image ./receipt.png
  python test_google_vision2.py  # uses built-in 1x1 png

Note: This script uses API-key auth (?key=...). Service-account auth is different.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


DEFAULT_TEST_IMAGE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

# A helpful set of common Vision feature types (Vision supports more).
KNOWN_FEATURE_TYPES = {
    "LABEL_DETECTION",
    "TEXT_DETECTION",
    "DOCUMENT_TEXT_DETECTION",
    "LOGO_DETECTION",
    "LANDMARK_DETECTION",
    "FACE_DETECTION",
    "SAFE_SEARCH_DETECTION",
    "IMAGE_PROPERTIES",
    "OBJECT_LOCALIZATION",
}


@dataclass
class VisionRequest:
    api_key: str
    image_b64: str
    features: List[Dict[str, Any]]
    endpoint: str = "https://vision.googleapis.com/v1/images:annotate"
    timeout_s: int = 30

    def url(self) -> str:
        return f"{self.endpoint}?key={self.api_key}"

    def payload(self) -> Dict[str, Any]:
        return {
            "requests": [
                {
                    "image": {"content": self.image_b64},
                    "features": self.features,
                }
            ]
        }


def _read_file_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _resolve_api_key(cli_value: Optional[str]) -> Optional[str]:
    # Keep compatibility with the original script env var name, plus a couple
    # common alternates people may have set.
    for name in ("GOOGLE_VISION_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        v = os.getenv(name)
        if v:
            return v
    return cli_value


def call_vision(req: VisionRequest) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}

    resp = requests.post(
        req.url(),
        headers=headers,
        data=json.dumps(req.payload()),
        timeout=req.timeout_s,
    )

    # Parse JSON even on non-200 (Google returns error JSON).
    try:
        body: Dict[str, Any] = resp.json()
    except Exception:
        body = {"raw": resp.text}

    if resp.status_code != 200:
        raise RuntimeError(
            f"Vision API request failed (HTTP {resp.status_code}): {json.dumps(body, ensure_ascii=False)}"
        )

    return body


def build_features(feature: str, max_results: int) -> List[Dict[str, Any]]:
    if feature not in KNOWN_FEATURE_TYPES:
        print(
            f"Warning: feature '{feature}' not in known set {sorted(KNOWN_FEATURE_TYPES)}. Continuing anyway.",
            file=sys.stderr,
        )
    return [{"type": feature, "maxResults": max_results}]


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Smoke-test a Google Vision API key")
    p.add_argument("--api-key", help="Google Vision API key (or set GOOGLE_VISION_API_KEY)")
    p.add_argument("--image", help="Path to a local image file")
    p.add_argument("--image-b64", help="Base64 image content (alternative to --image)")
    p.add_argument(
        "--feature",
        default="LABEL_DETECTION",
        help="Vision feature type, e.g. LABEL_DETECTION, TEXT_DETECTION",
    )
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    p.add_argument(
        "--endpoint",
        default="https://vision.googleapis.com/v1/images:annotate",
        help="Override Vision endpoint (rarely needed)",
    )
    p.add_argument("--quiet", action="store_true", help="Only print pass/fail")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    api_key = _resolve_api_key(args.api_key)
    if not api_key:
        print(
            "❌ No API key provided. Set GOOGLE_VISION_API_KEY or pass --api-key.",
            file=sys.stderr,
        )
        return 2

    if args.image and args.image_b64:
        print("❌ Use only one of --image or --image-b64", file=sys.stderr)
        return 2

    if args.image_b64:
        image_b64 = args.image_b64
    elif args.image:
        if not os.path.exists(args.image):
            print(f"❌ Image file not found: {args.image}", file=sys.stderr)
            return 2
        image_b64 = _read_file_b64(args.image)
    else:
        image_b64 = DEFAULT_TEST_IMAGE_B64

    req = VisionRequest(
        api_key=api_key,
        image_b64=image_b64,
        features=build_features(args.feature, args.max_results),
        endpoint=args.endpoint,
        timeout_s=args.timeout,
    )

    try:
        result = call_vision(req)
        if args.quiet:
            print("✅ OK")
        else:
            print("✅ API request succeeded")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        if args.quiet:
            print("❌ FAIL")
        else:
            print(f"❌ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
