#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
IMAGE_FILE="${1:-test-image.jpg}"

if [[ ! -f "$IMAGE_FILE" ]]; then
  echo "File not found: $IMAGE_FILE" >&2
  echo "Usage: ./test.sh /path/to/image.jpg" >&2
  exit 1
fi

echo "1. Gateway health"
curl --fail --silent --show-error "$BASE_URL/health"
echo

echo "2. Login as pre-created user bob"
LOGIN_RESPONSE="$(curl --fail --silent --show-error \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"login":"bob","password":"qwe123"}' \
  "$BASE_URL/token")"
TOKEN="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])' <<<"$LOGIN_RESPONSE")"
echo "Token received"

echo "3. Read current user"
curl --fail --silent --show-error \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/v1/user"
echo

echo "4. Upload image"
UPLOAD_RESPONSE="$(curl --fail --silent --show-error \
  -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/octet-stream' \
  --data-binary "@$IMAGE_FILE" \
  "$BASE_URL/upload")"
OBJECT="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["object"])' <<<"$UPLOAD_RESPONSE")"
echo "$UPLOAD_RESPONSE"

echo "5. Download through public compatibility route"
curl --fail --silent --show-error \
  "$BASE_URL/images/$OBJECT" \
  --output "downloaded-$OBJECT"
echo "Saved as downloaded-$OBJECT"

echo "6. Download through protected route"
curl --fail --silent --show-error \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/v1/user/$OBJECT" \
  --output "protected-$OBJECT"
echo "Saved as protected-$OBJECT"

echo "All checks passed"
