"""Image generation — HF diffusion (gratuit) + Pollinations (sans clé) ; DALL-E optionnel."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import re
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

# Strip French/English image-request prefixes from raw chat messages.
_IMAGE_CMD_VERB_RE = re.compile(
    r"\b(génère|genere|generate|crée|creer|create|dessine|draw|fais|fabrique)\b",
    re.I,
)
_IMAGE_CMD_NOUN_RE = re.compile(
    r"\b(logo|image|illustration|photo|avatar|icône|icone|visuel|affiche|poster|bannière|banniere)\b",
    re.I,
)
_VERB_PREFIX_RE = re.compile(
    r"^(?:génère|genere|generate|crée|creer|create|dessine|dessiner|draw|fais|fait|fabrique|montre)\s*(?:moi\s*)?",
    re.I,
)
_TYPE_DE_PREFIX_RE = re.compile(
    r"^(?:une?\s+)?(?:image|illustration|photo|avatar|icône|icone|visuel|affiche|poster|bannière|banniere|dessin)"
    r"(?:"
    r"\s+(?:de\s+|d[''']|du\s+|d'une?\s+|avec\s+)"
    r"|:\s*"
    r")",
    re.I,
)

_QUALITY_TAIL = "sharp focus, high detail, precise composition"
_PRECISION_TAIL = "exact colors as specified, legible text, clean layout, pixel-perfect details"
_NEGATIVE_BASE = (
    "blurry, out of focus, low quality, distorted, deformed, extra limbs, "
    "random objects, cluttered background, watermark, "
    "cropped, ugly, noisy, oversaturated, abstract, vague, generic"
)
_NEGATIVE_NO_TEXT = _NEGATIVE_BASE + ", illegible text, misspelled text, garbled letters"
_NEGATIVE_DEFAULT = _NEGATIVE_BASE + ", text overlay, logo"
_SHORT_EXPANSION = "clearly visible, well-defined subject, centered composition"

_TEXT_IN_IMAGE_RE = re.compile(
    r"\b(texte|text|écrit|ecrit|inscription|titre|title|mot[s]?|lettre[s]?|"
    r"affiche[r]?|panneau|signe|label|étiquette|etiquette|typograph|"
    r"écrire|ecrire|marqué|marque|caption|slogan)\b",
    re.I,
)
_PRECISION_HINT_RE = re.compile(
    r"\b(exact|précis|precis|précisément|precisement|spécifique|specifique|"
    r"couleur[s]? exacte[s]?|#[0-9a-f]{3,8}\b|rgb\(|layout|grille|grid|"
    r"aligné|aligne|centré|centre|pixel|détail[s]?|detail[s]?|"
    r"petit[s]?|miniature|icône|icone|logo)\b",
    re.I,
)


def _looks_like_user_command(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if _VERB_PREFIX_RE.match(t):
        return True
    return bool(_IMAGE_CMD_VERB_RE.search(t) and _IMAGE_CMD_NOUN_RE.search(t))


def _extract_subject(raw: str) -> str:
    """Remove image-request boilerplate; keep user's subject, style, colors."""
    text = " ".join((raw or "").strip().split())
    if not text:
        return ""
    if not _looks_like_user_command(text):
        return text
    text = _VERB_PREFIX_RE.sub("", text).strip()
    text = _TYPE_DE_PREFIX_RE.sub("", text).strip()
    return text.strip(" .,:;-")


def _expand_short_subject(subject: str) -> str:
    """Minimal expansion only when the subject is too short for the model."""
    if len(subject) >= 20:
        return subject
    return f"{subject}, {_SHORT_EXPANSION}"


def _needs_text_in_image(subject: str) -> bool:
    return bool(_TEXT_IN_IMAGE_RE.search(subject or ""))


def _needs_precision(subject: str) -> bool:
    s = subject or ""
    return _needs_text_in_image(s) or bool(_PRECISION_HINT_RE.search(s))


def _negative_prompt_for(subject: str) -> str:
    return _NEGATIVE_NO_TEXT if _needs_text_in_image(subject) else _NEGATIVE_DEFAULT


def _hf_model_order(subject: str) -> tuple[str, ...]:
    """SDXL first for precision (text/colors/layout); Flux schnell for speed otherwise."""
    if _needs_precision(subject):
        return (
            "stabilityai/stable-diffusion-xl-base-1.0",
            "black-forest-labs/FLUX.1-schnell",
            "runwayml/stable-diffusion-v1-5",
        )
    return _HF_MODELS


