#!/bin/bash
set -e

echo "[start.sh] Starting ComfyUI..."
cd /ComfyUI
python main.py \
    --listen 127.0.0.1 \
    --port 8188 \
    --disable-auto-launch \
    --disable-metadata \
    > /tmp/comfyui.log 2>&1 &

COMFY_PID=$!
echo "[start.sh] ComfyUI PID: $COMFY_PID"

# Espera activa — máx 120s
echo "[start.sh] Waiting for ComfyUI to be ready..."
for i in $(seq 1 60); do
    if curl -s http://127.0.0.1:8188/system_stats > /dev/null 2>&1; then
        echo "[start.sh] ComfyUI ready after ${i}x2s"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "[start.sh] ERROR: ComfyUI did not start in 120s"
        cat /tmp/comfyui.log
        exit 1
    fi
    sleep 2
done

echo "[start.sh] Starting RunPod handler..."
cd /
exec python -u rp_handler.py
