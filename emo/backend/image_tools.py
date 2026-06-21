"""Image generation — DALL-E 3 (OpenAI) with Hugging Face diffusion fallback."""
from __future__ import annotations

import base64
import logging

import httpx

from llm_config import get_api_key

logger = logging.getLogger(__name__)

_VALID_SIZES = frozenset({"1024x1024", "1792x1024", "1024x1792"})
_HF_MODELS = (
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
)


async def generate_image(prompt: str, size: str = "1024x1024") -> dict:
    """Generate an image from a text prompt. Returns base64 PNG/JPEG or error dict."""
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "Prompt vide."}

    size = size if size in _VALID_SIZES else "1024x1024"
    last_error = ""

    openai_key = get_api_key("openai")
    if openai_key:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt[:4000],
                        "n": 1,
                        "size": size,
                        "response_format": "b64_json",
                    },
                )
                if resp.is_success:
                    data = resp.json()
                    b64 = ((data.get("data") or [{}])[0]).get("b64_json")
                    if b64:
                        return {
                            "ok": True,
                            "image_base64": b64,
                            "mime": "image/png",
                            "prompt": prompt,
                            "provider": "openai",
                        }
                last_error = resp.text[:300]
        except Exception as exc:
            last_error = str(exc)[:300]
            logger.warning("OpenAI image generation failed: %s", exc)

    hf_key = get_api_key("huggingface")
    if hf_key:
        for model in _HF_MODELS:
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    resp = await client.post(
                        f"https://api-inference.huggingface.co/models/{model}",
                        headers={"Authorization": f"Bearer {hf_key}"},
                        json={"inputs": prompt[:2000]},
                    )
                    ctype = (resp.headers.get("content-type") or "").split(";")[0].strip()
                    if resp.is_success and ctype.startswith("image/"):
                        b64 = base64.b64encode(resp.content).decode("ascii")
                        return {
                            "ok": True,
                            "image_base64": b64,
                            "mime": ctype,
                            "prompt": prompt,
                            "provider": "huggingface",
                            "model": model,
                        }
                    if not resp.is_success:
                        last_error = resp.text[:300]
            except Exception as exc:
                last_error = str(exc)[:300]
                logger.warning("HF image generation (%s) failed: %s", model, exc)

    hint = "Configure OPENAI_API_KEY (DALL-E 3) ou HF_TOKEN (diffusion) dans backend/.env."
    if last_error:
        return {"ok": False, "error": f"Génération d'image échouée. {hint}", "detail": last_error}
    return {"ok": False, "error": f"Génération d'image indisponible. {hint}"}


GENERATE_IMAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "Génère une image à partir d'une description textuelle (DALL-E ou modèle diffusion). "
            "Utilise quand l'utilisateur demande de créer, dessiner ou générer une image."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description détaillée de l'image à générer (style, sujet, couleurs).",
                },
                "size": {
                    "type": "string",
                    "description": "Taille: 1024x1024 (défaut), 1792x1024 (paysage), 1024x1792 (portrait).",
                },
            },
            "required": ["prompt"],
        },
    },
}
