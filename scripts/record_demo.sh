#!/usr/bin/env bash
# Record LLMLAB demo video (macOS screen via ffmpeg avfoundation).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT}/docs/demo"
OUT_FILE="${OUT_DIR}/llmlab-demo.mp4"
PID_FILE="${OUT_DIR}/.record_demo.pid"
DURATION="${2:-180}"

mkdir -p "$OUT_DIR"

start_record() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Recording already running (pid $(cat "$PID_FILE"))"
    exit 1
  fi
  SCREEN_DEV="${LLMLAB_AV_SCREEN_DEVICE:-3}"
  echo "Recording screen device ${SCREEN_DEV} for up to ${DURATION}s -> ${OUT_FILE}"
  ffmpeg -y -hide_banner -loglevel warning \
    -f avfoundation -framerate 30 -capture_cursor 1 -capture_mouse_clicks 1 \
    -i "${SCREEN_DEV}:none" -t "$DURATION" \
    -pix_fmt yuv420p -c:v libx264 -preset veryfast -crf 23 \
    "$OUT_FILE" &
  echo $! > "$PID_FILE"
  echo "ffmpeg pid $(cat "$PID_FILE")"
}

stop_record() {
  if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill -INT "$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
  if [ -f "$OUT_FILE" ]; then
    echo "Saved: $OUT_FILE ($(du -h "$OUT_FILE" | awk '{print $1}'))"
  else
    echo "No output at $OUT_FILE"
  fi
}

case "${1:-}" in
  start) start_record ;;
  stop) stop_record ;;
  devices)
    ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep -E "AVFoundation|Capture screen" || true
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "recording pid $(cat "$PID_FILE")"
    else
      echo "not recording"
    fi
    [ -f "$OUT_FILE" ] && ls -lh "$OUT_FILE"
    ;;
  *)
    echo "Usage: $0 {start [sec]|stop|devices|status}"
    exit 1
    ;;
esac
