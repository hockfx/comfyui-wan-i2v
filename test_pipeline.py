"""
test_pipeline.py
Prueba el endpoint Wan I2V directamente contra RunPod.

Uso:
    python test_pipeline.py --image animagine_result.png
    python test_pipeline.py --image animagine_result.png --frames 33 --out clip.mp4
"""
import argparse
import base64
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY     = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_VIDEO_ENDPOINT_ID")

if not API_KEY or not ENDPOINT_ID:
    sys.exit("ERROR: Set RUNPOD_API_KEY and RUNPOD_VIDEO_ENDPOINT_ID in .env")

BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS  = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image",   required=True, help="Path to anime PNG image")
    parser.add_argument("--frames",  type=int, default=49, help="Frames (49=~3s, 33=~2s)")
    parser.add_argument("--width",   type=int, default=832)
    parser.add_argument("--height",  type=int, default=480)
    parser.add_argument("--seed",    type=int, default=42)
    parser.add_argument("--out",     default="wan_result.mp4")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        sys.exit(f"ERROR: File not found: {args.image}")

    # 1) Leer imagen
    with open(args.image, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    print(f"Image loaded: {args.image} ({len(img_b64)//1024} KB b64)")

    # 2) Submit job
    payload = {
        "input": {
            "image":           img_b64,
            "positive_prompt": "anime woman, smooth natural movement, gentle breeze, wind in hair",
            "negative_prompt": "low quality, blurry, static, no motion, watermark",
            "width":           args.width,
            "height":          args.height,
            "num_frames":      args.frames,
            "seed":            args.seed,
        }
    }
    print("Submitting job...")
    r = requests.post(f"{BASE_URL}/run", json=payload, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Submit error {r.status_code}: {r.text}")

    job_id = r.json().get("id")
    if not job_id:
        sys.exit(f"No job_id in response: {r.text}")
    print(f"Job ID: {job_id}")

    # 3) Polling
    data = None
    for i in range(120):   # max 10 min
        time.sleep(5)
        r = requests.get(f"{BASE_URL}/status/{job_id}", headers=HEADERS, timeout=15)
        data = r.json()
        st   = data.get("status", "UNKNOWN")
        print(f"  [{i*5}s] {st}")

        if st == "COMPLETED":
            break
        if st in ("FAILED", "CANCELLED"):
            sys.exit(f"Job {st}: {data.get('error', 'no details')}")

    if not data or data.get("status") != "COMPLETED":
        sys.exit("Timeout: job did not complete in 10 minutes")

    # 4) Guardar video
    video_b64 = data.get("output", {}).get("video")
    if not video_b64:
        sys.exit(f"No video in output. Full response:\n{data}")

    video_bytes = base64.b64decode(video_b64)
    with open(args.out, "wb") as f:
        f.write(video_bytes)

    print(f"\nDone. Video saved: {args.out} ({len(video_bytes)//1024} KB)")


if __name__ == "__main__":
    main()
