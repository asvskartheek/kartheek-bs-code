#!/usr/bin/env bash
# Start the Phoenix observability server for AI agent tracing.
# Usage: bash start_phoenix.sh
#   Or background: bash start_phoenix.sh &

set -e

PHOENIX_PORT=6006
PHOENIX_URL="http://localhost:${PHOENIX_PORT}"

# Check if already running
if curl -s --connect-timeout 1 "${PHOENIX_URL}" > /dev/null 2>&1; then
  echo "Phoenix is already running at ${PHOENIX_URL}"
  exit 0
fi

echo "Starting Phoenix observability server..."
uv run python -c "
import phoenix as px
import time

session = px.launch_app(use_temp_dir=False)
print(f'Phoenix UI: {session.url}')
print('Press Ctrl+C to stop the server.')

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print('Phoenix server stopped.')
"
