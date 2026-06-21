"""Générateur de site e-commerce clé en main — HTML/CSS/JS professionnels."""
from __future__ import annotations

import re
from html import escape

DEFAULT_PRODUCTS = [
    {"name": "Essentiel Premium", "price": "49,90 €", "badge": "Best-seller", "img": "🛍️"},
    {"name": "Collection Pro", "price": "79,90 €", "badge": "Nouveau", "img": "✨"},
    {"name": "Pack Découverte", "price": "29,90 €", "badge": "", "img": "🎁"},
    {"name": "Édition Limitée", "price": "99,90 €", "badge": "Exclusif", "img": "⭐"},
    {"name": "Classique", "price": "39,90 €", "badge": "", "img": "👕"},
    {"name": "Confort Plus", "price": "59,90 €", "badge": "Promo", "img": "👟"},
]

CLOTHING_PRODUCTS = [
    {"name": "Chemise Oxford", "price": "45,00 €", "badge": "Best-seller", "img": "👔"},
    {"name": "Jean Slim", "price": "69,00 €", "badge": "", "img": "👖"},
    {"name": "Robe Élégance", "price": "89,00 €", "badge": "Nouveau", "img": "👗"},
    {"name": "Sneakers Urban", "price": "79,00 €", "badge": "Promo", "img": "👟"},
    {"name": "Veste Softshell", "price": "119,00 €", "badge": "", "img": "🧥"},
    {"name": "T-shirt Bio", "price": "24,90 €", "badge": "Éco", "img": "👕"},
]


def _parse_brief(brief: str) -> dict:
    t = (brief or "").lower()
    title = "Ma Boutique"
    if m := re.search(r"(?:site|boutique|shop)\s+(?:de\s+|d['\u2019])?([^\.,\n]{3,40})", brief, re.I):
        title = m.group(1).strip().title()
    elif "vêtement" in t or "vetement" in t or "mode" in t:
        title = "Style & Co"
    elif "tech" in t or "électronique" in t:
        title = "Tech Store"
    niche = "general"
    products = DEFAULT_PRODUCTS
    if any(k in t for k in ("vêtement", "vetement", "mode", "chemise", "robe", "fashion")):
        niche = "clothing"
        products = CLOTHING_PRODUCTS
        if title == "Ma Boutique":
            title = "Style & Co"
    tagline = "Découvrez notre sélection premium — livraison rapide, paiement sécurisé."
    if niche == "clothing":
        tagline = "Mode tendance pour hommes et femmes — qualité, style et confort."
    accent = "#7c3aed"
    if "violet" in t or "purple" in t:
        accent = "#7c3aed"
    elif "bleu" in t or "blue" in t:
        accent = "#2563eb"
    elif "vert" in t or "green" in t:
        accent = "#059669"
    elif "rouge" in t or "red" in t:
        accent = "#dc2626"
    raw_title = title[:60]
    return {
        "title": escape(raw_title),
        "raw_title": raw_title,
        "slug": re.sub(r"[^a-z0-9]", "", raw_title.lower()) or "shop",
        "tagline": escape(tagline),
        "products": products,
        "accent": accent,
        "year": "2026",
    }


