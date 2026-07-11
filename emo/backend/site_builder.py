"""Générateur de site e-commerce premium — photos réelles, panier, animations."""
from __future__ import annotations

import json
import re
from html import escape

# Photos Unsplash (libres, hotlink OK)
_HERO_FASHION = "https://images.unsplash.com/photo-1441984904996-e0b4952c7b39?w=1600&q=85&auto=format&fit=crop"
_HERO_GENERAL = "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=1600&q=85&auto=format&fit=crop"

CLOTHING_PRODUCTS = [
    {"name": "Blazer Laine", "price": "189", "old": "249", "badge": "−24%", "img": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=700&q=80&auto=format&fit=crop", "cat": "homme"},
    {"name": "Robe Satin", "price": "129", "old": "", "badge": "Nouveau", "img": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=700&q=80&auto=format&fit=crop", "cat": "femme"},
    {"name": "Sneakers Aura", "price": "149", "old": "179", "badge": "Promo", "img": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=700&q=80&auto=format&fit=crop", "cat": "chaussures"},
    {"name": "Manteau Urban", "price": "219", "old": "", "badge": "", "img": "https://images.unsplash.com/photo-1539533018447-63fcce267834?w=700&q=80&auto=format&fit=crop", "cat": "homme"},
    {"name": "Sac Cuir", "price": "159", "old": "", "badge": "Best-seller", "img": "https://images.unsplash.com/photo-1584917865442-de89d76ffd96?w=700&q=80&auto=format&fit=crop", "cat": "accessoires"},
    {"name": "Pull Cachemire", "price": "99", "old": "129", "badge": "", "img": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=700&q=80&auto=format&fit=crop", "cat": "femme"},
    {"name": "Jean Raw", "price": "89", "old": "", "badge": "", "img": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=700&q=80&auto=format&fit=crop", "cat": "homme"},
    {"name": "Montre Classique", "price": "249", "old": "", "badge": "Exclusif", "img": "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=700&q=80&auto=format&fit=crop", "cat": "accessoires"},
]

DEFAULT_PRODUCTS = [
    {"name": "Pack Essentiel", "price": "49", "old": "69", "badge": "Promo", "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=700&q=80", "cat": "all"},
    {"name": "Edition Pro", "price": "89", "old": "", "badge": "Nouveau", "img": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=700&q=80", "cat": "all"},
    {"name": "Bundle Premium", "price": "129", "old": "159", "badge": "", "img": "https://images.unsplash.com/photo-1572635196233-15909fad6670?w=700&q=80", "cat": "all"},
    {"name": "Limited Drop", "price": "199", "old": "", "badge": "Exclusif", "img": "https://images.unsplash.com/photo-1560343090-f0409e92744a?w=700&q=80", "cat": "all"},
    {"name": "Starter Kit", "price": "39", "old": "", "badge": "", "img": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=700&q=80", "cat": "all"},
    {"name": "Signature", "price": "159", "old": "", "badge": "Best-seller", "img": "https://images.unsplash.com/photo-1491553895911-2485d0811f7e?w=700&q=80", "cat": "all"},
]


def _parse_brief(brief: str) -> dict:
    t = (brief or "").lower()
    title = "LUXE"
    if "émo" in t or "emo" in t:
        title = "Émo"
    elif m := re.search(r"(?:site|boutique|shop|marque)\s+(?:de\s+|d['\u2019]|pour\s+)?([^\.,\n]{2,40})", brief, re.I):
        title = m.group(1).strip().title()
    elif any(k in t for k in ("vêtement", "vetement", "mode", "fashion")):
        title = "MAISON NOIR"

    niche = "clothing" if any(k in t for k in ("vêtement", "vetement", "mode", "chemise", "robe", "fashion", "vetements")) else "general"
    products = CLOTHING_PRODUCTS if niche == "clothing" else DEFAULT_PRODUCTS

    tagline = "Pièces sélectionnées avec exigence — livraison express, retours gratuits 30 jours."
    if title == "Émo":
        tagline = "L'intelligence qui voit plus loin — design audacieux, expérience premium."

    accent = "#8b5cf6"
    accent2 = "#c084fc"
    if "violet" in t or "purple" in t or "émo" in t or "emo" in t:
        accent, accent2 = "#7c3aed", "#a78bfa"
    elif "bleu" in t or "blue" in t:
        accent, accent2 = "#2563eb", "#60a5fa"
    elif "or" in t or "gold" in t:
        accent, accent2 = "#b8860b", "#d4af37"

    hero_img = _HERO_FASHION if niche == "clothing" else _HERO_GENERAL
    raw = title[:40]
    return {
        "title": escape(raw),
        "raw_title": raw,
        "slug": re.sub(r"[^a-z0-9]", "", raw.lower()) or "shop",
        "tagline": escape(tagline),
        "products": products,
        "accent": accent,
        "accent2": accent2,
        "hero_img": hero_img,
        "year": "2026",
        "niche": niche,
    }


def _product_card(p: dict, i: int) -> str:
    badge = f'<span class="badge">{escape(p["badge"])}</span>' if p.get("badge") else ""
    old = f'<span class="price-old">{escape(p["old"])} €</span>' if p.get("old") else ""
    stars = "★★★★★" if i % 3 != 2 else "★★★★☆"
    return f"""<article class="product-card" data-cat="{escape(p.get('cat', 'all'))}" data-id="{i}">
  <a href="#" class="product-media">
    <img src="{p['img']}" alt="{escape(p['name'])}" loading="lazy" width="400" height="500" />
    <span class="product-overlay">Voir le détail</span>
  </a>
  {badge}
  <div class="product-body">
    <div class="stars" aria-label="4.8 sur 5">{stars}</div>
    <h3>{escape(p["name"])}</h3>
    <div class="price-row"><span class="price">{escape(p["price"])} €</span>{old}</div>
    <button type="button" class="btn btn-cart" data-add="{escape(p["name"])}" data-price="{escape(p["price"])}">Ajouter · {escape(p["price"])} €</button>
  </div>
</article>"""


def _render_html(cfg: dict) -> str:
    products_html = "\n".join(_product_card(p, i) for i, p in enumerate(cfg["products"]))
    cats = ["Tout", "Femme", "Homme", "Chaussures", "Accessoires"] if cfg["niche"] == "clothing" else ["Tout", "Nouveautés", "Promo", "Exclusif"]
    cat_btns = "".join(
        f'<button type="button" class="cat-pill{" active" if i == 0 else ""}" data-filter="{c.lower()}">{c}</button>'
        for i, c in enumerate(cats)
    )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="{cfg["tagline"]}" />
  <title>{cfg["title"]} — Boutique premium</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="announce">Livraison offerte dès 80 € · Retours gratuits 30 jours</div>

  <header class="header">
    <div class="container header-inner">
      <a href="#" class="logo"><span class="logo-mark"></span>{cfg["title"]}</a>
      <nav class="nav" id="nav">
        <a href="#accueil">Accueil</a>
        <a href="#collections">Collections</a>
        <a href="#produits">Boutique</a>
        <a href="#avis">Avis</a>
        <a href="#faq">FAQ</a>
      </nav>
      <div class="header-actions">
        <button type="button" class="icon-btn" id="cart-btn" aria-label="Panier">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/><path d="M6 6L5 3H2"/></svg>
          <span class="cart-count" id="cart-count">0</span>
        </button>
        <button type="button" class="menu-toggle" id="menu-toggle" aria-label="Menu"><span></span><span></span></button>
      </div>
    </div>
  </header>

  <main>
    <section id="accueil" class="hero">
      <div class="hero-bg" style="background-image:url('{cfg["hero_img"]}')"></div>
      <div class="hero-overlay"></div>
      <div class="container hero-content">
        <p class="eyebrow">Collection {cfg["year"]}</p>
        <h1>{cfg["title"]}<br /><span class="gradient-text">Redéfinir le style.</span></h1>
        <p class="hero-lead">{cfg["tagline"]}</p>
        <div class="hero-cta">
          <a href="#produits" class="btn btn-primary btn-lg">Explorer la boutique</a>
          <a href="#collections" class="btn btn-ghost btn-lg">Nos collections</a>
        </div>
        <div class="hero-trust">
          <div><strong>12k+</strong><span>Clients</span></div>
          <div><strong>4.9</strong><span>Note moyenne</span></div>
          <div><strong>48h</strong><span>Livraison</span></div>
        </div>
      </div>
    </section>

    <div class="marquee" aria-hidden="true">
      <div class="marquee-track">
        <span>Paiement sécurisé</span><span>·</span><span>Expédition 24–48h</span><span>·</span>
        <span>Retours gratuits</span><span>·</span><span>Support premium</span><span>·</span>
        <span>Paiement sécurisé</span><span>·</span><span>Expédition 24–48h</span><span>·</span>
        <span>Retours gratuits</span><span>·</span><span>Support premium</span><span>·</span>
      </div>
    </div>

    <section id="collections" class="section">
      <div class="container">
        <div class="section-head">
          <p class="label">Collections</p>
          <h2>Curated for you</h2>
        </div>
        <div class="collection-grid">
          <a href="#produits" class="collection-card collection-large" style="background-image:url('https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=900&q=80')">
            <span>Femme</span>
          </a>
          <a href="#produits" class="collection-card" style="background-image:url('https://images.unsplash.com/photo-1617137968427-85924c800a41?w=600&q=80')">
            <span>Homme</span>
          </a>
          <a href="#produits" class="collection-card" style="background-image:url('https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600&q=80')">
            <span>Accessoires</span>
          </a>
        </div>
      </div>
    </section>

    <section id="produits" class="section section-dark">
      <div class="container">
        <div class="section-head">
          <p class="label">Boutique</p>
          <h2>Nos best-sellers</h2>
          <p class="sub">Qualité premium · Matières nobles · Finitions soignées</p>
        </div>
        <div class="cat-bar">{cat_btns}</div>
        <div class="product-grid" id="product-grid">
{products_html}
        </div>
      </div>
    </section>

    <section class="section banner-cta">
      <div class="container banner-inner">
        <div>
          <p class="label">Offre limitée</p>
          <h2>−15 % avec le code <code>WELCOME15</code></h2>
          <p>Valable sur votre première commande — cumulable avec la livraison offerte.</p>
        </div>
        <a href="#produits" class="btn btn-primary btn-lg">J'en profite</a>
      </div>
    </section>

    <section id="avis" class="section">
      <div class="container">
        <div class="section-head"><p class="label">Avis clients</p><h2>Ils nous font confiance</h2></div>
        <div class="testimonials">
          <blockquote><p>« Qualité exceptionnelle, packaging soigné, livraison ultra rapide. Je recommande à 100 % ! »</p><footer>— Marie L. · Paris</footer></blockquote>
          <blockquote><p>« Enfin une boutique où le SAV répond en moins d'une heure. Les produits dépassent mes attentes. »</p><footer>— Thomas K. · Lyon</footer></blockquote>
          <blockquote><p>« Design moderne, coupes parfaites. C'est devenu ma référence mode. »</p><footer>— Sarah M. · Bordeaux</footer></blockquote>
        </div>
      </div>
    </section>

    <section id="faq" class="section section-dark">
      <div class="container faq-grid">
        <div><p class="label">FAQ</p><h2>Questions fréquentes</h2></div>
        <div class="faq-list">
          <details open><summary>Quels sont les délais de livraison ?</summary><p>Expédition sous 24 h, réception en 2–4 jours ouvrés en France métropolitaine.</p></details>
          <details><summary>Puis-je retourner un article ?</summary><p>Oui, retours gratuits sous 30 jours — remboursement ou échange au choix.</p></details>
          <details><summary>Quels moyens de paiement acceptez-vous ?</summary><p>CB, Visa, Mastercard, PayPal, Apple Pay et virement SEPA.</p></details>
          <details><summary>Comment contacter le support ?</summary><p>Chat en ligne 7j/7 ou e-mail — réponse garantie sous 2 h ouvrées.</p></details>
        </div>
      </div>
    </section>

    <section class="section newsletter">
      <div class="container newsletter-box">
        <h2>Rejoignez le club</h2>
        <p>Accès anticipé aux drops + −10 % sur la 1ère commande.</p>
        <form id="newsletter-form" class="newsletter-form">
          <input type="email" placeholder="votre@email.com" required aria-label="E-mail" />
          <button type="submit" class="btn btn-primary">S'inscrire</button>
        </form>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="container footer-grid">
      <div class="footer-brand">
        <span class="logo">{cfg["title"]}</span>
        <p>Boutique premium · Design & qualité depuis {cfg["year"]}.</p>
      </div>
      <div><h4>Boutique</h4><a href="#produits">Produits</a><a href="#collections">Collections</a><a href="#">Soldes</a></div>
      <div><h4>Aide</h4><a href="#faq">FAQ</a><a href="#">Livraison</a><a href="#">Retours</a></div>
      <div><h4>Contact</h4><a href="mailto:hello@{cfg["slug"]}.fr">hello@{cfg["slug"]}.fr</a><a href="#">Instagram</a><a href="#">TikTok</a></div>
    </div>
    <div class="container footer-bottom"><p>© {cfg["year"]} {cfg["title"]}. Tous droits réservés.</p></div>
  </footer>

  <aside class="cart-drawer" id="cart-drawer" aria-hidden="true">
    <div class="cart-header"><h2>Panier</h2><button type="button" id="cart-close" aria-label="Fermer">×</button></div>
    <ul class="cart-items" id="cart-items"></ul>
    <div class="cart-footer">
      <div class="cart-total">Total : <strong id="cart-total">0 €</strong></div>
      <button type="button" class="btn btn-primary btn-block" id="checkout-btn">Commander</button>
    </div>
  </aside>
  <div class="cart-backdrop" id="cart-backdrop"></div>
  <div class="toast" id="toast" role="status"></div>
  <script src="script.js"></script>
</body>
</html>"""


def _css(accent: str, accent2: str) -> str:
    return f""":root {{
  --accent: {accent};
  --accent2: {accent2};
  --bg: #050505;
  --surface: #0c0c0e;
  --surface2: #141418;
  --border: rgba(255,255,255,.08);
  --text: #fafafa;
  --muted: #9ca3af;
  --font-display: 'Syne', system-ui, sans-serif;
  --font-body: 'DM Sans', system-ui, sans-serif;
  --radius: 1rem;
  --shadow: 0 24px 80px rgba(0,0,0,.45);
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{font-family:var(--font-body);background:var(--bg);color:var(--text);line-height:1.6;overflow-x:hidden}}
img{{max-width:100%;display:block;height:auto}}
a{{color:inherit;text-decoration:none}}
.container{{width:min(1200px,92vw);margin:0 auto}}

.announce{{background:linear-gradient(90deg,var(--accent),var(--accent2));color:#fff;text-align:center;font-size:.75rem;font-weight:600;letter-spacing:.06em;padding:.55rem 1rem;text-transform:uppercase}}

.header{{position:sticky;top:0;z-index:100;background:rgba(5,5,5,.85);backdrop-filter:blur(16px);border-bottom:1px solid var(--border)}}
.header-inner{{display:flex;align-items:center;justify-content:space-between;padding:1rem 0;gap:1rem}}
.logo{{font-family:var(--font-display);font-weight:800;font-size:1.25rem;letter-spacing:.04em;display:flex;align-items:center;gap:.5rem}}
.logo-mark{{width:10px;height:10px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:2px}}
.nav{{display:flex;gap:1.75rem}}
.nav a{{font-size:.88rem;color:var(--muted);font-weight:500;transition:color .2s}}
.nav a:hover{{color:var(--text)}}
.header-actions{{display:flex;align-items:center;gap:.5rem}}
.icon-btn{{position:relative;background:var(--surface2);border:1px solid var(--border);color:var(--text);width:42px;height:42px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center}}
.cart-count{{position:absolute;top:-4px;right:-4px;background:var(--accent);color:#fff;font-size:.65rem;font-weight:700;min-width:18px;height:18px;border-radius:999px;display:flex;align-items:center;justify-content:center}}
.menu-toggle{{display:none;flex-direction:column;gap:5px;background:none;border:none;cursor:pointer;padding:8px}}
.menu-toggle span{{display:block;width:22px;height:2px;background:var(--text);border-radius:2px}}

.btn{{display:inline-flex;align-items:center;justify-content:center;gap:.5rem;padding:.75rem 1.5rem;border-radius:999px;font-weight:600;font-size:.9rem;border:none;cursor:pointer;font-family:inherit;transition:transform .2s,box-shadow .2s,background .2s}}
.btn:hover{{transform:translateY(-2px)}}
.btn-lg{{padding:1rem 2rem;font-size:.95rem}}
.btn-primary{{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;box-shadow:0 8px 32px color-mix(in srgb,var(--accent) 40%,transparent)}}
.btn-ghost{{background:rgba(255,255,255,.06);border:1px solid var(--border);color:var(--text);margin-left:.75rem}}
.btn-cart{{width:100%;margin-top:.85rem;background:var(--surface);border:1px solid var(--border);color:var(--text);font-size:.82rem;padding:.65rem}}
.btn-block{{width:100%}}

.hero{{position:relative;min-height:92vh;display:flex;align-items:center;padding:4rem 0;overflow:hidden}}
.hero-bg{{position:absolute;inset:0;background-size:cover;background-position:center;transform:scale(1.05)}}
.hero-overlay{{position:absolute;inset:0;background:linear-gradient(105deg,rgba(5,5,5,.92) 0%,rgba(5,5,5,.55) 45%,rgba(5,5,5,.75) 100%)}}
.hero-content{{position:relative;z-index:2;max-width:640px;padding:2rem 0}}
.eyebrow,.label{{text-transform:uppercase;letter-spacing:.2em;font-size:.7rem;font-weight:600;color:var(--accent2);margin-bottom:1rem}}
.hero h1{{font-family:var(--font-display);font-size:clamp(2.8rem,7vw,4.5rem);line-height:1.02;font-weight:800;margin-bottom:1.25rem}}
.gradient-text{{background:linear-gradient(135deg,#fff,var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero-lead{{font-size:1.1rem;color:var(--muted);max-width:42ch;margin-bottom:2rem;line-height:1.7}}
.hero-cta{{margin-bottom:2.5rem}}
.hero-trust{{display:flex;gap:2.5rem;flex-wrap:wrap}}
.hero-trust strong{{display:block;font-family:var(--font-display);font-size:1.75rem;font-weight:700}}
.hero-trust span{{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}

.marquee{{overflow:hidden;border-block:1px solid var(--border);background:var(--surface);padding:.85rem 0}}
.marquee-track{{display:flex;gap:2rem;animation:marquee 28s linear infinite;width:max-content;font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}}
@keyframes marquee{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}

.section{{padding:5rem 0}}
.section-dark{{background:var(--surface)}}
.section-head{{text-align:center;margin-bottom:2.5rem}}
.section-head h2{{font-family:var(--font-display);font-size:clamp(1.75rem,4vw,2.5rem);font-weight:700;margin-bottom:.5rem}}
.section-head .sub{{color:var(--muted);font-size:.95rem}}

.collection-grid{{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:1rem;min-height:420px}}
.collection-card{{position:relative;border-radius:var(--radius);overflow:hidden;background-size:cover;background-position:center;min-height:200px;display:flex;align-items:flex-end;padding:1.5rem}}
.collection-card::after{{content:'';position:absolute;inset:0;background:linear-gradient(transparent,rgba(0,0,0,.75))}}
.collection-card span{{position:relative;z-index:1;font-family:var(--font-display);font-size:1.35rem;font-weight:700}}
.collection-large{{grid-row:span 2;min-height:100%}}
.collection-card:hover{{transform:scale(1.02);transition:transform .4s}}

.cat-bar{{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;margin-bottom:2rem}}
.cat-pill{{background:transparent;border:1px solid var(--border);color:var(--muted);padding:.45rem 1rem;border-radius:999px;font-size:.8rem;cursor:pointer;font-family:inherit;transition:all .2s}}
.cat-pill.active,.cat-pill:hover{{background:var(--accent);border-color:var(--accent);color:#fff}}

.product-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.5rem}}
.product-card{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;transition:transform .3s,box-shadow .3s}}
.product-card:hover{{transform:translateY(-6px);box-shadow:var(--shadow)}}
.product-card.hidden{{display:none}}
.product-media{{position:relative;display:block;aspect-ratio:4/5;overflow:hidden;background:#111}}
.product-media img{{width:100%;height:100%;object-fit:cover;transition:transform .6s ease}}
.product-card:hover .product-media img{{transform:scale(1.06)}}
.product-overlay{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.4);opacity:0;transition:opacity .3s;font-size:.85rem;font-weight:600;letter-spacing:.05em}}
.product-card:hover .product-overlay{{opacity:1}}
.product-body{{padding:1.15rem}}
.stars{{color:#fbbf24;font-size:.75rem;letter-spacing:.1em;margin-bottom:.35rem}}
.product-body h3{{font-size:1rem;font-weight:600;margin-bottom:.5rem}}
.price-row{{display:flex;align-items:baseline;gap:.5rem}}
.price{{font-family:var(--font-display);font-size:1.2rem;font-weight:700;color:var(--accent2)}}
.price-old{{font-size:.85rem;color:var(--muted);text-decoration:line-through}}
.badge{{position:absolute;top:1rem;left:1rem;z-index:2;background:var(--accent);color:#fff;font-size:.65rem;font-weight:700;padding:.3rem .65rem;border-radius:999px;text-transform:uppercase}}

.banner-cta{{background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 25%,var(--surface)),var(--surface2))}}
.banner-inner{{display:flex;align-items:center;justify-content:space-between;gap:2rem;flex-wrap:wrap;padding:2.5rem;border:1px solid var(--border);border-radius:1.25rem}}
.banner-inner code{{background:rgba(255,255,255,.1);padding:.2rem .5rem;border-radius:.35rem;font-size:.95em}}

.testimonials{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1.25rem}}
.testimonials blockquote{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:1.75rem}}
.testimonials p{{font-size:.95rem;line-height:1.7;margin-bottom:1rem;font-style:italic;color:#e5e5e5}}
.testimonials footer{{font-size:.8rem;color:var(--muted);font-weight:600}}

.faq-grid{{display:grid;grid-template-columns:1fr 1.5fr;gap:3rem;align-items:start}}
.faq-list details{{border-bottom:1px solid var(--border);padding:1rem 0}}
.faq-list summary{{cursor:pointer;font-weight:600;list-style:none;display:flex;justify-content:space-between}}
.faq-list summary::after{{content:'+';color:var(--accent2)}}
.faq-list details[open] summary::after{{content:'−'}}
.faq-list p{{color:var(--muted);font-size:.9rem;margin-top:.75rem;padding-right:2rem}}

.newsletter-box{{text-align:center;max-width:520px;margin:0 auto}}
.newsletter-box h2{{font-family:var(--font-display);font-size:2rem;margin-bottom:.5rem}}
.newsletter-form{{display:flex;gap:.75rem;margin-top:1.5rem;flex-wrap:wrap}}
.newsletter-form input{{flex:1;min-width:200px;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:.9rem 1.1rem;border-radius:999px;font:inherit}}

.footer{{border-top:1px solid var(--border);padding:3rem 0 1.5rem;margin-top:2rem;background:var(--surface)}}
.footer-grid{{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:2rem;margin-bottom:2rem}}
.footer-brand p{{color:var(--muted);font-size:.88rem;margin-top:.75rem;max-width:28ch}}
.footer h4{{font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:1rem;color:var(--muted)}}
.footer a{{display:block;font-size:.88rem;color:var(--text);margin-bottom:.5rem;opacity:.8}}
.footer a:hover{{opacity:1;color:var(--accent2)}}
.footer-bottom{{padding-top:1.5rem;border-top:1px solid var(--border);font-size:.8rem;color:var(--muted)}}

.cart-drawer{{position:fixed;top:0;right:0;width:min(400px,100vw);height:100vh;background:var(--surface);border-left:1px solid var(--border);z-index:200;transform:translateX(100%);transition:transform .35s cubic-bezier(.4,0,.2,1);display:flex;flex-direction:column}}
.cart-drawer.open{{transform:translateX(0)}}
.cart-header{{display:flex;justify-content:space-between;align-items:center;padding:1.25rem 1.5rem;border-bottom:1px solid var(--border)}}
.cart-header h2{{font-family:var(--font-display);font-size:1.25rem}}
#cart-close{{background:none;border:none;color:var(--text);font-size:1.75rem;cursor:pointer;line-height:1}}
.cart-items{{flex:1;overflow-y:auto;padding:1rem 1.5rem;list-style:none}}
.cart-items li{{display:flex;justify-content:space-between;padding:.75rem 0;border-bottom:1px solid var(--border);font-size:.9rem}}
.cart-footer{{padding:1.25rem 1.5rem;border-top:1px solid var(--border)}}
.cart-total{{margin-bottom:1rem;font-size:1rem}}
.cart-backdrop{{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:199;opacity:0;pointer-events:none;transition:opacity .3s}}
.cart-backdrop.open{{opacity:1;pointer-events:auto}}

.toast{{position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%) translateY(120%);background:var(--surface2);border:1px solid var(--border);padding:.85rem 1.5rem;border-radius:999px;font-size:.88rem;opacity:0;transition:.35s;z-index:300;box-shadow:var(--shadow)}}
.toast.show{{transform:translateX(-50%) translateY(0);opacity:1}}

@media(max-width:900px){{
  .collection-grid{{grid-template-columns:1fr;min-height:auto}}
  .collection-large{{grid-row:auto}}
  .footer-grid{{grid-template-columns:1fr 1fr}}
  .faq-grid{{grid-template-columns:1fr}}
}}
@media(max-width:768px){{
  .menu-toggle{{display:flex}}
  .nav{{position:fixed;inset:3.2rem 0 auto 0;background:var(--surface);flex-direction:column;padding:1.5rem;gap:1rem;transform:translateY(-120%);transition:.3s;border-bottom:1px solid var(--border)}}
  .nav.open{{transform:translateY(0)}}
  .btn-ghost{{margin-left:0;margin-top:.75rem}}
  .hero-trust{{gap:1.5rem}}
}}
"""


JS_TEMPLATE = """(() => {
  const STORAGE = 'cart_v2';
  let cart = JSON.parse(localStorage.getItem(STORAGE) || '[]');
  const $ = (s) => document.querySelector(s);
  const countEl = $('#cart-count');
  const itemsEl = $('#cart-items');
  const totalEl = $('#cart-total');
  const drawer = $('#cart-drawer');
  const backdrop = $('#cart-backdrop');
  const toast = $('#toast');

  function fmt(n) { return n.toFixed(2).replace('.', ',') + ' €'; }

  function renderCart() {
    if (countEl) countEl.textContent = String(cart.length);
    if (!itemsEl) return;
    itemsEl.innerHTML = cart.length
      ? cart.map((i) => `<li><span>${i.name}</span><strong>${fmt(i.price)}</strong></li>`).join('')
      : '<li style="color:var(--muted)">Panier vide</li>';
    const sum = cart.reduce((a, b) => a + b.price, 0);
    if (totalEl) totalEl.textContent = fmt(sum);
    localStorage.setItem(STORAGE, JSON.stringify(cart));
  }

  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2800);
  }

  function openCart() {
    drawer?.classList.add('open');
    backdrop?.classList.add('open');
    drawer?.setAttribute('aria-hidden', 'false');
  }
  function closeCart() {
    drawer?.classList.remove('open');
    backdrop?.classList.remove('open');
    drawer?.setAttribute('aria-hidden', 'true');
  }

  document.querySelectorAll('[data-add]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const name = btn.getAttribute('data-add');
      const price = parseFloat(btn.getAttribute('data-price') || '0');
      cart.push({ name, price, at: Date.now() });
      renderCart();
      showToast(name + ' ajouté');
    });
  });

  $('#cart-btn')?.addEventListener('click', openCart);
  $('#cart-close')?.addEventListener('click', closeCart);
  backdrop?.addEventListener('click', closeCart);
  $('#checkout-btn')?.addEventListener('click', () => {
    if (!cart.length) { showToast('Panier vide'); return; }
    showToast('Commande demo — branchez Stripe pour production');
  });

  document.querySelectorAll('.cat-pill').forEach((pill) => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.cat-pill').forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');
      const f = pill.dataset.filter;
      document.querySelectorAll('.product-card').forEach((card) => {
        const cat = (card.dataset.cat || '').toLowerCase();
        const show = f === 'tout' || f === 'nouveautés' || f === 'promo' || f === 'exclusif'
          || cat.includes(f) || f.includes(cat.slice(0, 4));
        card.classList.toggle('hidden', !show && f !== 'tout');
      });
    });
  });

  $('#menu-toggle')?.addEventListener('click', () => $('#nav')?.classList.toggle('open'));
  $('#newsletter-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    showToast('Bienvenue ! Code WELCOME15 activé.');
    e.target.reset();
  });

  renderCart();
})();
"""


def build_sales_site(brief: str) -> dict:
    cfg = _parse_brief(brief)
    return {
        "ok": True,
        "title": cfg["raw_title"],
        "files": {
            "index.html": _render_html(cfg),
            "style.css": _css(cfg["accent"], cfg["accent2"]),
            "script.js": JS_TEMPLATE,
        },
    }


# ── Marketplace achat-revente (Vinted / LeBonCoin) ──────────────────────────

_MARKETPLACE_LISTINGS = [
    {"title": "Nike Air Max 90", "price": "45", "seller": "Léa_M", "city": "Paris 11e", "img": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=500&q=80", "cat": "mode", "size": "39", "likes": 24, "cond": "Très bon état"},
    {"title": "Veste en jean Levi's", "price": "28", "seller": "Tom_92", "city": "Lyon", "img": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500&q=80", "cat": "mode", "size": "M", "likes": 11, "cond": "Bon état"},
    {"title": "iPhone 13 128 Go", "price": "320", "seller": "MarieTech", "city": "Bordeaux", "img": "https://images.unsplash.com/photo-1592286923188-0d4f5a9c0e0a?w=500&q=80", "cat": "tech", "size": "", "likes": 56, "cond": "Comme neuf"},
    {"title": "Canapé 3 places gris", "price": "180", "seller": "Julie_Home", "city": "Nantes", "img": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=500&q=80", "cat": "maison", "size": "", "likes": 8, "cond": "Bon état"},
    {"title": "PlayStation 5 + 2 manettes", "price": "380", "seller": "GamerX", "city": "Lille", "img": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=500&q=80", "cat": "loisirs", "size": "", "likes": 42, "cond": "Très bon état"},
    {"title": "Robe Zara neuve", "price": "22", "seller": "Chloé_V", "city": "Marseille", "img": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500&q=80", "cat": "mode", "size": "S", "likes": 19, "cond": "Neuf avec étiquette"},
    {"title": "Vélo ville Decathlon", "price": "95", "seller": "Pierre_B", "city": "Toulouse", "img": "https://images.unsplash.com/photo-1485965120188-e496f3752776?w=500&q=80", "cat": "sport", "size": "", "likes": 15, "cond": "Bon état"},
    {"title": "MacBook Air M1 2020", "price": "520", "seller": "DevShop", "city": "Paris 15e", "img": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500&q=80", "cat": "tech", "size": "", "likes": 73, "cond": "Très bon état"},
    {"title": "Baskets Adidas Stan Smith", "price": "35", "seller": "Nina_S", "city": "Strasbourg", "img": "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=500&q=80", "cat": "mode", "size": "38", "likes": 9, "cond": "Bon état"},
    {"title": "Table basse scandinave", "price": "55", "seller": "Deco_Luc", "city": "Rennes", "img": "https://images.unsplash.com/photo-1532372320572-cda25653a26d?w=500&q=80", "cat": "maison", "size": "", "likes": 6, "cond": "Bon état"},
    {"title": "Appareil photo Canon EOS", "price": "290", "seller": "PhotoMax", "city": "Nice", "img": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=500&q=80", "cat": "loisirs", "size": "", "likes": 31, "cond": "Très bon état"},
    {"title": "Pull cachemire Uniqlo", "price": "18", "seller": "Emma_W", "city": "Grenoble", "img": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=500&q=80", "cat": "mode", "size": "L", "likes": 5, "cond": "Comme neuf"},
]


def _parse_marketplace_brief(brief: str) -> dict:
    t = (brief or "").lower()
    has_vinted = "vinted" in t
    has_lbc = "leboncoin" in t or "le bon coin" in t
    if has_vinted and not has_lbc:
        title, accent, accent2 = "Vinted", "#09b1ba", "#1ccad8"
    elif has_lbc and not has_vinted:
        title, accent, accent2 = "LeBonCoin", "#ff6e14", "#ff8c42"
    elif has_vinted or has_lbc:
        title, accent, accent2 = "ReMarket", "#09b1ba", "#6366f1"
    else:
        title, accent, accent2 = "ReMarket", "#09b1ba", "#6366f1"
    return {
        "title": escape(title),
        "raw_title": title,
        "slug": re.sub(r"[^a-z0-9]", "", title.lower()) or "market",
        "accent": accent,
        "accent2": accent2,
        "year": "2026",
        "listings": _MARKETPLACE_LISTINGS,
    }


def _listing_card(item: dict, i: int) -> str:
    size = f'<span class="listing-size">Taille {escape(item["size"])}</span>' if item.get("size") else ""
    return f"""<article class="listing-card" data-cat="{escape(item['cat'])}" data-id="{i}" data-title="{escape(item['title'].lower())}">
  <a href="#" class="listing-media" data-open="{i}">
    <img src="{item['img']}" alt="{escape(item['title'])}" loading="lazy" width="300" height="360" />
    <button type="button" class="like-btn" data-like="{i}" aria-label="Ajouter aux favoris">♡</button>
  </a>
  <div class="listing-body">
    <div class="listing-meta"><span class="listing-price">{escape(item['price'])} €</span>{size}</div>
    <h3><a href="#" data-open="{i}">{escape(item['title'])}</a></h3>
    <p class="listing-cond">{escape(item.get('cond', ''))}</p>
    <div class="listing-seller">
      <span class="avatar">{escape(item['seller'][:1].upper())}</span>
      <span>{escape(item['seller'])} · {escape(item['city'])}</span>
    </div>
  </div>
</article>"""


def _render_marketplace_html(cfg: dict) -> str:
    cards = "\n".join(_listing_card(it, i) for i, it in enumerate(cfg["listings"]))
    cats = [
        ("all", "Tout voir"),
        ("mode", "Mode"),
        ("tech", "High-Tech"),
        ("maison", "Maison"),
        ("loisirs", "Loisirs"),
        ("sport", "Sport"),
    ]
    cat_btns = "".join(
        f'<button type="button" class="cat-pill{" active" if k == "all" else ""}" data-filter="{k}">{label}</button>'
        for k, label in cats
    )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="Achat-revente entre particuliers — annonces, messagerie, paiement sécurisé." />
  <title>{cfg["title"]} — Achat & revente</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="header">
    <div class="container header-inner">
      <a href="#" class="logo">{cfg["title"]}</a>
      <form class="search-bar" id="search-form" role="search">
        <input type="search" id="search-input" placeholder="Rechercher une annonce…" aria-label="Rechercher" />
        <button type="submit" class="btn btn-primary btn-sm">Rechercher</button>
      </form>
      <nav class="nav" id="nav">
        <a href="#annonces">Annonces</a>
        <a href="#vendre">Vendre</a>
        <a href="#messages">Messages</a>
        <a href="#profil">Profil</a>
      </nav>
      <div class="header-actions">
        <button type="button" class="btn btn-sell" id="sell-btn">+ Vendre</button>
        <button type="button" class="icon-btn" id="fav-btn" aria-label="Favoris">♡ <span id="fav-count">0</span></button>
        <button type="button" class="menu-toggle" id="menu-toggle" aria-label="Menu"><span></span><span></span></button>
      </div>
    </div>
  </header>

  <main>
    <section class="hero-market">
      <div class="container hero-market-inner">
        <div>
          <p class="eyebrow">Entre particuliers · 0 % commission</p>
          <h1>Achetez & revendez<br /><span class="accent-text">en toute confiance.</span></h1>
          <p class="hero-lead">Publiez une annonce en 2 min, discutez avec les acheteurs, expédiez avec suivi.</p>
          <div class="hero-cta">
            <button type="button" class="btn btn-primary btn-lg" id="hero-sell">Déposer une annonce</button>
            <a href="#annonces" class="btn btn-ghost btn-lg">Parcourir</a>
          </div>
        </div>
        <div class="hero-stats">
          <div><strong>2,4M</strong><span>Annonces actives</span></div>
          <div><strong>98 %</strong><span>Avis positifs</span></div>
          <div><strong>24h</strong><span>Paiement sécurisé</span></div>
        </div>
      </div>
    </section>

    <section id="annonces" class="section">
      <div class="container">
        <div class="section-head">
          <h2>Dernières annonces</h2>
          <p class="sub">Filtrez par catégorie ou recherchez un article précis</p>
        </div>
        <div class="cat-bar">{cat_btns}</div>
        <div class="listing-grid" id="listing-grid">
{cards}
        </div>
        <p class="empty-state" id="empty-state" hidden>Aucune annonce ne correspond à votre recherche.</p>
      </div>
    </section>

    <section id="vendre" class="section section-alt">
      <div class="container sell-grid">
        <div>
          <p class="eyebrow">Vendre</p>
          <h2>3 étapes pour vendre</h2>
          <ol class="steps">
            <li><strong>Photo + description</strong> — Ajoutez 4 photos minimum et le prix souhaité.</li>
            <li><strong>Discussion</strong> — Répondez aux messages des acheteurs intéressés.</li>
            <li><strong>Expédition</strong> — Étiquette prépayée ou remise en main propre.</li>
          </ol>
        </div>
        <form class="sell-form" id="sell-form">
          <h3>Nouvelle annonce</h3>
          <label>Titre<input type="text" name="title" placeholder="Ex: Veste Nike taille M" required /></label>
          <label>Prix (€)<input type="number" name="price" min="1" placeholder="25" required /></label>
          <label>Catégorie
            <select name="cat" required>
              <option value="mode">Mode</option><option value="tech">High-Tech</option>
              <option value="maison">Maison</option><option value="loisirs">Loisirs</option><option value="sport">Sport</option>
            </select>
          </label>
          <label>Description<textarea name="desc" rows="3" placeholder="État, défauts, dimensions…"></textarea></label>
          <button type="submit" class="btn btn-primary btn-block">Publier l'annonce</button>
        </form>
      </div>
    </section>

    <section id="messages" class="section">
      <div class="container">
        <h2>Messagerie</h2>
        <div class="chat-layout">
          <aside class="chat-list">
            <button type="button" class="chat-thread active" data-thread="0"><span class="avatar">L</span><div><strong>Léa_M</strong><p>Nike Air Max — toujours dispo ?</p></div></button>
            <button type="button" class="chat-thread" data-thread="1"><span class="avatar">T</span><div><strong>Tom_92</strong><p>Je peux passer ce soir</p></div></button>
            <button type="button" class="chat-thread" data-thread="2"><span class="avatar">M</span><div><strong>MarieTech</strong><p>iPhone — batterie à combien % ?</p></div></button>
          </aside>
          <div class="chat-panel">
            <div class="chat-header"><span class="avatar">L</span><strong id="chat-name">Léa_M</strong></div>
            <div class="chat-messages" id="chat-messages">
              <div class="msg them">Salut ! La Nike Air Max est toujours dispo ?</div>
              <div class="msg me">Oui ! Très bon état, portées 3 fois. 45 € + livraison.</div>
              <div class="msg them">Parfait, je prends. Tu envoies avec suivi ?</div>
            </div>
            <form class="chat-input" id="chat-form">
              <input type="text" placeholder="Écrire un message…" required />
              <button type="submit" class="btn btn-primary btn-sm">Envoyer</button>
            </form>
          </div>
        </div>
      </div>
    </section>

    <section id="profil" class="section section-alt">
      <div class="container profile-card">
        <div class="profile-head">
          <span class="profile-avatar">H</span>
          <div><h2>Mon profil</h2><p>Membre depuis 2024 · ★ 4,9 (127 avis)</p></div>
        </div>
        <div class="profile-stats">
          <div><strong>12</strong><span>Annonces</span></div>
          <div><strong>48</strong><span>Ventes</span></div>
          <div><strong>23</strong><span>Achats</span></div>
        </div>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="container footer-bottom"><p>© {cfg["year"]} {cfg["title"]} — Démo achat-revente (HTML/CSS/JS statique).</p></div>
  </footer>

  <dialog class="modal" id="listing-modal">
    <button type="button" class="modal-close" id="modal-close" aria-label="Fermer">×</button>
    <div class="modal-body" id="modal-body"></div>
  </dialog>
  <div class="toast" id="toast" role="status"></div>
  <script src="script.js"></script>
</body>
</html>"""


def _marketplace_css(accent: str, accent2: str) -> str:
    return f""":root {{
  --accent: {accent}; --accent2: {accent2}; --bg: #f4f6f8; --surface: #fff;
  --surface2: #eef1f4; --border: #e2e8f0; --text: #0f172a; --muted: #64748b;
  --font: 'Plus Jakarta Sans', system-ui, sans-serif; --radius: 14px;
  --shadow: 0 12px 40px rgba(15,23,42,.08);
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.55}}
img{{max-width:100%;display:block}}
a{{color:inherit;text-decoration:none}}
.container{{width:min(1180px,94vw);margin:0 auto}}
.header{{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}}
.header-inner{{display:flex;align-items:center;gap:1rem;padding:.85rem 0;flex-wrap:wrap}}
.logo{{font-weight:800;font-size:1.35rem;color:var(--accent)}}
.search-bar{{flex:1;display:flex;gap:.5rem;min-width:200px}}
.search-bar input{{flex:1;border:1px solid var(--border);border-radius:999px;padding:.65rem 1rem;font:inherit}}
.nav{{display:flex;gap:1.25rem}}
.nav a{{font-size:.88rem;color:var(--muted);font-weight:600}}
.nav a:hover{{color:var(--text)}}
.header-actions{{display:flex;align-items:center;gap:.5rem;margin-left:auto}}
.btn{{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;padding:.65rem 1.25rem;border-radius:999px;font-weight:700;font-size:.88rem;border:none;cursor:pointer;font-family:inherit;transition:transform .15s,box-shadow .15s}}
.btn:hover{{transform:translateY(-1px)}}
.btn-sm{{padding:.5rem 1rem;font-size:.82rem}}
.btn-lg{{padding:.9rem 1.6rem}}
.btn-primary{{background:var(--accent);color:#fff;box-shadow:0 6px 20px color-mix(in srgb,var(--accent) 35%,transparent)}}
.btn-ghost{{background:var(--surface);border:1px solid var(--border);color:var(--text)}}
.btn-sell{{background:var(--accent2);color:#fff}}
.btn-block{{width:100%}}
.icon-btn{{background:var(--surface2);border:1px solid var(--border);border-radius:999px;padding:.45rem .85rem;cursor:pointer;font:inherit}}
.menu-toggle{{display:none;flex-direction:column;gap:4px;background:none;border:none;padding:8px;cursor:pointer}}
.menu-toggle span{{width:20px;height:2px;background:var(--text);border-radius:2px}}
.hero-market{{background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 12%,#fff),#fff);padding:3rem 0}}
.hero-market-inner{{display:grid;grid-template-columns:1.4fr 1fr;gap:2rem;align-items:center}}
.hero-market h1{{font-size:clamp(2rem,5vw,3rem);font-weight:800;line-height:1.1;margin:.75rem 0}}
.accent-text{{color:var(--accent)}}
.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:.68rem;font-weight:700;color:var(--accent)}}
.hero-lead{{color:var(--muted);max-width:48ch;margin-bottom:1.5rem}}
.hero-cta{{display:flex;flex-wrap:wrap;gap:.75rem}}
.hero-stats{{display:grid;gap:1rem}}
.hero-stats div{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem;box-shadow:var(--shadow)}}
.hero-stats strong{{display:block;font-size:1.6rem;font-weight:800}}
.hero-stats span{{font-size:.78rem;color:var(--muted)}}
.section{{padding:3.5rem 0}}
.section-alt{{background:var(--surface)}}
.section-head{{margin-bottom:1.5rem}}
.section-head h2{{font-size:1.75rem;font-weight:800}}
.section-head .sub{{color:var(--muted)}}
.cat-bar{{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1.5rem}}
.cat-pill{{border:1px solid var(--border);background:var(--surface);color:var(--muted);padding:.4rem .95rem;border-radius:999px;font:inherit;font-size:.82rem;cursor:pointer}}
.cat-pill.active,.cat-pill:hover{{background:var(--accent);border-color:var(--accent);color:#fff}}
.listing-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:1rem}}
.listing-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;transition:box-shadow .2s,transform .2s}}
.listing-card:hover{{box-shadow:var(--shadow);transform:translateY(-3px)}}
.listing-media{{position:relative;display:block;aspect-ratio:4/5;overflow:hidden;background:var(--surface2)}}
.listing-media img{{width:100%;height:100%;object-fit:cover}}
.like-btn{{position:absolute;top:.6rem;right:.6rem;width:34px;height:34px;border-radius:50%;border:none;background:rgba(255,255,255,.92);cursor:pointer;font-size:1.1rem}}
.listing-body{{padding:.85rem}}
.listing-price{{font-weight:800;font-size:1.05rem;color:var(--accent)}}
.listing-size{{font-size:.72rem;color:var(--muted);margin-left:.5rem}}
.listing-body h3{{font-size:.92rem;margin:.35rem 0;font-weight:700}}
.listing-cond{{font-size:.75rem;color:var(--muted)}}
.listing-seller{{display:flex;align-items:center;gap:.45rem;margin-top:.55rem;font-size:.78rem;color:var(--muted)}}
.avatar{{width:26px;height:26px;border-radius:50%;background:var(--accent);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700}}
.sell-grid{{display:grid;grid-template-columns:1fr 1fr;gap:2rem;align-items:start}}
.steps{{margin-top:1rem;padding-left:1.2rem;color:var(--muted)}}
.steps li{{margin-bottom:.75rem}}
.sell-form{{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);padding:1.5rem;display:grid;gap:.75rem}}
.sell-form label{{display:grid;gap:.3rem;font-size:.82rem;font-weight:600}}
.sell-form input,.sell-form select,.sell-form textarea{{border:1px solid var(--border);border-radius:10px;padding:.6rem .75rem;font:inherit}}
.chat-layout{{display:grid;grid-template-columns:280px 1fr;gap:1rem;margin-top:1rem;min-height:320px}}
.chat-list{{display:grid;gap:.35rem}}
.chat-thread{{display:flex;gap:.65rem;text-align:left;border:1px solid var(--border);background:var(--surface);border-radius:12px;padding:.75rem;cursor:pointer;font:inherit}}
.chat-thread.active{{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 8%,#fff)}}
.chat-thread p{{font-size:.78rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.chat-panel{{border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);display:grid;grid-template-rows:auto 1fr auto}}
.chat-header{{padding:.85rem 1rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:.5rem}}
.chat-messages{{padding:1rem;display:grid;gap:.6rem;align-content:start;max-height:280px;overflow:auto}}
.msg{{max-width:78%;padding:.55rem .85rem;border-radius:14px;font-size:.88rem}}
.msg.them{{background:var(--surface2);justify-self:start}}
.msg.me{{background:var(--accent);color:#fff;justify-self:end}}
.chat-input{{display:flex;gap:.5rem;padding:.75rem;border-top:1px solid var(--border)}}
.chat-input input{{flex:1;border:1px solid var(--border);border-radius:999px;padding:.55rem .85rem;font:inherit}}
.profile-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.5rem}}
.profile-head{{display:flex;gap:1rem;align-items:center}}
.profile-avatar{{width:56px;height:56px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.4rem;font-weight:800}}
.profile-stats{{display:flex;gap:2rem;margin-top:1.25rem}}
.profile-stats strong{{display:block;font-size:1.4rem}}
.profile-stats span{{font-size:.78rem;color:var(--muted)}}
.footer{{padding:2rem 0;color:var(--muted);font-size:.82rem}}
.modal{{border:none;border-radius:var(--radius);padding:0;max-width:520px;width:92vw;box-shadow:var(--shadow)}}
.modal::backdrop{{background:rgba(15,23,42,.45)}}
.modal-close{{position:absolute;top:.5rem;right:.75rem;border:none;background:none;font-size:1.6rem;cursor:pointer}}
.modal-body{{padding:1.25rem}}
.toast{{position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%) translateY(120%);background:var(--text);color:#fff;padding:.7rem 1.2rem;border-radius:999px;font-size:.85rem;transition:transform .25s;z-index:200}}
.toast.show{{transform:translateX(-50%) translateY(0)}}
.empty-state{{text-align:center;color:var(--muted);padding:2rem}}
@media(max-width:900px){{
  .hero-market-inner,.sell-grid,.chat-layout{{grid-template-columns:1fr}}
  .nav{{display:none;position:absolute;top:100%;left:0;right:0;background:var(--surface);flex-direction:column;padding:1rem;border-bottom:1px solid var(--border)}}
  .nav.open{{display:flex}}
  .menu-toggle{{display:flex}}
}}
"""


MARKETPLACE_JS = r"""
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const toast = $('#toast');
  const showToast = (m) => { if (!toast) return; toast.textContent = m; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 2600); };

  const LISTINGS = """ + json.dumps(_MARKETPLACE_LISTINGS, ensure_ascii=False) + r""";

  let favorites = new Set();

  function filterListings(cat, q) {
    const query = (q || '').trim().toLowerCase();
    let visible = 0;
    $$('.listing-card').forEach((card) => {
      const matchCat = cat === 'all' || card.dataset.cat === cat;
      const matchQ = !query || (card.dataset.title || '').includes(query);
      const show = matchCat && matchQ;
      card.hidden = !show;
      if (show) visible++;
    });
    const empty = $('#empty-state');
    if (empty) empty.hidden = visible > 0;
  }

  $$('.cat-pill').forEach((btn) => btn.addEventListener('click', () => {
    $$('.cat-pill').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    filterListings(btn.dataset.filter, $('#search-input')?.value);
  }));

  $('#search-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const active = $('.cat-pill.active');
    filterListings(active?.dataset.filter || 'all', $('#search-input')?.value);
  });

  $$('[data-like]').forEach((btn) => btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const id = btn.dataset.like;
    if (favorites.has(id)) { favorites.delete(id); btn.textContent = '♡'; }
    else { favorites.add(id); btn.textContent = '♥'; showToast('Ajouté aux favoris'); }
    const fc = $('#fav-count');
    if (fc) fc.textContent = String(favorites.size);
  }));

  const modal = $('#listing-modal');
  const openModal = (id) => {
    const item = LISTINGS[Number(id)];
    if (!item || !modal) return;
    $('#modal-body').innerHTML = `
      <img src="${item.img}" alt="${item.title}" style="width:100%;border-radius:12px;margin-bottom:1rem" />
      <h2>${item.title}</h2>
      <p style="font-size:1.4rem;font-weight:800;color:var(--accent);margin:.5rem 0">${item.price} €</p>
      <p>${item.cond} · ${item.seller} · ${item.city}</p>
      <button type="button" class="btn btn-primary btn-block" style="margin-top:1rem" onclick="document.getElementById('listing-modal').close();document.getElementById('messages').scrollIntoView()">Contacter le vendeur</button>`;
    modal.showModal();
  };
  $$('[data-open]').forEach((el) => el.addEventListener('click', (e) => { e.preventDefault(); openModal(el.dataset.open); }));
  $('#modal-close')?.addEventListener('click', () => modal?.close());

  const scrollSell = () => document.getElementById('vendre')?.scrollIntoView({ behavior: 'smooth' });
  $('#sell-btn')?.addEventListener('click', scrollSell);
  $('#hero-sell')?.addEventListener('click', scrollSell);

  $('#sell-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    showToast('Annonce publiée (démo) — connecte un backend pour la persistance.');
    e.target.reset();
  });

  const threads = {
    0: { name: 'Léa_M', msgs: ['Salut ! La Nike Air Max est toujours dispo ?', 'Oui ! Très bon état. 45 € + livraison.', 'Parfait, je prends.'] },
    1: { name: 'Tom_92', msgs: ['Je peux passer ce soir vers 19h ?', 'Oui, je suis dispo Place Bellecour.', 'Super, à tout à l\'heure !'] },
    2: { name: 'MarieTech', msgs: ['iPhone — batterie à combien % ?', '87 % selon Réglages.', 'OK, je prends à 320 €'] },
  };
  $$('.chat-thread').forEach((btn) => btn.addEventListener('click', () => {
    $$('.chat-thread').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    const t = threads[btn.dataset.thread];
    if (!t) return;
    $('#chat-name').textContent = t.name;
    $('#chat-messages').innerHTML = t.msgs.map((m, i) =>
      `<div class="msg ${i % 2 ? 'me' : 'them'}">${m}</div>`).join('');
  }));

  $('#chat-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const input = e.target.querySelector('input');
    const text = input?.value?.trim();
    if (!text) return;
    $('#chat-messages')?.insertAdjacentHTML('beforeend', `<div class="msg me">${text}</div>`);
    input.value = '';
    showToast('Message envoyé (démo)');
  });

  $('#menu-toggle')?.addEventListener('click', () => $('#nav')?.classList.toggle('open'));
})();
"""


def build_marketplace_site(brief: str) -> dict:
    cfg = _parse_marketplace_brief(brief)
    return {
        "ok": True,
        "title": cfg["raw_title"],
        "files": {
            "index.html": _render_marketplace_html(cfg),
            "style.css": _marketplace_css(cfg["accent"], cfg["accent2"]),
            "script.js": MARKETPLACE_JS,
        },
    }
