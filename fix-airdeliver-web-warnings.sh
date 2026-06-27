#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
cd "$ROOT"

WEB_DIR="apps/web"
if [ ! -d "$WEB_DIR" ]; then
  echo "Error: apps/web not found under: $ROOT" >&2
  exit 1
fi

NEXT_CONFIG="$WEB_DIR/next.config.mjs"
HEADER_FILE="$WEB_DIR/components/layout/Header.tsx"

[ -f "$NEXT_CONFIG" ] || { echo "Error: $NEXT_CONFIG not found" >&2; exit 1; }
[ -f "$HEADER_FILE" ] || { echo "Error: $HEADER_FILE not found" >&2; exit 1; }

python3 - "$NEXT_CONFIG" "$HEADER_FILE" <<'PY'
from pathlib import Path
import re, sys
next_config = Path(sys.argv[1])
header = Path(sys.argv[2])

# ---- Patch next.config.mjs ----
text = next_config.read_text()
if 'images:' not in text:
    m = re.search(r'(const\s+nextConfig\s*=\s*\{)', text)
    if m:
        text = text.replace(m.group(1), m.group(1) + '\n  images: { qualities: [75, 90] },', 1)
else:
    if 'qualities:' in text:
        text = re.sub(r'qualities\s*:\s*\[[^\]]*\]', 'qualities: [75, 90]', text, count=1)
    else:
        text = re.sub(r'images\s*:\s*\{', 'images: {\n    qualities: [75, 90],', text, count=1)
next_config.write_text(text)

# ---- Patch Header.tsx ----
text = header.read_text()

# 1) Motion transparent -> rgba(0,0,0,0)
text = text.replace('"transparent"', '"rgba(0, 0, 0, 0)"')

# 2) Add quality/loading/style fixes to logo images conservatively
text = re.sub(
    r'(<Image\s+\n\s*src="/logo\.png"\n\s*alt="airdeliver logo"\n\s*width=\{150\}\n\s*height=\{28\}\n)',
    r'\1                  quality={90}\n                  loading="eager"\n',
    text,
    count=1,
)
text = re.sub(
    r'(<Image\s+\n\s*src="/logo\.png"\n\s*alt=""\n\s*width=\{150\}\n\s*height=\{28\}\n)',
    r'\1                  quality={90}\n',
    text,
    count=1,
)
text = re.sub(
    r'(<Image\s+\n\s*src="/logo\.png"\n\s*alt="airdeliver core logo"\n\s*width=\{120\}\n\s*height=\{24\}\n)',
    r'\1                  quality={90}\n',
    text,
    count=1,
)

# 3) Preserve aspect ratio when CSS changes rendered size
text = re.sub(
    r'(className="h-7 w-auto object-contain[^"]*")',
    r'\1\n                  style={{ height: "auto" }}',
    text,
    count=1,
)
text = re.sub(
    r'(className="absolute top-0 left-0 h-7 w-auto object-contain[^"]*")',
    r'\1\n                  style={{ height: "auto" }}',
    text,
    count=1,
)
text = re.sub(
    r'(className="h-6 w-auto object-contain")',
    r'\1\n                  style={{ height: "auto" }}',
    text,
    count=1,
)

# 4) If priority is present, avoid duplicate eager insertion issues by keeping both harmlessly compatible
header.write_text(text)
PY

# ---- Optional: patch THREE.Clock usage anywhere in apps/web ----
while IFS= read -r -d '' file; do
  perl -0pi -e 's/THREE\.Clock/THREE.Timer/g; s/new\s+Clock\s*\(/new Timer(/g' "$file"
done < <(grep -RIlZ 'THREE\.Clock|new Clock\s*\(' "$WEB_DIR" --exclude-dir=node_modules || true)

cat <<'MSG'
Done.

Fixed automatically:
- apps/web/next.config.mjs -> images.qualities = [75, 90]
- apps/web/components/layout/Header.tsx ->
  - logo quality={90}
  - loading="eager" for above-the-fold main logo
  - style={{ height: "auto" }} on CSS-resized logos
  - replaced "transparent" with "rgba(0, 0, 0, 0)" for animatable motion values
- apps/web/** -> replaced THREE.Clock with THREE.Timer where found

Warnings that may still appear and are expected:
- Stripe HTTP warning in local dev; production must run on HTTPS

Suggested one-liner:
  bash fix-airdeliver-web-warnings.sh /path/to/airdeliver
MSG
