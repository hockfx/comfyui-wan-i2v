"""
rp_handler.py — RunPod Serverless handler para Wan 2.1 Image-to-Video
Recibe: imagen anime en base64
Retorna: MP4 en base64
"""
import runpod
import requests
import base64
import json
import time
import uuid
import os

COMFY_URL  = "http://127.0.0.1:8188"
OUTPUT_DIR = "/ComfyUI/output"


# ── Espera a que ComfyUI esté up ──────────────────────────────────────────────
def wait_for_comfy(max_wait: int = 120):
    print("[handler] Waiting for ComfyUI...")
    for _ in range(max_wait // 3):
        try:
            r = requests.get(f"{COMFY_URL}/system_stats", timeout=5)
            if r.status_code == 200:
                print("[handler] ComfyUI ready.")
                return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError("ComfyUI did not become ready in time")


# ── Sube imagen base64 al input de ComfyUI ────────────────────────────────────
def upload_image(image_b64: str, filename: str) -> str:
    # Acepta base64 puro o con data-URI prefix
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    image_bytes = base64.b64decode(image_b64)
    resp = requests.post(
        f"{COMFY_URL}/upload/image",
        files={"image": (filename, image_bytes, "image/png")},
        data={"overwrite": "true"},
        timeout=30,
    )
    resp.raise_for_status()
    confirmed = resp.json()["name"]
    print(f"[handler] Image uploaded: {confirmed}")
    return confirmed


# ── Carga workflow y parchea parámetros ───────────────────────────────────────
def build_workflow(input_filename, positive, negative, width, height, frames, seed):
    with open("/workflow_wan_i2v.json", "r") as f:
        wf = json.load(f)

    # Nodo 1: UnetLoaderGGUF — nombre del modelo
    wf["1"]["inputs"]["unet_name"] = "wan2.1-i2v-14b-480p-Q4_K_S.gguf"
    # Nodo 2: LoadImage — imagen de entrada
    wf["2"]["inputs"]["image"]     = input_filename
    # Nodo 5: CLIPTextEncode — positive
    wf["5"]["inputs"]["text"]      = positive
    # Nodo 6: CLIPTextEncode — negative
    wf["6"]["inputs"]["text"]      = negative
    # Nodo 8: WanImageToVideo — resolución, frames, seed
    wf["8"]["inputs"]["width"]     = width
    wf["8"]["inputs"]["height"]    = height
    wf["8"]["inputs"]["length"]    = frames
    wf["8"]["inputs"]["seed"]      = seed

    return wf


# ── Encola workflow en ComfyUI ────────────────────────────────────────────────
def queue_workflow(workflow: dict) -> str:
    client_id = str(uuid.uuid4())
    payload   = {"prompt": workflow, "client_id": client_id}
    resp = requests.post(f"{COMFY_URL}/prompt", json=payload, timeout=30)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]
    print(f"[handler] Queued prompt_id: {prompt_id}")
    return prompt_id


# ── Polling hasta completado ──────────────────────────────────────────────────
def wait_for_job(prompt_id: str, timeout: int = 600) -> dict:
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Job timed out after {timeout}s")

        try:
            resp = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=10)
            data = resp.json()
        except Exception as e:
            print(f"[handler] History fetch error: {e}")
            time.sleep(5)
            continue

        if prompt_id in data:
            job    = data[prompt_id]
            status = job.get("status", {})
            if status.get("completed"):
                print(f"[handler] Job completed in {elapsed:.1f}s")
                return job
            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                raise RuntimeError(f"ComfyUI job error: {msgs}")

        print(f"[handler]   [{elapsed:.0f}s] waiting...")
        time.sleep(5)


# ── Extrae el MP4 del historial ───────────────────────────────────────────────
def extract_video(job: dict) -> bytes:
    outputs = job.get("outputs", {})
    for node_id, node_out in outputs.items():
        # VHS_VideoCombine guarda en "gifs" aunque sea mp4
        for key in ("gifs", "videos", "images"):
            files = node_out.get(key, [])
            for f in files:
                fname     = f.get("filename", "")
                subfolder = f.get("subfolder", "")
                ftype     = f.get("type", "output")
                if not (fname.endswith(".mp4") or fname.endswith(".webm")):
                    continue
                # Primero intenta leer del disco
                candidates = [
                    os.path.join(OUTPUT_DIR, subfolder, fname),
                    os.path.join(OUTPUT_DIR, fname),
                ]
                for path in candidates:
                    if os.path.exists(path):
                        print(f"[handler] Reading video from disk: {path}")
                        with open(path, "rb") as fh:
                            return fh.read()
                # Fallback: HTTP
                print(f"[handler] Fetching video via HTTP: {fname}")
                r = requests.get(
                    f"{COMFY_URL}/view",
                    params={"filename": fname, "subfolder": subfolder, "type": ftype},
                    timeout=60,
                )
                r.raise_for_status()
                return r.content

    raise RuntimeError("No MP4/WebM found in job output. Check workflow VHS_VideoCombine node.")


# ── Handler principal ─────────────────────────────────────────────────────────
def handler(job):
    inp = job.get("input", {})

    # Validación básica
    image_b64 = inp.get("image")
    if not image_b64:
        return {"error": "Missing required field: 'image' (base64 PNG)"}

    positive = inp.get("positive_prompt",
        "anime woman, smooth natural movement, gentle breeze, wind in hair, subtle motion")
    negative = inp.get("negative_prompt",
        "low quality, blurry, static image, no motion, watermark, deformed")
    width    = int(inp.get("width",  832))
    height   = int(inp.get("height", 480))
    frames   = int(inp.get("num_frames", 49))   # ~3s @ 16fps
    seed     = int(inp.get("seed", 42))

    print(f"[handler] Job start | {width}x{height} | frames={frames} | seed={seed}")

    try:
        # 1) Subir imagen
        job_uid         = str(uuid.uuid4())[:8]
        input_filename  = f"wan_input_{job_uid}.png"
        confirmed_name  = upload_image(image_b64, input_filename)

        # 2) Build workflow y encolar
        workflow  = build_workflow(confirmed_name, positive, negative,
                                   width, height, frames, seed)
        prompt_id = queue_workflow(workflow)

        # 3) Esperar resultado
        job_result = wait_for_job(prompt_id, timeout=600)

        # 4) Extraer MP4
        video_bytes = extract_video(job_result)
        video_b64   = base64.b64encode(video_bytes).decode("utf-8")

        print(f"[handler] Done. Video size: {len(video_bytes)/1024:.1f} KB")

        return {
            "video":   video_b64,
            "format":  "mp4",
            "frames":  frames,
            "width":   width,
            "height":  height,
        }

    except Exception as e:
        print(f"[handler] ERROR: {e}")
        return {"error": str(e)}


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    wait_for_comfy()
    print("[handler] RunPod serverless starting...")
    runpod.serverless.start({"handler": handler})
