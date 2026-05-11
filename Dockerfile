# ─────────────────────────────────────────────────────────────────────────────
# comfyui-wan-i2v — Wan 2.1 Image-to-Video
# Base oficial RunPod — handler serverless incluido
# ─────────────────────────────────────────────────────────────────────────────
FROM runpod/worker-comfyui:5.8.5-base

# ── Custom nodes ──────────────────────────────────────────────────────────────
# ComfyUI-GGUF — loader para modelos .gguf (UnetLoaderGGUF)
RUN comfy node install comfyui-gguf

# ComfyUI-VideoHelperSuite — VHS_VideoCombine → genera MP4
RUN comfy node install comfyui-videohelpersuite

# ComfyUI-WanVideoWrapper — nodos WanImageToVideo y VAEDecodeVideo
RUN comfy node install comfyui-wanvideowrapper

# ── Modelos Wan 2.1 I2V ───────────────────────────────────────────────────────
# Wan2.1 I2V 480p GGUF Q4_K_S — 10.4 GB
RUN comfy model download \
    --url "https://huggingface.co/city96/Wan2.1-I2V-14B-480P-gguf/resolve/main/wan2.1-i2v-14b-480p-Q4_K_S.gguf" \
    --relative-path models/unet \
    --filename wan2.1-i2v-14b-480p-Q4_K_S.gguf

# T5 text encoder — 1.2 GB
RUN comfy model download \
    --url "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    --relative-path models/text_encoders \
    --filename umt5_xxl_fp8_e4m3fn_scaled.safetensors

# CLIP Vision — 0.6 GB
RUN comfy model download \
    --url "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors" \
    --relative-path models/clip_vision \
    --filename clip_vision_h.safetensors

# VAE Wan — 0.4 GB
RUN comfy model download \
    --url "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors" \
    --relative-path models/vae \
    --filename wan_2.1_vae.safetensors

# ── Verificar modelos ─────────────────────────────────────────────────────────
RUN ls -lh /comfyui/models/unet/ && \
    ls -lh /comfyui/models/text_encoders/ && \
    ls -lh /comfyui/models/clip_vision/ && \
    ls -lh /comfyui/models/vae/