def build_image_prompt(
    raw: str,
    *,
    for_pollinations: bool = False,
) -> dict[str, str]:
    """
    Build structured prompts: preserve user intent, minimal quality suffix at end.
    Returns subject, positive, final_prompt, negative.
    """
    subject = _extract_subject(raw)
    if not subject:
        subject = " ".join((raw or "").strip().split())

    subject = _expand_short_subject(subject)
    positive = f"Exact depiction of: {subject}"
    precision = _needs_precision(subject)
    tail = _PRECISION_TAIL if precision else _QUALITY_TAIL

    if for_pollinations:
        # enhance=true on Pollinations already boosts quality — avoid double dilution.
        final = f"{positive}, {tail}" if precision else positive
    else:
        final = f"{positive}, {tail}"

    return {
        "subject": subject,
        "positive": positive,
        "final_prompt": final[:2000],
        "negative": _negative_prompt_for(subject),
        "precision": precision,
    }


def _is_plausible_image(raw: bytes, ctype: str) -> bool:
    """Reject empty, tiny, or non-image payloads (HF sometimes returns garbage)."""
    if not raw or len(raw) < 2000:
        return False
    if raw[:2] == b"\xff\xd8":
        return True
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if raw[:4] == b"RIFF" and len(raw) > 12 and raw[8:12] == b"WEBP":
        return True
    return (ctype or "").startswith("image/")


    if seed is not None:
        return max(0, int(seed))
    digest = hashlib.md5(prompt.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_147_483_647


def _parse_size(size: str) -> tuple[int, int]:
    if size in _VALID_SIZES:
        w, h = size.split("x")
        return int(w), int(h)
    return 1024, 1024


def _hf_parameters(
    model: str,
    width: int,
    height: int,
    seed: int,
    *,
    negative_prompt: str,
    precision: bool = False,
) -> dict:
    if "flux" in model.lower():
        return {
            "width": width,
            "height": height,
            "num_inference_steps": 8 if precision else 4,
            "guidance_scale": 3.5 if precision else 0.0,
            "seed": seed,
        }
    if "xl" in model.lower():
        return {
            "width": width,
            "height": height,
            "num_inference_steps": 40 if precision else 30,
            "guidance_scale": 8.5 if precision else 7.5,
            "negative_prompt": negative_prompt,
            "seed": seed,
        }
    return {
        "width": width,
        "height": height,
        "num_inference_steps": 30 if precision else 25,
        "guidance_scale": 7.5 if precision else 7.0,
        "negative_prompt": negative_prompt,
        "seed": seed,
    }


async def _hf_generate(
    client: httpx.AsyncClient,
    model: str,
    final_prompt: str,
    *,
    width: int,
    height: int,
    seed: int,
    negative_prompt: str,
    precision: bool = False,
) -> dict | None:
    headers = {}
    hf_key = get_api_key("huggingface")
    if hf_key:
        headers["Authorization"] = f"Bearer {hf_key}"
    body = {
        "inputs": final_prompt,
        "parameters": _hf_parameters(
            model, width, height, seed,
            negative_prompt=negative_prompt,
            precision=precision,
        ),
    }
    for base_tpl in _HF_ENDPOINTS:
        url = base_tpl.format(model=model)
        for attempt in range(3):
            try:
                resp = await client.post(url, headers=headers, json=body)
                ctype = (resp.headers.get("content-type") or "").split(";")[0].strip()
                if resp.is_success and ctype.startswith("image/"):
                    if not _is_plausible_image(resp.content, ctype):
                        logger.warning("HF image %s: implausible payload (%s bytes)", model, len(resp.content))
                        continue
                    b64 = base64.b64encode(resp.content).decode("ascii")
                    return {
                        "ok": True,
                        "image_base64": b64,
                        "mime": ctype,
                        "prompt": final_prompt,
                        "final_prompt": final_prompt,
                        "provider": "huggingface",
                        "model": model,
                        "seed": seed,
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


async def _pollinations_generate(
    client: httpx.AsyncClient,
    built: dict[str, str],
    *,
    width: int,
    height: int,
    seed: int,
) -> dict | None:
    """Génération gratuite via Pollinations — sujet préservé, enhance=true côté API."""
    final = built["final_prompt"]
    q = urllib.parse.quote(final)
    neg = urllib.parse.quote(built["negative"])
    guidance = "9.0" if built.get("precision") else "7.5"
    url = (
        f"https://image.pollinations.ai/prompt/{q}"
        f"?width={width}&height={height}&nologo=true&enhance=true&model=flux"
        f"&seed={seed}&negative_prompt={neg}&guidance_scale={guidance}"
    )
    try:
        resp = await client.get(url, follow_redirects=True)
        ctype = (resp.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
        if resp.is_success and ctype.startswith("image/") and _is_plausible_image(resp.content, ctype):
            b64 = base64.b64encode(resp.content).decode("ascii")
            return {
                "ok": True,
                "image_base64": b64,
                "image_url": str(resp.url),
                "mime": ctype,
                "prompt": final,
                "final_prompt": final,
                "subject": built["subject"],
                "provider": "pollinations",
                "seed": seed,
            }
    except Exception as exc:
        logger.warning("Pollinations image failed: %s", exc)
    return None


async def _openai_generate(prompt: str, size: str, *, final_prompt: str, seed: int) -> dict | None:
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
                    "prompt": final_prompt[:4000],
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
                        "final_prompt": final_prompt,
                        "provider": "openai",
                        "seed": seed,
                    }
    except Exception as exc:
        logger.warning("OpenAI image generation failed: %s", exc)
    return None


async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    *,
    seed: int | None = None,
) -> dict:
    """Generate an image — gratuit en priorité (HF + Pollinations)."""
    raw = (prompt or "").strip()
    if not raw:
        return {"ok": False, "error": "Prompt vide."}

    size = size if size in _VALID_SIZES else "1024x1024"
    width, height = _parse_size(size)

    built_hf = build_image_prompt(raw, for_pollinations=False)
    built_poll = build_image_prompt(raw, for_pollinations=True)
    seed_val = _seed_from_prompt(built_hf["final_prompt"], seed)

    logger.info(
        "Image gen subject=%r precision=%s final_hf=%r",
        built_hf["subject"][:120],
        built_hf.get("precision"),
        built_hf["final_prompt"][:200],
    )

    precision = bool(built_hf.get("precision"))
    model_order = _hf_model_order(built_hf["subject"])

    async with httpx.AsyncClient(timeout=180.0) as client:
        for model in model_order:
            hit = await _hf_generate(
                client,
                model,
                built_hf["final_prompt"],
                width=width,
                height=height,
                seed=seed_val,
                negative_prompt=built_hf["negative"],
                precision=precision,
            )
            if hit:
                hit["subject"] = built_hf["subject"]
                hit["negative_prompt"] = built_hf["negative"]
                return hit

        hit = await _pollinations_generate(
            client,
            built_poll,
            width=width,
            height=height,
            seed=seed_val,
        )
        if hit:
            hit["negative_prompt"] = built_poll["negative"]
            return hit

    hit = await _openai_generate(raw, size, final_prompt=built_hf["final_prompt"], seed=seed_val)
    if hit:
        hit["subject"] = built_hf["subject"]
        return hit

    return {
        "ok": False,
        "error": (
            "Génération d'image indisponible pour le moment. "
            "Les serveurs gratuits sont peut‑être occupés — réessayez dans 1 minute."
        ),
        "final_prompt": built_hf["final_prompt"],
        "subject": built_hf["subject"],
    }


GENERATE_IMAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "Génère une image gratuitement (HF / Pollinations). "
            "Utilise quand l'utilisateur demande de créer, dessiner ou générer une image ou logo. "
            "IMPORTANT: le prompt doit reprendre fidèlement le sujet, style, couleurs, texte et composition "
            "demandés — pas de termes génériques (masterpiece, 8k, professional). "
            "Pour texte dans l'image: recopie le mot exact entre guillemets. "
            "Exemple: « chat rouge sur canapé bleu style cartoon » → « chat rouge sur canapé bleu, style cartoon »."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Description précise de l'image: sujet, style, couleurs, composition. "
                        "Reprendre les mots exacts de l'utilisateur, sans reformulation vague."
                    ),
                },
                "size": {
                    "type": "string",
                    "description": "Taille: 1024x1024 (défaut), 1792x1024 (paysage), 1024x1792 (portrait).",
                },
                "seed": {
                    "type": "integer",
                    "description": "Seed optionnel pour reproduire la même image.",
                },
            },
            "required": ["prompt"],
        },
    },
}
