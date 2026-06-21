"""Image generation — HF diffusion (gratuit) + Pollinations (sans clé) ; DALL-E optionnel."""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import urllib.parse

import httpx

from llm_config import get_api_key

logger = logging.getLogger(__name__)

_VALID_SIZES = frozenset({"1024x1024", "1792x1024", "1024x1792"})
_HF_MODELS = (
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "runwayml/stable-diffusion-v1-5",
)
_HF_ENDPOINTS = (
    "https://router.huggingface.co/hf-inference/models/{model}",
    "https://api-inference.huggingface.co/models/{model}",
)


async def _hf_generate(client: httpx.AsyncClient, model: str, prompt: str) -> dict | None:
    headers = {}
    hf_key = get_api_key("huggingface")
    if hf_key:
        headers["Authorization"] = f"Bearer {hf_key}"
    body = {"inputs": prompt[:2000]}
    for base_tpl in _HF_ENDPOINTS:
        url = base_tpl.format(model=model)
        for attempt in range(3):
            try:
                resp = await client.post(url, headers=headers, json=body)
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
                if resp.status_code in (503, 504):
                    await asyncio.sleep(8 + attempt * 6)
                    continue
                if not resp.is_success:
                    logger.warning("HF image %s: %s %s", model, resp.status_code, resp.text[:200])
            except Exception as exc:
                logger.warning("HF image %s attempt %s: %s", model, attempt, exc)
                await asyncio.sleep(4)
    return None


async def _pollinations_generate(client: httpx.AsyncClient, prompt: str) -> dict | None:
    """Génération 100 % gratuite, sans clé API (Pollinations.ai)."""
    q = urllib.parse.quote(prompt[:1000])
    url = f"https://image.pollinations.ai/prompt/{q}?width=1024&height=1024&nologo=true&enhance=true"
    try:
        resp = await client.get(url, follow_redirects=True)
        ctype = (resp.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
        if resp.is_success and ctype.startswith("image/") and len(resp.content) > 500:
            b64 = base64.b64encode(resp.content).decode("ascii")
            return {
                "ok": True,
                "image_base64": b64,
                "mime": ctype,
                "prompt": prompt,
                "provider": "pollinations",
            }
    except Exception as exc:
        logger.warning("Pollinations image failed: %s", exc)
    return None


async def _openai_generate(prompt: str, size: str) -> dict | None:
    if os.environ.get("EMO_ALLOW_PAID_IMAGE_GEN", "").lower() not in ("1", "true", "yes"):
        return None
    openai_key = get_api_key("openai")
    if not openai_key:
        return None
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
                b64 = ((resp.json().get("data") or [{}])[0]).get("b64_json")
                if b64:
                    return {
                        "ok": True,
                        "image_base64": b64,
                        "mime": "image/png",
                        "prompt": prompt,
                        "provider": "openai",
                    }
    except Exception as exc:
        logger.warning("OpenAI image generation failed: %s", exc)
    return None


async def generate_image(prompt: str, size: str = "1024x1024") -> dict:
    """Generate an image — gratuit en priorité (HF + Pollinations)."""
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "Prompt vide."}

    size = size if size in _VALID_SIZES else "1024x1024"
    last_error = ""

    async with httpx.AsyncClient(timeout=180.0) as client:
        for model in _HF_MODELS:
            hit = await _hf_generate(client, model, prompt)
            if hit:
                return hit

        hit = await _pollinations_generate(client, prompt)
        if hit:
            return hit

    hit = await _openai_generate(prompt, size)
    if hit:
        return hit

    return {
        "ok": False,
        "error": (
            "Génération d'image indisponible pour le moment. "
            "Les serveurs gratuits sont peut‑être occupés — réessayez dans 1 minute."
        ),
        "detail": last_error or "hf+pollinations",
    }


GENERATE_IMAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "Génère une image gratuitement (HF / Pollinations). "
            "Utilise quand l'utilisateur demande de créer, dessiner ou générer une image ou logo."
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
