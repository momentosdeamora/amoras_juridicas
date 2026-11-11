#!/bin/sh
set -eu
ollama serve &
model_pid=$!
trap 'kill "$model_pid" 2>/dev/null || true' EXIT INT TERM
model_attempt=0
until ollama list >/dev/null 2>&1; do
  model_attempt=$((model_attempt + 1))
  if [ "$model_attempt" -gt 30 ]; then exit 1; fi
  sleep 1
done
ollama pull qwen3:1.7b
