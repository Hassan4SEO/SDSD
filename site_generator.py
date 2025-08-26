#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# site_generator.py  — multi-language static(PHP) site generator with SEO features
#
# Usage examples:
#   python3 site_generator.py --output . --total 2000 --batch 1000 --internal 40 --ext-min 150 --ext-max 200
#
# Features:
# - Multi-language (ar, en, fr) with hreflang alternates
# - Time-based URLs: /{lang}/{yyyy}/{mm}/page-{id}.php
# - Multiple templates, TOC, Breadcrumbs, JSON-LD (Article + Breadcrumb + FAQ)
# - Dynamic titles/descriptions from keywords.txt (if present)
# - Heavy interlinking (internal) + external links (tunable)
# - Categories/Tags/Hub pages, Archive pages, Home page listing all posts per language
# - RSS feeds, robots.txt, improved sitemaps with index + priority/changefreq (+ image entries)
# - Random authors/dates, rich media (Unsplash images, optional YouTube embed)
# - CSS themes (light/dark/colorful)
# - Gzip (and Brotli if available)
# - Checkpoint/resume

import os, sys, argparse, random, uuid, json, gzip, shutil, html, math
from pathlib import Path
from datetime import datetime, timedelta
from time import sleep
from urllib.parse import quote_plus

# ---------------- DEFAULTS ----------------
DEFAULT_OUTPUT = "."
DEFAULT_TOTAL   = 1000
DEFAULT_BATCH   = 1000
FILES_PER_FOLDER = 2000
SITEMAP_URLS_LIMIT = 50000
BASE_URL = "https://lyrics.trustdealzz.com"   # change if needed

LANGS = ["ar","en","fr"]
LANG_HTML = {"ar":"ar","en":"en","fr":"fr"}
DIR_ATTR  = {"ar":"rtl","en":"ltr","fr":"ltr"}

# Load external sources (subset of your big list; you can extend safely)
EXTERNAL_SOURCES = [
    "https://wikipedia.org","https://bbc.com","https://cnn.com","https://nytimes.com","https://reuters.com",
    "https://theverge.com","https://wired.com","https://arstechnica.com","https://techradar.com","https://cnet.com",
    "https://forbes.com","https://wsj.com","https://ft.com","https://economist.com","https://investopedia.com",
    "https://who.int","https://cdc.gov","https://mayoclinic.org","https://nih.gov","https://thelancet.com",
    "https://espn.com","https://uefa.com","https://fifa.com","https://olympics.com","https://mlb.com",
    "https://vogue.com","https://gq.com","https://tripadvisor.com","https://lonelyplanet.com","https://timeout.com",
    "https://nasa.gov","https://esa.int","https://nature.com","https://scientificamerican.com","https://space.com",
    "https://github.blog","https://developer.mozilla.org","https://producthunt.com","https://engadget.com","https://venturebeat.com",
    "https://aljazeera.net","https://alarabiya.net","https://arabic.cnn.com","https://youm7.com","https://almasryalyoum.com",
    "https://lemonde.fr","https://lefigaro.fr","https://20minutes.fr","https://bfmtv.com","https://ouest-france.fr"
]

ANCHORS_EN = ["Read more","See details","Discover more","Explore now","Full guide","Learn more","Open article"]
ANCHORS_AR = ["اقرأ التفاصيل","شاهد المزيد","تعرّف أكثر","اكتشف الآن","الدليل الكامل","المزيد","افتح المقال"]
ANCHORS_FR = ["En savoir plus","Voir détails","Découvrez plus","Explorer","Guide complet","En lire plus","Ouvrir l'article"]

THEMES = ["light","dark","colorful"]
YOUTUBE_IDS = ["dQw4w9WgXcQ","9bZkp7q19f0","Zi_XLOBDo_Y","3JZ_D3ELwOQ","kXYiU_JCYtU"]  # sample

AUTHORS_AR = ["أحمد علي","محمد سمير","ليلى حسن","سارة محمود","نور الدين"]
AUTHORS_EN = ["John Carter","Emily Stone","Alex Morgan","Sarah Lee","David Kim"]
AUTHORS_FR = ["Jean Dupont","Marie Curie","Luc Martin","Camille Bernard","Sophie Laurent"]

CATEGORIES = {
    "ar": [("تقنية","ذكاء-اصطناعي"),("صحة","لياقة"),("سفر","وجهات"),("أعمال","تسويق"),("تعليم","مهارات")],
    "en": [("Technology","AI"),("Health","Fitness"),("Travel","Destinations"),("Business","Marketing"),("Education","Skills")],
    "fr": [("Technologie","IA"),("Santé","Fitness"),("Voyage","Destinations"),("Business","Marketing"),("Éducation","Compétences")]
}

TAG_BANK = {
    "ar": ["تقنية","تعليم","أعمال","سفر","صحة","أمن سيبراني","ذكاء اصطناعي","تسويق رقمي","طبخ","رياضة"],
    "en": ["tech","education","business","travel","health","cybersecurity","ai","digital-marketing","cooking","sports"],
    "fr": ["tech","éducation","business","voyage","santé","cybersécurité","ia","marketing","cuisine","sport"]
}

SAMPLE_PARAGRAPHS = {
    "ar":[
        "في هذا الدليل سنعرض أفكارًا عملية وسريعة التطبيق. نستخدم أمثلة حقيقية ونصائح مختصين.",
        "ينصح الخبراء بالبدء بخطوات صغيرة، وقياس النتائج، ثم التطوير بشكل تدريجي.",
        "تأكّد من مراجعة المصادر الموثوقة قبل اتخاذ أي قرار، وجرّب الأدوات المذكورة."
    ],
    "en":[
        "This guide outlines practical ideas you can apply today, backed by credible sources.",
        "Experts recommend starting small, measuring impact, then iterating for continuous improvement.",
        "Always validate with trusted references before decisions and test the mentioned tools."
    ],
    "fr":[
        "Ce guide présente des idées pratiques à appliquer dès aujourd'hui, appuyées par des sources fiables.",
        "Les experts conseillent de commencer petit, mesurer l'impact, puis itérer pour s'améliorer.",
        "Vérifiez toujours avec des références de confiance et testez les outils évoqués."
    ]
}