def _render_html(cfg: dict) -> str:
    cards = []
    for i, p in enumerate(cfg["products"]):
        badge = f'<span class="badge">{escape(p["badge"])}</span>' if p.get("badge") else ""
        cards.append(
            f"""<article class="product-card" data-id="{i}">
  <div class="product-img" aria-hidden="true">{p["img"]}</div>
  {badge}
  <h3>{escape(p["name"])}</h3>
  <p class="price">{escape(p["price"])}</p>
  <button type="button" class="btn btn-cart" data-add="{escape(p["name"])}">Ajouter au panier</button>
</article>"""
        )
    products_html = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="{cfg["tagline"]}" />
  <title>{cfg["title"]} — Boutique en ligne</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="header">
    <div class="container header-inner">
      <a href="#" class="logo">{cfg["title"]}</a>
      <nav class="nav" id="nav">
        <a href="#accueil">Accueil</a>
        <a href="#produits">Produits</a>
        <a href="#avantages">Avantages</a>
        <a href="#contact">Contact</a>
      </nav>
      <div class="header-actions">
        <button type="button" class="cart-btn" id="cart-btn" aria-label="Panier">
          🛒 <span id="cart-count">0</span>
        </button>
        <button type="button" class="menu-toggle" id="menu-toggle" aria-label="Menu">☰</button>
      </div>
    </div>
  </header>

  <main>
    <section id="accueil" class="hero">
      <div class="container hero-grid">
        <div class="hero-content">
          <p class="eyebrow">Boutique en ligne · Clé en main</p>
          <h1>{cfg["title"]}</h1>
          <p class="hero-lead">{cfg["tagline"]}</p>
          <div class="hero-cta">
            <a href="#produits" class="btn btn-primary">Voir la boutique</a>
            <a href="#contact" class="btn btn-ghost">Nous contacter</a>
          </div>
          <ul class="hero-stats">
            <li><strong>500+</strong><span>Clients</span></li>
            <li><strong>48h</strong><span>Livraison</span></li>
            <li><strong>4.9★</strong><span>Avis</span></li>
          </ul>
        </div>
        <div class="hero-visual">
          <div class="hero-card">✨ Collection {cfg["year"]}</div>
        </div>
      </div>
    </section>

    <section id="produits" class="section">
      <div class="container">
        <div class="section-head">
          <h2>Nos produits</h2>
          <p>Sélection soignée — qualité garantie, retours sous 30 jours.</p>
        </div>
        <div class="product-grid">
{products_html}
        </div>
      </div>
    </section>

    <section id="avantages" class="section section-alt">
      <div class="container features">
        <article><span>🚚</span><h3>Livraison rapide</h3><p>Expédition sous 24–48 h partout en France.</p></article>
        <article><span>🔒</span><h3>Paiement sécurisé</h3><p>CB, PayPal, virement — transactions chiffrées.</p></article>
        <article><span>↩️</span><h3>Retours faciles</h3><p>30 jours pour changer d'avis, sans stress.</p></article>
        <article><span>💬</span><h3>Support 7j/7</h3><p>Une équipe réactive par chat et e-mail.</p></article>
      </div>
    </section>

    <section class="section newsletter">
      <div class="container newsletter-box">
        <h2>−10 % sur votre première commande</h2>
        <p>Inscrivez-vous à la newsletter.</p>
        <form id="newsletter-form" class="newsletter-form">
          <input type="email" placeholder="votre@email.com" required aria-label="E-mail" />
          <button type="submit" class="btn btn-primary">S'inscrire</button>
        </form>
      </div>
    </section>

    <section id="contact" class="section">
      <div class="container contact-grid">
        <div>
          <h2>Contact</h2>
          <p>Questions, devis, partenariats — on vous répond vite.</p>
          <ul class="contact-list">
            <li>📧 contact@{cfg["slug"]}.fr</li>
            <li>📞 01 23 45 67 89</li>
            <li>📍 Paris, France</li>
          </ul>
        </div>
        <form class="contact-form" id="contact-form">
          <input type="text" placeholder="Nom" required />
          <input type="email" placeholder="E-mail" required />
          <textarea rows="4" placeholder="Message"></textarea>
          <button type="submit" class="btn btn-primary">Envoyer</button>
        </form>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="container footer-inner">
      <p>© {cfg["year"]} {cfg["title"]}. Tous droits réservés.</p>
      <div class="footer-links">
        <a href="#">Mentions légales</a>
        <a href="#">CGV</a>
        <a href="#">Confidentialité</a>
      </div>
    </div>
  </footer>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>
  <script src="script.js"></script>
