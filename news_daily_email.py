#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
News Daily (multi-source) + Email
- Sources: Convergência Digital, TechTudo, Olhar Digital, Exame/Tech
- Filters: Segurança da Informação, Cloud, Hackers, Infraestrutura
- Output: HTML named dailysummaryTI_YYYY-MM-DD_HHMM.html
- Email: sends HTML inline to the recipient from .env

Usage:
  python news_daily_email.py [output_dir]

ENV (.env in same folder or OS env):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_FROM, MAIL_TO
  (optional) TIMEOUT, MAX_LINKS_PER_SOURCE
"""
import os, re, sys, ssl, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ---------------------------- Config ----------------------------
SOURCES = [
    "https://convergenciadigital.com.br/",
    "https://www.techtudo.com.br/",
    "https://olhardigital.com.br/",
    "https://exame.com/tecnologia/",
]

KEYWORDS = {
    "Segurança da Informação": [
        "cibersegurança", "segurança da informação", "ransomware", "vazamento",
        "lgpd", "ddos", "phishing", "malware", "vulnerabilidade", "zero-day",
        "honeypot", "ameaça", "botnet", "exploit", "autenticação", "mfa", "2fa",
    ],
    "Cloud": [
        "cloud", "nuvem", "aws", "azure", "gcp", "kubernetes", "container",
        "devops", "terraform", "iac", "serverless", "compute", "s3", "ec2",
    ],
    "Hackers": [
        "hacker", "ataque", "invasão", "invasores", "black hat", "grupo", "gangue",
        "lockbit", "lazarus", "ransom", "crackers", "defacement",
    ],
    "Infraestrutura": [
        "infraestrutura", "data center", "datacenter", "rede", "redes", "backbone",
        "fibra", "5g", "edge", "latência", "disponibilidade", "resiliência",
    ],
}

USER_AGENT = "Mozilla/5.0 (compatible; NewsDailyAgent/1.0)"

def env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

MAX_LINKS_PER_SOURCE = env_int("MAX_LINKS_PER_SOURCE", 30)
TIMEOUT = env_int("TIMEOUT", 20)

# ------------------------ Helper functions ----------------------
def http_get(url):
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def extract_links_from_home(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    links = set()
    base_host = urlparse(base_url).netloc.replace("www.", "")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        netloc = urlparse(full).netloc.replace("www.", "")
        if netloc.endswith(base_host):
            links.add(full.split("#")[0])
    return list(links)

def clean_text(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def get_title_and_body(url, html):
    soup = BeautifulSoup(html, "lxml")
    # Title
    title = soup.find("h1")
    title = clean_text(title.get_text(" ")) if title else (clean_text(soup.title.get_text(" ")) if soup.title else "Sem título")
    # Body candidates
    selectors = [
        "article",
        "div[itemprop='articleBody']",
        "div.td-post-content",
        "div.entry-content",
        "div.post-content",
        "section.article-content",
        "div#js-article-content",
        "div.content",
        "main",
    ]
    candidates = []
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            candidates.append(el.get_text(" "))
    body = clean_text(max(candidates, key=len) if candidates else "")
    return title, body

def categorize(title, body):
    text = f"{title}\n{body}".lower()
    for cat, words in KEYWORDS.items():
        for w in words:
            if w.lower() in text:
                return cat
    return None

def summarize(text, max_chars=600):
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    short = " ".join(parts[:4]).strip()
    return (short[: max_chars - 1] + "…") if len(short) > max_chars else short

def hostname(url):
    return urlparse(url).netloc.replace("www.", "")

def generate_html(items):
    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H%M")
    filename = f"dailysummaryTI_{stamp}.html"

    def esc(s): 
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    cards = []
    for i, it in enumerate(items, 1):
        cards.append(f"""
        <div class="card">
          <h2>{i}. {esc(it['title'])} <span class="badge">{esc(it['category'])}</span></h2>
          <p><strong>Fonte:</strong> {esc(it['source'])} — <a href="{it['url']}" target="_blank" rel="noopener">Abrir link</a></p>
          <p>{esc(it['summary'])}</p>
        </div>
        """)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resumo Diário – {now.strftime('%d/%m/%Y')}</title>
  <style>
    body{{font-family:Arial,Helvetica,sans-serif;line-height:1.6;color:#111;margin:0;background:#f9fafb}}
    .container{{max-width:900px;margin:0 auto;padding:32px}}
    h1{{font-size:28px;margin:0 0 8px}}
    .date{{color:#555;margin-bottom:24px}}
    h2{{font-size:20px;margin-top:24px}}
    .card{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
    .badge{{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:9999px;padding:4px 10px;font-size:12px;margin-left:6px}}
    a{{text-decoration:none}}
    a:hover{{text-decoration:underline}}
    .footer{{font-size:12px;color:#6b7280;margin-top:24px}}
  </style>
</head>
<body>
  <div class="container">
    <h1>Resumo Diário — Tecnologia e Segurança</h1>
    <div class="date">{now.strftime('%d/%m/%Y %H:%M')}</div>
    {''.join(cards) if cards else '<p><em>Nenhum item relevante encontrado hoje.</em></p>'}
    <div class="footer">
      <p>Gerado automaticamente em {now.strftime('%d/%m/%Y %H:%M')} — arquivo: {filename}</p>
    </div>
  </div>
</body>
</html>"""
    return filename, html

def crawl_and_summarize():
    items = []
    seen = set()
    for src in SOURCES:
        try:
            home = http_get(src).text
        except Exception:
            continue
        links = extract_links_from_home(home, src)[:MAX_LINKS_PER_SOURCE]
        for url in links:
            if url in seen:
                continue
            seen.add(url)
            # skip non-article-ish
            if any(x in url for x in ["/tag/", "/tags/", "/autor/", "/sobre/", "/contato/", "/newsletter/", "/login/"]):
                continue
            try:
                art = http_get(url).text
            except Exception:
                continue
            title, body = get_title_and_body(url, art)
            if not title or not body:
                continue
            cat = categorize(title, body)
            if not cat:
                continue
            summary = summarize(f"{title}. {body}")
            items.append({
                "title": title,
                "url": url,
                "summary": summary,
                "category": cat,
                "source": hostname(src),
            })
    items.sort(key=lambda x: (x["category"], x["source"], x["title"]))
    return items

def send_email(html_path: Path):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    mail_from = os.getenv("MAIL_FROM", smtp_user or "bot@example.com")
    mail_to = os.getenv("MAIL_TO", "albert.godinho@tailor.com.br")

    html = Path(html_path).read_text(encoding="utf-8")
    subject = f"[Resumo Diário] {Path(html_path).stem}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.attach(MIMEText("Segue o resumo diário em HTML.", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=ctx)
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, [mail_to], msg.as_string())

def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)
    items = crawl_and_summarize()
    filename, html = generate_html(items)
    html_path = out_dir / filename
    html_path.write_text(html, encoding="utf-8")
    # send email
    send_email(html_path)
    print(f"Gerado e enviado: {html_path}")

if __name__ == "__main__":
    main()
