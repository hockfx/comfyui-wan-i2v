# ─────────────────────────────────────────────────────────────────────────────
# comfyui-wan-i2v — Wan 2.1 Image-to-Video (GGUF Q4_K_S, ~20 GB final)
# RunPod Serverless + ComfyUI
# ─────────────────────────────────────────────────────────────────────────────
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ── Sistema base ──────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
        python3.11 python3.11-venv python3-pip \
        git wget curl ffmpeg \
        libgl1-mesa-glx libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 \
 && ln -sf /usr/bin/python3 /usr/bin/python

# ── PyTorch + ComfyUI ────────────────────────────────────────────────────────
WORKDIR /
RUN git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git

WORKDIR /ComfyUI

RUN pip install --no-cache-dir \
        torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 \
        --index-url https://download.pytorch.org/whl/cu121

RUN pip install --no-cache-dir -r requirements.txt

# ── Custom nodes ──────────────────────────────────────────────────────────────
WORKDIR /ComfyUI/custom_nodes

# ComfyUI-GGUF — loader para modelos .gguf (UnetLoaderGGUF)
RUN git clone --depth=1 https://github.com/city96/ComfyUI-GGUF.git \
 && cd ComfyUI-GGUF && pip install --no-cache-dir -r requirements.txt

# ComfyUI-VideoHelperSuite — VHS_VideoCombine → genera MP4 real
RUN git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git \
 && cd ComfyUI-VideoHelperSuite && pip install --no-cache-dir -r requirements.txt

# ── RunPod SDK ────────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir runpod requests

# ── Directorios de modelos ────────────────────────────────────────────────────
RUN mkdir -p \
    /ComfyUI/models/unet \
    /ComfyUI/models/text_encoders \
    /ComfyUI/models/clip_vision \
    /ComfyUI/models/vae

# ── Descarga de modelos (baked en imagen) ─────────────────────────────────────
# Wan2.1 I2V 480p GGUF Q4_K_S — 10.4 GB
# Menor footprint viable para 14B i2v en RTX 4090 24 GB
RUN wget --progress=dot:giga \
    -O /ComfyUI/models/unet/wan2.1-i2v-14b-480p-Q4_K_S.gguf \
    "https://huggingface.co/city96/Wan2.1-I2V-14B-480P-gguf/resolve/main/wan2.1-i2v-14b-480p-Q4_K_S.gguf"

# T5 text encoder — 1.2 GB
RUN wget --progress=dot:giga \
    -O /ComfyUI/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"

# CLIP Vision — 0.6 GB
RUN wget --progress=dot:giga \
    -O /ComfyUI/models/clip_vision/clip_vision_h.safetensors \
    "https://huggingface.co/comfyanonymous/clip_vision_gits/resolve/main/clip_vision_h.safetensors"

# VAE Wan — 0.4 GB
RUN wget --progress=dot:giga \
    -O /ComfyUI/models/vae/wan_2.1_vae.safetensors \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"

# ── Limpieza de caches pip y apt ──────────────────────────────────────────────
RUN pip cache purge \
 && rm -rf /root/.cache /tmp/*

# ── Handler y archivos de runtime ─────────────────────────────────────────────
WORKDIR /
COPY rp_handler.py .
COPY workflow_wan_i2v.json .
COPY start.sh .
RUN chmod +x /start.sh

CMD ["/start.sh"]
