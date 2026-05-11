# comfyui-wan-i2v

**Phase 4B** — Wan 2.1 Image-to-Video en RunPod Serverless.

Recibe una imagen anime (output de Phase 4A) y devuelve un MP4 real.

```
anime image (base64) → RunPod endpoint → ComfyUI → Wan 2.1 I2V → MP4 (base64)
```

---

## Estructura del repo

```
comfyui-wan-i2v/
├── Dockerfile                          # Imagen Docker completa
├── rp_handler.py                       # Handler RunPod serverless
├── start.sh                            # Arranque ComfyUI + handler
├── workflow_wan_i2v.json               # Workflow ComfyUI (GGUF + VHS MP4)
├── requirements.txt                    # Dependencias Python del handler
├── test_pipeline.py                    # Script de prueba directa
└── .github/
    └── workflows/
        └── build-and-push.yml          # GitHub Actions → Docker Hub
```

---

## Modelo usado

| Componente | Archivo | Tamaño |
|---|---|---|
| Diffusion model | `wan2.1-i2v-14b-480p-Q4_K_S.gguf` | 10.4 GB |
| Text encoder | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 1.2 GB |
| CLIP Vision | `clip_vision_h.safetensors` | 0.6 GB |
| VAE | `wan_2.1_vae.safetensors` | 0.4 GB |
| **Total imagen Docker** | | **~20 GB** |

Se usa la variante GGUF Q4_K_S del modelo 14B para mantener la imagen Docker dentro de ~20 GB y que funcione en RTX 4090 24 GB sin OOM.

---

## Secrets necesarios en GitHub

Ve a **Settings → Secrets and variables → Actions** y agrega:

| Secret | Valor |
|---|---|
| `DOCKERHUB_USERNAME` | Tu usuario de Docker Hub |
| `DOCKERHUB_TOKEN` | Access token de Docker Hub (no contraseña) |

Para crear el token: Docker Hub → Account Settings → Security → New Access Token.

---

## Cómo ejecutar GitHub Actions

1. Crea el repo en GitHub como `comfyui-wan-i2v`
2. Sube todos los archivos a la rama `main`
3. Configura los 2 secrets
4. Ve a **Actions → Build and Push ComfyUI Wan I2V Image → Run workflow**
5. El build tarda ~25-40 min (descarga ~13 GB de modelos durante el build)
6. Al terminar, la imagen queda publicada en:
   ```
   tuusuario/comfyui-wan-i2v:latest
   tuusuario/comfyui-wan-i2v:<short-sha>
   ```

---

## Crear el endpoint en RunPod

1. RunPod → **Serverless → + New Endpoint**
2. **Container Image**: `tuusuario/comfyui-wan-i2v:latest`
3. **Container Disk**: `30 GB`
4. **GPU recomendada**: RTX 4090 (24 GB VRAM) o A100 40 GB
5. **Min Workers**: `0`
6. **Max Workers**: `2`
7. **Idle Timeout**: `60s`
8. Deploy → copiar el **Endpoint ID**

Agrega al `.env` de tu backend:
```
RUNPOD_VIDEO_ENDPOINT_ID=<endpoint_id>
```

---

## Payload de ejemplo

**Submit (POST `/run`):**
```json
{
  "input": {
    "image": "<base64 PNG>",
    "positive_prompt": "anime woman, smooth natural movement, wind in hair",
    "negative_prompt": "low quality, blurry, static, no motion, watermark",
    "width": 832,
    "height": 480,
    "num_frames": 49,
    "seed": 42
  }
}
```

**Response (GET `/status/<job_id>`):**
```json
{
  "status": "COMPLETED",
  "output": {
    "video":  "<base64 MP4>",
    "format": "mp4",
    "frames": 49,
    "width":  832,
    "height": 480
  }
}
```

Frames de referencia: `33` = ~2s, `49` = ~3s, `65` = ~4s (todos múltiplos de 16 + 1).

---

## Probar con test_pipeline.py

```bash
# Requiere RUNPOD_API_KEY y RUNPOD_VIDEO_ENDPOINT_ID en .env
pip install requests python-dotenv

# Test básico
python test_pipeline.py --image animagine_result.png

# Con parámetros
python test_pipeline.py --image animagine_result.png --frames 33 --out clip.mp4
```

---

## Troubleshooting

**"Model not found" al arrancar ComfyUI**
El modelo GGUF va en `/ComfyUI/models/unet/`. Si el wget falló durante el build, el archivo no existe. Verificá los logs del build en GitHub Actions — el `wget` de 10 GB a veces falla por timeout en el runner. En ese caso, hacé re-run del workflow.

**ComfyUI no arranca**
El log de ComfyUI está en `/tmp/comfyui.log` dentro del container. El `start.sh` imprime ese log si ComfyUI no levanta en 120s. Causas comunes: CUDA no disponible (GPU no asignada al worker) o puerto 8188 bloqueado.

**No aparece MP4 en el output**
El nodo `VHS_VideoCombine` guarda el video en `/ComfyUI/output/`. Si el `extract_video` falla, usualmente es porque el workflow terminó con error de ComfyUI. Revisá el campo `status.messages` en el historial del job.

**Timeout (job > 10 min)**
Con Q4_K_S en RTX 4090, 49 frames tarda ~3-5 min. Si supera 10 min es probable OOM o cold start lento. Reducí `num_frames` a 33 para pruebas. Si el cold start es el problema, considerá subir `Min Workers` a 1.

**Out of memory (OOM)**
Q4_K_S necesita ~16-18 GB VRAM en inferencia. En RTX 4090 (24 GB) hay margen. En GPUs de 16 GB puede fallar. En ese caso usar `Q3_K_M` (8.59 GB) cambiando el `wget` en el Dockerfile y el nombre en el workflow y handler.