</body>
</html>
"""


def _css(accent: str) -> str:
    return f""":root {{
  --accent: {accent};
  --accent-hover: color-mix(in srgb, {accent} 85%, black);
  --bg: #0f0f12;
  --surface: #1a1a1f;
  --surface-2: #24242b;
  --text: #fafafa;
  --muted: #a1a1aa;
  --radius: 1rem;
  --shadow: 0 8px 32px rgba(0,0,0,.35);
  --font: 'Inter', system-ui, sans-serif;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{ font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.6; }}
.container {{ width: min(1120px, 92vw); margin: 0 auto; }}
a {{ color: inherit; text-decoration: none; }}
img {{ max-width: 100%; display: block; }}

.header {{ position: sticky; top: 0; z-index: 50; background: rgba(15,15,18,.92); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255,255,255,.06); }}
.header-inner {{ display: flex; align-items: center; justify-content: space-between; padding: 1rem 0; gap: 1rem; }}
.logo {{ font-weight: 700; font-size: 1.15rem; letter-spacing: -.02em; }}
.nav {{ display: flex; gap: 1.5rem; }}
.nav a {{ color: var(--muted); font-size: .9rem; transition: color .2s; }}
.nav a:hover {{ color: var(--text); }}
.header-actions {{ display: flex; align-items: center; gap: .75rem; }}
.cart-btn {{ background: var(--surface-2); border: 1px solid rgba(255,255,255,.08); color: var(--text); padding: .45rem .85rem; border-radius: 999px; cursor: pointer; font-size: .85rem; }}
.menu-toggle {{ display: none; background: none; border: none; color: var(--text); font-size: 1.4rem; cursor: pointer; }}

.btn {{ display: inline-flex; align-items: center; justify-content: center; padding: .75rem 1.35rem; border-radius: 999px; font-weight: 600; font-size: .9rem; border: none; cursor: pointer; transition: transform .15s, opacity .15s; }}
.btn:hover {{ transform: translateY(-1px); }}
.btn-primary {{ background: var(--accent); color: #fff; }}
.btn-primary:hover {{ background: var(--accent-hover); }}
.btn-ghost {{ background: transparent; border: 1px solid rgba(255,255,255,.15); color: var(--text); margin-left: .5rem; }}
.btn-cart {{ width: 100%; margin-top: .75rem; background: var(--surface-2); color: var(--text); border: 1px solid rgba(255,255,255,.1); }}

.hero {{ padding: 4rem 0 5rem; background: radial-gradient(ellipse 80% 60% at 50% -10%, color-mix(in srgb, var(--accent) 25%, transparent), transparent); }}
.hero-grid {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 3rem; align-items: center; }}
.eyebrow {{ text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; color: var(--accent); font-weight: 600; margin-bottom: .75rem; }}
.hero h1 {{ font-size: clamp(2.2rem, 5vw, 3.4rem); line-height: 1.1; font-weight: 700; margin-bottom: 1rem; }}
.hero-lead {{ color: var(--muted); font-size: 1.05rem; max-width: 34ch; margin-bottom: 1.75rem; }}
.hero-cta {{ margin-bottom: 2rem; }}
.hero-stats {{ display: flex; gap: 2rem; list-style: none; }}
.hero-stats strong {{ display: block; font-size: 1.35rem; }}
.hero-stats span {{ font-size: .78rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }}
.hero-visual {{ display: flex; justify-content: center; }}
.hero-card {{ width: min(320px, 100%); aspect-ratio: 1; border-radius: 1.5rem; background: linear-gradient(135deg, var(--surface-2), var(--surface)); border: 1px solid rgba(255,255,255,.08); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; font-weight: 600; box-shadow: var(--shadow); }}

.section {{ padding: 4rem 0; }}
.section-alt {{ background: var(--surface); }}
.section-head {{ text-align: center; margin-bottom: 2.5rem; }}
.section-head h2 {{ font-size: 1.85rem; margin-bottom: .5rem; }}
.section-head p {{ color: var(--muted); }}

.product-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 1.25rem; }}
.product-card {{ position: relative; background: var(--surface-2); border: 1px solid rgba(255,255,255,.06); border-radius: var(--radius); padding: 1.25rem; transition: transform .2s, box-shadow .2s; }}
.product-card:hover {{ transform: translateY(-4px); box-shadow: var(--shadow); }}
.product-img {{ font-size: 3rem; text-align: center; padding: 1rem 0; background: var(--surface); border-radius: .75rem; margin-bottom: 1rem; }}
.product-card h3 {{ font-size: 1rem; margin-bottom: .35rem; }}
.price {{ color: var(--accent); font-weight: 700; font-size: 1.1rem; }}
.badge {{ position: absolute; top: 1rem; right: 1rem; background: var(--accent); color: #fff; font-size: .65rem; font-weight: 700; padding: .25rem .5rem; border-radius: 999px; text-transform: uppercase; }}

.features {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; }}
.features article {{ background: var(--surface-2); padding: 1.5rem; border-radius: var(--radius); border: 1px solid rgba(255,255,255,.05); }}
.features span {{ font-size: 1.75rem; display: block; margin-bottom: .75rem; }}
.features h3 {{ font-size: 1rem; margin-bottom: .35rem; }}
.features p {{ color: var(--muted); font-size: .88rem; }}

.newsletter-box {{ text-align: center; background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 20%, var(--surface)), var(--surface-2)); padding: 3rem 2rem; border-radius: 1.25rem; border: 1px solid rgba(255,255,255,.08); }}
.newsletter-form {{ display: flex; gap: .75rem; max-width: 420px; margin: 1.25rem auto 0; flex-wrap: wrap; justify-content: center; }}
.newsletter-form input, .contact-form input, .contact-form textarea {{
  background: var(--bg); border: 1px solid rgba(255,255,255,.1); color: var(--text);
  padding: .75rem 1rem; border-radius: .75rem; font: inherit; width: 100%;
}}
.newsletter-form input {{ flex: 1; min-width: 200px; }}

