"""Tests for image prompt building and precision routing."""
from image_tools import build_image_prompt, _extract_subject, _hf_model_order, _needs_precision


def test_extract_subject_avec_marque():
    raw = "genere moi une image avec marque test en noir sur blanc"
    assert _extract_subject(raw) == "marque test en noir sur blanc"


def test_extract_subject_colon_format():
    raw = 'Génère une image: fond blanc pur, texte "PRECISION" en rouge'
    assert _extract_subject(raw) == 'fond blanc pur, texte "PRECISION" en rouge'


def test_extract_subject_mot_banane():
    raw = "Genere moi une image avec le mot banane dessus et c'est tout"
    assert "banane" in _extract_subject(raw)
    assert "une image" not in _extract_subject(raw).lower()


def test_precision_detects_text_and_hex_color():
    built = build_image_prompt(
        'fond blanc, texte "TEST" en rouge #FF0000 centré',
    )
    assert built["precision"] is True
    assert "legible text" in built["negative"] or "misspelled" in built["negative"]
    assert "pixel-perfect" in built["final_prompt"] or "exact colors" in built["final_prompt"]


def test_precision_routes_sdxl_first():
    order = _hf_model_order('logo rouge avec texte "EMO"')
    assert order[0] == "stabilityai/stable-diffusion-xl-base-1.0"


def test_non_precision_routes_flux_first():
    order = _hf_model_order("chat orange sur canapé bleu")
    assert order[0] == "black-forest-labs/FLUX.1-schnell"


def test_needs_precision_marque():
    assert _needs_precision("marque test en noir sur blanc") is True
