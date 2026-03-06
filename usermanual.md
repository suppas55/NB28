# usermanual.md — `test_google_vision2.py`

A small, dependable smoke-test script for **Google Cloud Vision API** using **API-key auth** (`?key=...`). It’s designed to run non-interactively (CI-friendly) and gives clear success/failure output.

> Note: This script uses **API keys**, not service-account OAuth. If you need service-account auth, you’ll use a different flow.

---

## What it does

- Builds a single `images:annotate` request to the Vision API endpoint.
- Sends a base64-encoded image payload.
- Requests one Vision **feature type** (labels, text, faces, etc.).
- Prints the full JSON response (or a simple OK/FAIL in `--quiet` mode).

---

## Requirements

- Python 3.x
- `requests`

Install dependency:

```bash
pip install requests
```

---

## Authentication (API key)

Provide your Vision API key either via environment variable (preferred) or CLI flag.

### Environment variables

The script checks these env vars in order and uses the first one that is set:

1. `GOOGLE_VISION_API_KEY`
2. `GOOGLE_API_KEY`
3. `GEMINI_API_KEY`

Example:

```bash
export GOOGLE_VISION_API_KEY="YOUR_KEY_HERE"
```

### CLI flag

```bash
python test_google_vision2.py --api-key "YOUR_KEY_HERE"
```

---

## Image input options

Exactly one of the following is used:

1. `--image PATH` — read a local image file and base64-encode it
2. `--image-b64 BASE64` — provide base64 content directly
3. (default) built-in 1×1 PNG test image (base64)

Examples:

```bash
python test_google_vision2.py --image ./cat.jpg
python test_google_vision2.py --image-b64 "iVBORw0KGgoAAA..."
python test_google_vision2.py   # uses built-in 1x1 png
```

---

## Features (what to detect)

The script sends one feature with `type=<FEATURE>` and `maxResults=<N>`.

### Common feature values

The script knows about these common feature types (Vision supports more):

- `LABEL_DETECTION`
- `TEXT_DETECTION`
- `DOCUMENT_TEXT_DETECTION`
- `LOGO_DETECTION`
- `LANDMARK_DETECTION`
- `FACE_DETECTION`
- `SAFE_SEARCH_DETECTION`
- `IMAGE_PROPERTIES`
- `OBJECT_LOCALIZATION`

If you pass a feature not in that set, it will warn but still continue.

---

## Usage

```bash
python test_google_vision2.py [options]
```

### Options

- `--api-key` — API key (or set `GOOGLE_VISION_API_KEY`)
- `--image` — path to local image file
- `--image-b64` — base64 image content
- `--feature` — Vision feature type (default: `LABEL_DETECTION`)
- `--max-results` — max results to request (default: `5`)
- `--timeout` — HTTP timeout seconds (default: `30`)
- `--endpoint` — override endpoint (default: `https://vision.googleapis.com/v1/images:annotate`)
- `--quiet` — only print pass/fail

---

## Examples

### Label detection

```bash
export GOOGLE_VISION_API_KEY="..."
python test_google_vision2.py --feature LABEL_DETECTION --image ./cat.jpg
```

### Text detection

```bash
export GOOGLE_VISION_API_KEY="..."
python test_google_vision2.py --feature TEXT_DETECTION --image ./receipt.png
```

### Quiet mode (CI)

```bash
export GOOGLE_VISION_API_KEY="..."
python test_google_vision2.py --quiet --feature LABEL_DETECTION --image ./cat.jpg
# prints: ✅ OK   (exit 0)  or  ❌ FAIL (exit 1)
```

---

## Exit codes

- `0` — request succeeded
- `1` — request failed (HTTP error, network error, JSON parse error, etc.)
- `2` — bad invocation (missing API key, conflicting image args, missing file)

---

## Troubleshooting

### “No API key provided”

Set `GOOGLE_VISION_API_KEY` or pass `--api-key`.

### HTTP non-200 error

The script raises a `RuntimeError` that includes the HTTP status and the error JSON returned by Google.

Common causes:
- API key doesn’t have Vision API enabled
- key is restricted (HTTP referrer / IP / API restrictions)
- billing/project configuration issues

### Timeouts

Increase timeout:

```bash
python test_google_vision2.py --timeout 60 --image ./cat.jpg
```

---

## How it works (high level)

1. Parse CLI args with `argparse`.
2. Resolve API key (env vars first, then `--api-key`).
3. Resolve image content (file → base64, or direct base64, or default test image).
4. Build request JSON:

```json
{
  "requests": [
    {
      "image": {"content": "<base64>"},
      "features": [{"type": "LABEL_DETECTION", "maxResults": 5}]
    }
  ]
}
```

5. POST to:

```
https://vision.googleapis.com/v1/images:annotate?key=<API_KEY>
```

6. Print result JSON on success.