SYNONYMS = {
    "ar":{"أفضل":["أحسن","أكثر فاعلية"],"دليل":["مرشد","مرجع"],"طرق":["وسائل","أساليب"]},
    "en":{"best":["great","top"],"guide":["handbook","primer"],"ways":["methods","tactics"]},
    "fr":{"meilleures":["top","excellentes"],"guide":["manuel","référence"],"méthodes":["façons","techniques"]}
}

# ------------- UTILITIES -------------
def ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)

def read_keywords():
    here = Path(__file__).resolve().parent
    f = here / "keywords.txt"
    if f.exists():
        kws = [x.strip() for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        random.shuffle(kws)
        return kws
    # fallback short bank
    return [
        "artificial intelligence","digital marketing","healthy recipes","travel hacks","financial freedom",
        "productivity tips","cybersecurity basics","fitness routine","remote work","python tutorials",
        "apprentissage automatique","marketing numérique","recettes saines","voyage pas cher","liberté financière",
        "تسويق رقمي","ذكاء اصطناعي","وصفات صحية","خدع السفر","الحرية المالية"
    ]

def rand_date():
    # random date between 2018-01-01 and 2025-12-31
    start = datetime(2018,1,1)
    end   = datetime(2025,12,31)
    delta = end - start
    d = start + timedelta(days=random.randint(0, delta.days))
    # modified after published by 0..240 days
    m = d + timedelta(days=random.randint(0,240))
    return d, m

def choose_author(lang):
    return random.choice({"ar":AUTHORS_AR,"en":AUTHORS_EN,"fr":AUTHORS_FR}[lang])

def choose_theme():
    return random.choice(THEMES)

def spin_text(lang, text):
    bank = SYNONYMS.get(lang,{})
    for k,vals in bank.items():
        if random.random()<0.5:
            text = text.replace(k, random.choice(vals))
    return text

def make_paragraph(lang, min_words=60, max_words=120):
    target = random.randint(min_words, max_words)
    s = []
    while len(" ".join(s).split()) < target:
        s.append(random.choice(SAMPLE_PARAGRAPHS[lang]))
    text = spin_text(lang, " ".join(s))

    # ✅ إدخال لينك داخلي عشوائي جوا الفانكشن
    if planner and planner.by_lang_index.get(lang):
        art = random.choice(planner.by_lang_index[lang])
        link = f'<a href="/{art["rel"]}">{html.escape(art["keyword"])}</a>'
        words = text.split()
        if len(words) > 5:
            pos = random.randint(3, len(words)-2)
            words.insert(pos, link)
            text = " ".join(words)

    return text


def make_sections(lang):
    # returns list of (h2, [h3s])
    h2_count = random.randint(3,4)
    sections=[]
    for i in range(1,h2_count+1):
        h2 = {"ar":f"الجزء {i}","en":f"Section {i}","fr":f"Section {i}"}[lang]
        h3s=[]
        for j in range(1,random.randint(2,4)):
            h3s.append({"ar":f"نقطة {i}.{j}","en":f"Point {i}.{j}","fr":f"Point {i}.{j}"}[lang])
        sections.append((h2,h3s))
    return sections

def toc_html(sections):
    items=[]
    idx=1
    for (h2,h3s) in sections:
        items.append(f'<li><a href="#sec{idx}">{html.escape(h2)}</a></li>')
        idx+=1
    return '<div class="toc"><h3>Table of Contents</h3><ul>'+"\n".join(items)+'</ul></div>'

def youtube_embed():
    vid = random.choice(YOUTUBE_IDS)
    return f'<div class="yt"><iframe width="560" height="315" src="https://www.youtube.com/embed/{vid}" title="YouTube video" frameborder="0" allowfullscreen loading="lazy"></iframe></div>'

def unsplash_img(keyword, alt):
    q = quote_plus(keyword)
    # source.unsplash.com returns random image for the query without API key
    src = f"https://source.unsplash.com/800x450/?{q}"
    return f'<figure><img src="{src}" alt="{html.escape(alt)}" loading="lazy"><figcaption>{html.escape(alt)}</figcaption></figure>', src

def anchor_for(lang):
    return random.choice({"ar":ANCHORS_AR,"en":ANCHORS_EN,"fr":ANCHORS_FR}[lang])

def gzip_file(path):
    gz = path + ".gz"
    with open(path,"rb") as f_in, gzip.open(gz,"wb",compresslevel=6) as f_out:
        shutil.copyfileobj(f_in,f_out)
    return gz

def brotli_file(path):
    try:
        import brotli
    except Exception:
        return None
    br = path + ".br"
    data = Path(path).read_bytes()
    Path(br).write_bytes(brotli.compress(data, quality=5))
    return br

def minify_html(s):
    # safe light minify
    s = "\n".join([l.strip() for l in s.splitlines()])
    s = s.replace("> <", "><")
    return s

# ------------- META + JSON-LD -------------
def build_meta(title, desc, url, published, modified, canonical, og_image, lang, hreflangs):
    meta = []
    meta.append(f"<title>{html.escape(title)}</title>")
    meta.append(f'<meta name="description" content="{html.escape(desc)}">')
    meta.append(f'<link rel="canonical" href="{canonical}">')
    # hreflang alternates
    for hl_url, hl_code in hreflangs:
        meta.append(f'<link rel="alternate" hreflang="{hl_code}" href="{hl_url}">')
    # OG/Twitter
    meta += [
        f'<meta property="og:title" content="{html.escape(title)}">',
        f'<meta property="og:description" content="{html.escape(desc)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:type" content="article">',
        f'<meta property="og:image" content="{og_image}">',
        f'<meta name="twitter:card" content="summary_large_image">'
    ]
    # article times
    meta += [
        f'<meta property="article:published_time" content="{published}"/>',
        f'<meta property="article:modified_time" content="{modified}"/>'
    ]
    return "\n".join(meta)

def jsonld_article(title, author, pub_iso, mod_iso, url):
    data = {
        "@context":"https://schema.org","@type":"Article",
        "headline": title,
        "author": {"@type":"Person","name": author},
        "datePublished": pub_iso, "dateModified": mod_iso,
        "mainEntityOfPage": url
    }
    return '<script type="application/ld+json">'+json.dumps(data, ensure_ascii=False)+'</script>'

def jsonld_breadcrumb(crumbs):
    # crumbs: list of (name,url)
    items=[]
    for i,(name,url) in enumerate(crumbs, start=1):
        items.append({"@type":"ListItem","position":i,"name":name,"item":url})
    data={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":items}
    return '<script type="application/ld+json">'+json.dumps(data, ensure_ascii=False)+'</script>'

def jsonld_website():
    data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "url": BASE_URL,
        "potentialAction": {
            "@type": "SearchAction",
            "target": BASE_URL + "/search?q={search_term_string}",
            "query-input": "required name=search_term_string"
        }
    }
    return '<script type="application/ld+json">'+json.dumps(data, ensure_ascii=False)+'</script>'

def jsonld_faq(lang, keyword):
    # 1-3 Q&A simple
    Q = {
        "ar":[
            ("ما هي أهم النقاط المرتبطة بـ "+keyword+"؟","تشمل أفضل الممارسات، الأدوات، وخطوات البداية المنظمة."),
            ("كيف أبدأ في "+keyword+"؟","ابدأ بخطوات صغيرة، قِس النتائج، ثم طوّر نهجك تدريجيًا."),
        ],
        "en":[
            ("What is important about "+keyword+"?","Best practices, tools, and a structured way to begin."),
            ("How to get started with "+keyword+"?","Start small, measure results, and iterate regularly."),
        ],
        "fr":[
            ("Qu'est-ce qui est important pour "+keyword+" ?","Bonnes pratiques, outils, et une approche progressive."),
            ("Comment débuter avec "+keyword+" ?","Commencez petit, mesurez les résultats et itérez."),
        ]
    }
    pairs=random.sample(Q[lang], k=random.randint(1,2))
    main=[]
    for q,a in pairs:
        main.append({"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}})
    data={"@context":"https://schema.org","@type":"FAQPage","mainEntity":main}
    return '<script type="application/ld+json">'+json.dumps(data, ensure_ascii=False)+'</script>'

# ------------- TEMPLATES -------------
def template_article_v1(lang, title, byline, toc, body_html, media_html, related_html, tags_html, pager_html, breadcrumbs_html, ld_json):
    return f"""
<article class="v1" itemscope itemtype="https://schema.org/Article">
{breadcrumbs_html}
<header><h1 itemprop="name">{html.escape(title)}</h1>{byline}</header>
{media_html}
{toc}
<section itemprop="articleBody">{body_html}</section>
{tags_html}
{pager_html}
<section class="related"><h3>{_t(lang,'related')}</h3>{related_html}</section>
{ld_json}
</article>
"""

def template_article_v2(lang, title, byline, toc, body_html, media_html, related_html, tags_html, pager_html, breadcrumbs_html, ld_json):
    return f"""
<article class="v2" itemscope itemtype="https://schema.org/Article">
{breadcrumbs_html}
<header><h1 itemprop="name">{html.escape(title)}</h1>{byline}</header>
{toc}
{media_html}
<section itemprop="articleBody">{body_html}</section>
{tags_html}
{pager_html}
<section><h3>{_t(lang,'related')}</h3>{related_html}</section>
{ld_json}
</article>
"""

def template_listicle(lang, title, byline, toc, items_html, media_html, related_html, tags_html, pager_html, breadcrumbs_html, ld_json):
    return f"""
<article class="listicle" itemscope itemtype="https://schema.org/Article">
{breadcrumbs_html}
<header><h1 itemprop="name">{html.escape(title)}</h1>{byline}</header>
{media_html}
{toc}
<section itemprop="articleBody">
<ol class="listicle-items">
{items_html}
</ol>
</section>
{tags_html}
{pager_html}
<section><h3>{_t(lang,'related')}</h3>{related_html}</section>
{ld_json}
</article>
"""

def _t(lang, key):
    T = {
        "by_en":"By","by_ar":"بواسطة","by_fr":"Par",
        "related":{"ar":"روابط ذات صلة","en":"Related","fr":"Liés"},
        "home":{"ar":"الصفحة الرئيسية","en":"Home","fr":"Accueil"},
        "tags":{"ar":"الوسوم","en":"Tags","fr":"Tags"},
        "prev":{"ar":"السابق","en":"« Prev","fr":"« Préc."},
        "next":{"ar":"التالي","en":"Next »","fr":"Suiv. »"},
        "all_posts":{"ar":"كل المقالات","en":"All Articles","fr":"Tous les articles"}
    }
    if key=="by":
        return {"ar":T["by_ar"],"en":T["by_en"],"fr":T["by_fr"]}[lang]
    if key in T:
        v=T[key]
        return v[lang] if isinstance(v,dict) else v
    return key

# ------------- CORE PLANNER -------------
class Planner:
    """
    Precompute metadata for all pages for each language:
    - keyword, title, description
    - dates, author
    - category/subcategory
    - tags
    - URL path (lang/year/mm/page-id.php)
    So prev/next are guaranteed to exist (no 404).
    """
    def __init__(self, total, output_root):
        self.total = total
        self.output_root = output_root
        self.keywords = read_keywords()
        self.plan = {lang:{} for lang in LANGS}  # plan[lang][id] -> dict
        self.by_lang_index = {lang:[] for lang in LANGS}
        self._build()
        self.by_lang_cat = {lang:{} for lang in LANGS}  # by category

    def _kw_for(self, idx):
        return self.keywords[idx % len(self.keywords)]

    def _title_for(self, lang, kw):
        year = random.randint(2020,2025)
        if lang=="en":
            patterns = [f"Top {random.randint(7,17)} ways to {kw} in {year}",
                        f"Ultimate guide to {kw}",
                        f"{kw.title()}: Tips, tools and tactics"]
        elif lang=="fr":
            patterns = [f"Top {random.randint(7,17)} façons de {kw} en {year}",
                        f"Guide ultime de {kw}",
                        f"{kw.title()}: Conseils et outils"]
        else:
            patterns = [f"أفضل {random.randint(7,17)} طرق لـ {kw} في {year}",
                        f"الدليل الشامل حول {kw}",
                        f"{kw}: نصائح وأدوات"]
        return random.choice(patterns)

    def _desc_for(self, lang, kw):
        base = {
            "en": f"Quick, practical overview about {kw} with real examples and references.",
            "fr": f"Aperçu pratique et rapide de {kw} avec des exemples concrets.",
            "ar": f"ملخص عملي وسريع حول {kw} مع أمثلة واقعية ومراجع."
        }[lang]
        return base[:160]

class Planner:
    def __init__(self, total):
        self.total = total
        self.plan = {lang:{} for lang in LANGS}
        self.by_lang_cat = {lang:{} for lang in LANGS}
        self.by_lang_index = {lang:[] for lang in LANGS}

    def _build(self):
        for lang in LANGS:
            for i in range(1, self.total+1):
                kw = self._kw_for(i)
                title = self._title_for(lang, kw)
                desc = self._desc_for(lang, kw)
                pub_dt, mod_dt = rand_date()
                author = choose_author(lang)
                cat, sub = self._cat_for(lang)
                tags = self._tags_for(lang)
                rel = self._slug_path(lang, pub_dt, i)
                url = f"{BASE_URL}/{rel}"
                self.plan[lang][i] = {
                    "keyword": kw, "title": title, "description": desc,
                    "published": pub_dt, "modified": mod_dt,
                    "author": author, "category": cat, "subcategory": sub,
                    "tags": tags, "rel": rel, "url": url, "lang":lang, "id":i
                }

                # ✅ الفهرسة هنا
                key = (cat, sub)
                self.by_lang_cat[lang].setdefault(key, []).append(self.plan[lang][i])
                self.by_lang_index[lang].append(self.plan[lang][i])

def main():
    args = parse_args()
    planner = Planner(args.total)
    planner._build()

    # --- كتابة المقالات ---
    for lang in LANGS:
        for i, art in planner.plan[lang].items():
            write_article_page(args.output, art)

    # --- كتابة الصفحات الخاصة بالأقسام ---
    for lang in LANGS:
        for (cat, sub), articles in planner.by_lang_cat[lang].items():
            write_category_page(args.output, lang, cat, sub, articles)

# ------------- PAGE GENERATION -------------
def header_php(theme):
    return f"""<?php // header.php (generated) ?>
<!doctype html>
<html lang="{{lang}}" dir="{{dir}}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/assets/style-{theme}.css">
</head>
<body>
<header class="site-header">
  <div class="container">
    <h1><a href="/">lyrics.trustdealzz.com</a></h1>
    <nav class="main-nav">
      <a href="/">{html.escape('Home')}</a>
      <a href="/archive/index.php">Archive</a>
      <a href="/sitemaps/sitemap_index.xml">Sitemaps</a>
      <a href="/rss/index.xml">RSS</a>
    </nav>
  </div>
</header>
<main class="container">
"""

def footer_php():
    year = datetime.utcnow().year
    return f"""
</main>
<footer class="site-footer">
  <div class="container">
    <p>&copy; {year} TrustDealzz — Generated content for testing purposes.</p>
    <nav class="footer-nav">
      <a href="/privacy.php">Privacy</a> · <a href="/robots.txt">robots.txt</a> · <a href="/404.php">404</a>
    </nav>
  </div>
</footer>
</body>
</html>
"""

def base_css(theme):
    # minimal clean styling; three variants
    common = """
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial}
.container{max-width:1100px;margin:0 auto;padding:16px}
.site-header,.site-footer{padding:12px 0}
.main-nav a,.footer-nav a{margin-right:12px;text-decoration:none}
article h1{font-size:2rem;margin:.2rem 0 1rem}
article .toc{background:var(--card);padding:12px;border-radius:12px;margin:16px 0}
article figure{margin:16px 0}
.breadcrumbs{font-size:.9rem;margin:6px 0 16px}
.pager{margin:20px 0}
.tags a{display:inline-block;margin-right:8px}
.grid{display:grid;gap:16px}
.home-grid{grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.card{background:var(--card);padding:12px;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
ul.inline{list-style:none;padding:0;margin:0}
ul.inline li{display:inline-block;margin-right:8px}
h3{margin-top:1.2rem}
table{border-collapse:collapse;width:100%;margin:12px 0}
td,th{border:1px solid var(--border);padding:8px}
"""
    if theme=="light":
        vars = ":root{--bg:#f8fafc;--fg:#0f172a;--card:#ffffff;--border:#e5e7eb} body{background:var(--bg);color:var(--fg)} a{color:#0ea5e9}"
    elif theme=="dark":
        vars = ":root{--bg:#0b1220;--fg:#e5e7eb;--card:#121a2b;--border:#1f2937} body{background:var(--bg);color:var(--fg)} a{color:#60a5fa}"
    else:
        vars = ":root{--bg:#fff7ed;--fg:#1f2937;--card:#fffbeb;--border:#fed7aa} body{background:var(--bg);color:var(--fg)} a{color:#f97316}"
    return vars + common

def write_assets(root):
    assets = os.path.join(root,"assets")
    ensure_dir(assets)
    for t in THEMES:
        Path(os.path.join(assets,f"style-{t}.css")).write_text(base_css(t), encoding="utf-8")

def write_shared_php(root, theme_choice="light"):
    # global header/footer once per language runtime (we inject lang into include)
    Path(os.path.join(root,"header.php")).write_text(header_php(theme_choice), encoding="utf-8")
    Path(os.path.join(root,"footer.php")).write_text(footer_php(), encoding="utf-8")

def breadcrumbs_html(lang, crumbs):
    parts=[]
    parts.append(f'<nav class="breadcrumbs"><a href="/">{_t(lang,"home")}</a> › ')
    links=[]
    for name,url in crumbs[:-1]:
        links.append(f'<a href="{url}">{html.escape(name)}</a>')
    last = html.escape(crumbs[-1][0])
    parts.append(" › ".join(links + [f"<span>{last}</span>"]))
    parts.append("</nav>")
    return "".join(parts)

def byline_html(lang, author, pub_dt):
    d = pub_dt.strftime({"ar":"%d %B %Y","en":"%d %B %Y","fr":"%d %B %Y"}[lang])
    return f'<p class="byline">{_t(lang,"by")} <strong>{html.escape(author)}</strong> — {d}</p>'

def tags_html(lang, tags):
    links = " ".join([f'<a href="/{lang}/tags/{quote_plus(t)}/">#{html.escape(t)}</a>' for t in tags])
    return f'<aside class="tags"><strong>{_t(lang,"tags")}:</strong> {links}</aside>'

def write_category_page(root, lang, category, subcategory, articles):
    """توليد صفحة قسم مع روابط المقالات"""
    ensure_dir(os.path.join(root, lang, "category", quote_plus(category)))
    path = os.path.join(root, lang, "category", quote_plus(category), "index.php")

    links_html = "<ul>"
    for art in articles:
        links_html += f'<li><a href="/{art["rel"]}">{html.escape(art["title"])}</a></li>'
    links_html += "</ul>"

    html_out = f"""<?php include_once($_SERVER['DOCUMENT_ROOT'].'/header.php'); ?>
<h1>{html.escape(category)} / {html.escape(subcategory)}</h1>
{links_html}
<?php include_once($_SERVER['DOCUMENT_ROOT'].'/footer.php'); ?>
"""
    Path(path).write_text(minify_html(html_out), encoding="utf-8")
    return path

def pager_html(lang, prev_url, next_url):
    prev = f'<a href="{prev_url}">{_t(lang,"prev")}</a>' if prev_url else ""
    nxt  = f'<a href="{next_url}">{_t(lang,"next")}</a>' if next_url else ""
    mid = " | " if prev and nxt else ""
    return f'<div class="pager">{prev}{mid}{nxt}</div>'

# ------------- LINK GRAPH -------------
def build_internal_links(planner, lang, page_id, per_page=100):
    # pick from same lang except self; mixture of close ids + random
    ids = list(range(1, planner.total+1))
    ids.remove(page_id)
    close = [i for i in range(max(1,page_id-10), min(planner.total,page_id+10)+1) if i!=page_id]
    pool = list(set(random.sample(ids, k=min(len(ids), per_page//2)) + random.sample(close, k=min(len(close), per_page//2))))
    random.shuffle(pool)
    items=[]
    for i in pool[:per_page]:
        u = planner.plan[lang][i]["url"]
        text = anchor_for(lang)
        items.append(f'<li><a href="{u}">{html.escape(text)}</a></li>')
    return "<ul>"+ "".join(items) + "</ul>"

def build_external_links(ext_min, ext_max, keyword):
    n = random.randint(ext_min, min(ext_max, len(EXTERNAL_SOURCES)))
    sample = random.sample(EXTERNAL_SOURCES, k=n)
    items=[]
    for u in sample:
        label = u.replace("https://","").replace("http://","")[:60]
        items.append(f'<li><a rel="nofollow noopener noreferrer" target="_blank" href="{u}">{html.escape(label)}</a></li>')
    # add a couple keyword-based Google queries (no-follow)
    q = quote_plus(keyword)
    items.append(f'<li><a rel="nofollow noopener" target="_blank" href="https://www.google.com/search?q={q}">Google: {html.escape(keyword)}</a></li>')
    return "<ul>"+"".join(items)+"</ul>"

# ------------- PAGE WRITER -------------
def write_article_page(root, planner, lang, page_id, internal_n, ext_min, ext_max, shared_header_rel):
    p = planner.plan[lang][page_id]
    pub_iso = p["published"].strftime("%Y-%m-%dT00:00:00Z")
    mod_iso = p["modified"].strftime("%Y-%m-%dT00:00:00Z")
    rel = p["rel"]
    fullpath = os.path.join(root, rel)
    ensure_dir(os.path.dirname(fullpath))
# --- Generate article pages ---
for lang in LANGS:
    for art in planner.by_lang[lang]:
        write_article_page(args.output, lang, art)

# --- Generate category pages ---
for lang in LANGS:
    for (cat, sub), articles in planner.by_lang_cat[lang].items():
        write_category_page(args.output, lang, cat, sub, articles)

    # Hreflang alternates
    hreflangs=[]
    for L in LANGS:
        hreflangs.append((planner.plan[L][page_id]["url"], L))
    # Meta
    img_html, img_src = unsplash_img(p["keyword"], p["title"])
    meta = build_meta(p["title"], p["description"], p["url"], pub_iso, mod_iso, p["url"], img_src, lang, hreflangs)

    # Breadcrumbs
    crumbs = [
        (_t(lang,"home"), f"{BASE_URL}/"),
        (p["category"], f"{BASE_URL}/{lang}/category/{quote_plus(p['category'])}/"),
        (p["subcategory"], f"{BASE_URL}/{lang}/category/{quote_plus(p['category'])}/{quote_plus(p['subcategory'])}/"),
        (p["title"], p["url"]),
    ]
    bch_html = breadcrumbs_html(lang, [(c[0], c[1]) for c in crumbs])

    # Body (sections + TOC)
    sections = make_sections(lang)
    toc = toc_html(sections)
    body_parts=[]
    sec_idx=1
    for (h2,h3s) in sections:
        body_parts.append(f'<h2 id="sec{sec_idx}">{html.escape(h2)}</h2>')
        # paragraph under H2
        body_parts.append("<p>"+html.escape(make_paragraph(lang,120,180))+"</p>")
        for h3 in h3s:
            body_parts.append(f"<h3>{html.escape(h3)}</h3>")
            # random: paragraph or table block
            if random.random()<0.8:
                body_parts.append("<p>"+html.escape(make_paragraph(lang,70,120))+"</p>")
            else:
                # dynamic table block
                body_parts.append("<table><tr><th>Item</th><th>Value</th></tr>" +
                                  "".join([f"<tr><td>Option {i}</td><td>${random.randint(9,99)}</td></tr>" for i in range(1,1+random.randint(2,4))]) +
                                  "</table>")
        sec_idx+=1
    # listicle variant items (if used)
    listicle_items = "".join([f"<li>{html.escape(make_paragraph(lang,25,40))}</li>" for _ in range(random.randint(6,10))])

    # Related Internal / External
    related = build_internal_links(planner, lang, page_id, per_page=internal_n)
    external = build_external_links(ext_min, ext_max, p["keyword"])

    # Tags + Byline + Pager
    tags = tags_html(lang, p["tags"])
    byline = byline_html(lang, p["author"], p["published"])
    prev_url = planner.plan[lang][page_id-1]["url"] if page_id>1 else ""
    next_url = planner.plan[lang][page_id+1]["url"] if page_id<planner.total else ""
    pager = pager_html(lang, prev_url, next_url)

    # JSON-LD
    ld_article = jsonld_article(p["title"], p["author"], pub_iso, mod_iso, p["url"])
    ld_breadcrumb = jsonld_breadcrumb([(c[0],c[1]) for c in crumbs])
    ld_faq = jsonld_faq(lang, p["keyword"])
    ld_json = "\n".join([ld_article, ld_breadcrumb, ld_faq])

    # Choose template
    tpl = random.choice([template_article_v1, template_article_v2, template_listicle])
    if tpl==template_listicle:
        content_html = tpl(lang, p["title"], byline, toc, listicle_items, img_html + youtube_embed(), related, tags, pager, bch_html, ld_json)
    else:
        content_html = tpl(lang, p["title"], byline, toc, "\n".join(body_parts)+f"<h3>External References</h3>{external}", img_html, related, tags, pager, bch_html, ld_json)

    # PHP includes w/ lang injection
    include_prefix = os.path.relpath(root, start=os.path.dirname(fullpath)).replace(os.path.sep,"/")
    include_prefix = "" if include_prefix=="." else include_prefix+"/"
    html_page = f'''<?php $lang="{LANG_HTML[lang]}"; $dir="{DIR_ATTR[lang]}"; include("{include_prefix}header.php"); ?>
<head>
{meta}
</head>
{content_html}
<?php include("{include_prefix}footer.php"); ?>'''

    # write file (minify then compress)
    Path(fullpath).write_text(minify_html(html_page))
    gzip_file(fullpath)
# brotli skipped for speed
    return fullpath, img_src

    
# ------------- LISTING PAGES (HOME / HUB / TAG / ARCHIVE) -------------
def write_home(root, planner):
    # main home at /index.php listing language portals + latest posts (per lang)
    ensure_dir(root)
    theme = choose_theme()
    write_shared_php(root, theme_choice=theme)
    write_assets(root)

    # language landing pages and main home cards
    cards=[]
    for lang in LANGS:
        latest = sorted(planner.by_lang_index[lang], key=lambda x: x["published"], reverse=True)[:20]
        lis="\n".join([f'<li><a href="{p["url"]}">{html.escape(p["title"])}</a></li>' for p in latest])
        # language landing
        lang_root = os.path.join(root, lang)
        ensure_dir(lang_root)
        include_prefix = ""  # header/footer at root
        lang_html = f'''<?php $lang="{LANG_HTML[lang]}"; $dir="{DIR_ATTR[lang]}"; include("{include_prefix}header.php"); ?>
<head><title>{_t(lang,"home")} — {lang.upper()}</title><meta name="description" content="Latest articles ({lang.upper()})"></head>
<h1>{_t(lang,"home")} ({lang.upper()})</h1>
<div class="grid home-grid">
{ "".join([f'<div class="card"><h3><a href="{p["url"]}">{html.escape(p["title"])}</a></h3><p>{html.escape(p["description"])}</p></div>' for p in latest]) }
</div>
<h2>{_t(lang,"all_posts")}</h2>
<ul>
{lis}
</ul>
<?php include("{include_prefix}footer.php"); ?>'''
        Path(os.path.join(lang_root,"index.php")).write_text(minify_html(lang_html), encoding="utf-8")
        gzip_file(os.path.join(lang_root,"index.php")); brotli_file(os.path.join(lang_root,"index.php"))

        cards.append(f'<div class="card"><h3><a href="/{lang}/">{lang.upper()} — {_t(lang,"home")}</a></h3><ul>{lis}</ul></div>')

    home = f'''<?php $lang="en"; $dir="ltr"; include("header.php"); ?>
<head><title>TrustDealzz — Home</title><meta name="description" content="All generated articles in AR, EN, FR"></head>
<h1>Welcome</h1>
<p>This is the main index linking literally to all article pages with names, plus language portals.</p>
<div class="grid home-grid">
{ "".join(cards) }
</div>
<section>
<h2>ALL ARTICLES (AR/EN/FR)</h2>
<ul>
{"".join([f'<li><a href="{p["url"]}">{html.escape(p["title"])}</a></li>' for lang in LANGS for p in sorted(planner.by_lang_index[lang], key=lambda x:x["id"])])}
</ul>
</section>
<?php include("footer.php"); ?>'''
    Path(os.path.join(root,"index.php")).write_text(minify_html(home), encoding="utf-8")
    gzip_file(os.path.join(root,"index.php")); brotli_file(os.path.join(root,"index.php"))

    # 404
    not_found = '''<?php $lang="en"; $dir="ltr"; include("header.php"); ?>
<head><title>404 Not Found</title><meta name="robots" content="noindex"></head>
<h1>404</h1>
<p>Sorry, page not found. Try one of these:</p>
<ul>
<?php
// quick links: latest EN
echo '<li><a href="/en/">English Home</a></li>';
echo '<li><a href="/ar/">Arabic Home</a></li>';
echo '<li><a href="/fr/">French Home</a></li>';
?>
</ul>
<?php include("footer.php"); ?>'''
    Path(os.path.join(root,"404.php")).write_text(minify_html(not_found), encoding="utf-8")

    # simple privacy
    privacy = '''<?php $lang="en"; $dir="ltr"; include("header.php"); ?>
<head><title>Privacy Policy</title></head>
<h1>Privacy Policy</h1>
<p>Generated test website. No real tracking.</p>
<?php include("footer.php"); ?>'''
    Path(os.path.join(root,"privacy.php")).write_text(minify_html(privacy), encoding="utf-8")

def write_hubs_tags_archives(root, planner):
    # HUBS by category/subcategory per language
    for lang in LANGS:
        # hubs
        for (cat, sub) in CATEGORIES[lang]:
            hub_dir = os.path.join(root, lang, "category", quote_plus(cat), quote_plus(sub))
            ensure_dir(hub_dir)
            pages = [p for p in planner.by_lang_index[lang] if p["category"]==cat and p["subcategory"]==sub]
            pages = sorted(pages, key=lambda x: x["published"], reverse=True)
            lis = "\n".join([f'<li><a href="{p["url"]}">{html.escape(p["title"])}</a></li>' for p in pages[:1000]])
            page = f'''<?php $lang="{LANG_HTML[lang]}"; $dir="{DIR_ATTR[lang]}"; include("{os.path.relpath(root, hub_dir).replace(os.path.sep,"/")}/header.php"); ?>
<head><title>{html.escape(cat)} / {html.escape(sub)}</title><meta name="description" content="{html.escape(cat)} - {html.escape(sub)} hub"></head>
<h1>{html.escape(cat)} › {html.escape(sub)}</h1>
<ul>{lis}</ul>
<?php include("{os.path.relpath(root, hub_dir).replace(os.path.sep,"/")}/footer.php"); ?>'''
            Path(os.path.join(hub_dir,"index.php")).write_text(minify_html(page), encoding="utf-8")

        # tags
        tag_dir = os.path.join(root, lang, "tags")
        ensure_dir(tag_dir)
        # collect tag -> pages
        tagmap={}
        for p in planner.by_lang_index[lang]:
            for t in p["tags"]:
                tagmap.setdefault(t,[]).append(p)
        for t, plist in tagmap.items():
            d = os.path.join(tag_dir, quote_plus(t))
            ensure_dir(d)
            lis = "\n".join([f'<li><a href="{pp["url"]}">{html.escape(pp["title"])}</a></li>' for pp in plist[:2000]])
            page = f'''<?php $lang="{LANG_HTML[lang]}"; $dir="{DIR_ATTR[lang]}"; include("{os.path.relpath(root, d).replace(os.path.sep,"/")}/header.php"); ?>
<head><title>#{html.escape(t)}</title><meta name="description" content="Tag: {html.escape(t)}"></head>
<h1>#{html.escape(t)}</h1>
<ul>{lis}</ul>
<?php include("{os.path.relpath(root, d).replace(os.path.sep,"/")}/footer.php"); ?>'''
            Path(os.path.join(d,"index.php")).write_text(minify_html(page), encoding="utf-8")

        # archives per year/month
        arch_root = os.path.join(root,"archive"); ensure_dir(arch_root)
        arch_lang_root = os.path.join(arch_root, lang); ensure_dir(arch_lang_root)
        by_ym={}
        for p in planner.by_lang_index[lang]:
            key = (p["published"].year, p["published"].month)
            by_ym.setdefault(key,[]).append(p)
        # per month page
        for (y,m), plist in by_ym.items():
            d = os.path.join(arch_lang_root, f"{y}", f"{m:02d}")
            ensure_dir(d)
            lis = "\n".join([f'<li><a href="{pp["url"]}">{html.escape(pp["title"])}</a></li>' for pp in sorted(plist, key=lambda x:x["id"])])
            page = f'''<?php $lang="{LANG_HTML[lang]}"; $dir="{DIR_ATTR[lang]}"; include("{os.path.relpath(root, d).replace(os.path.sep,"/")}/header.php"); ?>
<head><title>Archive {lang.upper()} — {y}-{m:02d}</title></head>
<h1>Archive {lang.upper()} — {y}-{m:02d}</h1>
<ul>{lis}</ul>
<?php include("{os.path.relpath(root, d).replace(os.path.sep,"/")}/footer.php"); ?>'''
            Path(os.path.join(d,"index.php")).write_text(minify_html(page), encoding="utf-8")

    # master archive index listing everything (root /archive/index.php)
    arch_index = os.path.join(root,"archive","index.php")
    ensure_dir(os.path.dirname(arch_index))
    big_list = "".join([f'<li><a href="{p["url"]}">{html.escape(p["title"])}</a></li>' for lang in LANGS for p in sorted(planner.by_lang_index[lang], key=lambda x:x["id"])])
    page = f'''<?php $lang="en"; $dir="ltr"; include("{os.path.relpath(root, os.path.join(root,'archive')).replace(os.path.sep,'/')}/header.php"); ?>
<head><title>Archive</title></head>
<h1>Archive</h1>
<ul>{big_list}</ul>
<?php include("{os.path.relpath(root, os.path.join(root,'archive')).replace(os.path.sep,'/')}/footer.php"); ?>'''
    Path(arch_index).write_text(minify_html(page), encoding="utf-8")

# ------------- RSS / ROBOTS / SITEMAPS -------------
def write_rss(root, planner):
    rss_dir = os.path.join(root,"rss"); ensure_dir(rss_dir)
    for lang in LANGS:
        items=[]
        latest = sorted(planner.by_lang_index[lang], key=lambda x:x["published"], reverse=True)[:100]
        for p in latest:
            pub = p["published"].strftime("%a, %d %b %Y 00:00:00 +0000")
            items.append(f"<item><title>{html.escape(p['title'])}</title><link>{p['url']}</link><guid>{p['url']}</guid><pubDate>{pub}</pubDate><description>{html.escape(p['description'])}</description></item>")
        rss = f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>TrustDealzz {lang.upper()}</title><link>{BASE_URL}/{lang}/</link><description>Latest {lang.upper()} posts</description>' + "".join(items) + "</channel></rss>"
        Path(os.path.join(rss_dir, f"{lang}.xml")).write_text(rss, encoding="utf-8")
    # index
    idx = '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>TrustDealzz RSS Index</title><link>'+BASE_URL+'/</link><description>All feeds</description>'
    for lang in LANGS:
        idx+= f'<item><title>{lang.upper()} Feed</title><link>{BASE_URL}/rss/{lang}.xml</link></item>'
    idx += "</channel></rss>"
    Path(os.path.join(rss_dir,"index.xml")).write_text(idx, encoding="utf-8")

def write_robots(root):
    robots = f"""User-agent: *
Allow: /
Sitemap: {BASE_URL}/sitemaps/sitemap_index.xml
"""
    Path(os.path.join(root,"robots.txt")).write_text(robots, encoding="utf-8")
    Path(os.path.join(root,"humans.txt")).write_text("Site: TrustDealzz Test\nGenerator: site_generator.py\n", encoding="utf-8")

def flush_sitemap_entries(sitemap_dir, count, entries):
    fname = os.path.join(sitemap_dir, f"sitemap-{count:03d}.xml")
    with open(fname,"w",encoding="utf-8") as sf:
        sf.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        sf.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n')
        for u, lastmod, prio, chgfreq, img in entries:
            sf.write("  <url>\n")
            sf.write(f"    <loc>{u}</loc>\n")
            sf.write(f"    <lastmod>{lastmod}</lastmod>\n")
            sf.write(f"    <priority>{prio}</priority>\n")
            sf.write(f"    <changefreq>{chgfreq}</changefreq>\n")
            if img:
                sf.write(f'    <image:image><image:loc>{img}</image:loc></image:image>\n')
            sf.write("  </url>\n")
        sf.write("</urlset>\n")
    return fname

def write_sitemaps(root, planner):
    sitemap_root = os.path.join(root, "sitemaps")
    ensure_dir(sitemap_root)
    all_urls = []
    for lang in LANGS:
        for art in planner.by_lang_index[lang]:
            all_urls.append(art["url"])

    # تقسيم الملفات 50,000 لينك في كل واحد
    chunks = [all_urls[i:i+SITEMAP_URLS_LIMIT] for i in range(0, len(all_urls), SITEMAP_URLS_LIMIT)]
    index_entries = []
    for idx, chunk in enumerate(chunks, start=1):
        sm_path = os.path.join(sitemap_root, f"sitemap-{idx:03d}.xml")
        with open(sm_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
            for url in chunk:
                f.write(f"<url><loc>{url}</loc></url>\n")
            f.write("</urlset>")
        index_entries.append(f"<sitemap><loc>{BASE_URL}/sitemaps/sitemap-{idx:03d}.xml</loc><lastmod>{datetime.utcnow().isoformat()}Z</lastmod></sitemap>")

    # كتابة index
    index_path = os.path.join(sitemap_root, "sitemap_index.xml")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        f.write("\n".join(index_entries))
        f.write("\n</sitemapindex>")

# ------------- MAIN GENERATION -------------
def generate_all(output_root, total, batch_size, files_per_folder, ext_min, ext_max, internal_links_count):
    # prep
    ensure_dir(output_root)
    write_assets(output_root)
    write_shared_php(output_root, theme_choice=choose_theme())
    write_robots(output_root)

    # plan all pages deterministically to avoid 404 in prev/next
    planner = Planner(total, output_root)

    # HOME/HUB/TAG/ARCHIVE will be written after articles
    # progress + checkpoint
    checkpoint = os.path.join(output_root, "generator_checkpoint.json")
    start_id = 1
    if os.path.exists(checkpoint):
        data = json.loads(Path(checkpoint).read_text(encoding="utf-8") or "{}")
        start_id = data.get("last_index", 0) + 1
        print(f"Resuming from id {start_id}")

    images_map = {}  # url -> image
    # write pages
    for pid in range(start_id, total+1):
        for lang in LANGS:
            fullpath, img = write_article_page(output_root, planner, lang, pid, internal_links_count, ext_min, ext_max, "header.php")
            images_map[planner.plan[lang][pid]["url"]] = img

        # checkpoint + soft sleep
        if pid % batch_size == 0:
            Path(checkpoint).write_text(json.dumps({"last_index": pid}, ensure_ascii=False), encoding="utf-8")
            print(f"Checkpoint at id={pid}")
            sleep(0.1)
        if pid % max(1,(batch_size//10 or 1)) == 0:
            print(f"Progress: {pid}/{total}")

    # supporting pages
    write_home(output_root, planner)
    write_hubs_tags_archives(output_root, planner)
    write_rss(output_root, planner)
    write_sitemaps(output_root, planner, images_map)
    write_sitemaps(args.output, planner)
    
    # done
    Path(checkpoint).write_text(json.dumps({"last_index": total}, ensure_ascii=False), encoding="utf-8")
    print("Generation complete.")

# ------------- CLI -------------
if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Mass multi-language static PHP site generator with SEO")
    parser.add_argument("--output","-o", default=DEFAULT_OUTPUT, help="Output root (e.g. /path)")
    parser.add_argument("--total","-t", type=int, default=DEFAULT_TOTAL, help="Number of article IDs (each generated in AR/EN/FR)")
    parser.add_argument("--batch","-b", type=int, default=DEFAULT_BATCH, help="Checkpoint batch size")
    parser.add_argument("--files-per-folder", type=int, default=FILES_PER_FOLDER, help="(kept for compatibility)")
    parser.add_argument("--ext-min", type=int, default=120, help="Min external links/page")
    parser.add_argument("--ext-max", type=int, default=220, help="Max external links/page")
    parser.add_argument("--internal", type=int, default=120, help="Internal links per page")
    
    args = parser.parse_args()

    OUTPUT = os.path.abspath(args.output)
    FILES_PER_FOLDER = args.files_per_folder

    if args.total >= 100000:
        print("⚠️ You are about to generate a very large number of pages per language.")
        print("Consider running with a smaller --total first to verify structure.")

    print(f"[INFO] Starting generation of {args.total} pages per language (AR/EN/FR)...")
    print(f"[INFO] Output directory: {OUTPUT}")
    print(f"[INFO] Batch size: {args.batch}")
    
    generate_all(OUTPUT, args.total, args.batch, FILES_PER_FOLDER, args.ext_min, args.ext_max, args.internal)
    
    print("[DONE] All pages generated successfully.")