.contact-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2.5rem; align-items: start; }}
.contact-list {{ list-style: none; margin-top: 1rem; color: var(--muted); }}
.contact-list li {{ margin-bottom: .5rem; }}
.contact-form {{ display: flex; flex-direction: column; gap: .75rem; }}

.footer {{ border-top: 1px solid rgba(255,255,255,.06); padding: 1.5rem 0; margin-top: 2rem; }}
.footer-inner {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; font-size: .85rem; color: var(--muted); }}
.footer-links {{ display: flex; gap: 1.25rem; }}
.footer-links a:hover {{ color: var(--text); }}

.toast {{
  position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%) translateY(120%);
  background: var(--surface-2); border: 1px solid rgba(255,255,255,.1); padding: .75rem 1.25rem;
  border-radius: 999px; font-size: .88rem; opacity: 0; transition: .3s; pointer-events: none; z-index: 100;
}}
.toast.show {{ transform: translateX(-50%) translateY(0); opacity: 1; }}

@media (max-width: 768px) {{
  .menu-toggle {{ display: block; }}
  .nav {{
    position: fixed; inset: 4rem 0 auto 0; background: var(--surface);
    flex-direction: column; padding: 1.5rem; gap: 1rem;
    transform: translateY(-120%); transition: .3s; border-bottom: 1px solid rgba(255,255,255,.08);
  }}
  .nav.open {{ transform: translateY(0); }}
  .hero-grid, .contact-grid {{ grid-template-columns: 1fr; }}
  .hero-visual {{ order: -1; }}
  .btn-ghost {{ margin-left: 0; margin-top: .5rem; }}
}}
"""


JS_TEMPLATE = """(() => {
  const cart = JSON.parse(localStorage.getItem('cart') || '[]');
  const countEl = document.getElementById('cart-count');
  const toast = document.getElementById('toast');

  function updateCart() {
    if (countEl) countEl.textContent = String(cart.length);
    localStorage.setItem('cart', JSON.stringify(cart));
  }

  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2800);
  }

  document.querySelectorAll('[data-add]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const name = btn.getAttribute('data-add');
      cart.push({ name, at: Date.now() });
      updateCart();
      showToast(name + ' ajouté au panier');
    });
  });

  updateCart();

  const toggle = document.getElementById('menu-toggle');
  const nav = document.getElementById('nav');
  toggle?.addEventListener('click', () => nav?.classList.toggle('open'));

  document.getElementById('newsletter-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    showToast('Merci ! Code BIENVENUE10 envoyé (démo).');
    e.target.reset();
  });

  document.getElementById('contact-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    showToast('Message envoyé — nous revenons vers vous vite.');
    e.target.reset();
  });
})();
"""


def build_sales_site(brief: str) -> dict:
    """Retourne index.html, style.css, script.js pour un site e-commerce complet."""
    cfg = _parse_brief(brief)
    return {
        "ok": True,
        "title": cfg["raw_title"],
        "files": {
            "index.html": _render_html(cfg),
            "style.css": _css(cfg["accent"]),
            "script.js": JS_TEMPLATE,
        },
    }
