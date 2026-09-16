#!/usr/bin/env python3
"""
fetch_page.py - Fetch a web page (or PDF) and save its readable text as evidence.

Standard library only for HTML. Optional extras:
  - PDF text:       pip install pypdf
  - JS-heavy pages: pip install playwright && playwright install chromium   (then use --browser)

For every URL it writes, under --out (default ./web-evidence):
  pages/<ID>.md    readable text with a metadata header (url, final_url, fetched_at, title, published, ...)
  pages/<ID>.json  the same metadata as JSON, plus quality flags
  raw/<ID>.html    the raw HTML/PDF (only with --raw)

and prints one JSON line per URL to stdout so the caller can read the flags:
  text_chars, truncated, looks_like_js_shell, looks_like_login_wall, looks_like_blocked, ...

--find "some sentence" checks whether that sentence appears in the extracted text
(whitespace/case-insensitive, and also sentence-by-sentence for partial matches).
Use it to verify that a quote you plan to cite really is on the page.

Usage:
  python fetch_page.py https://example.com/article --id S01 --out web-evidence
  python fetch_page.py https://example.com/article --find "the exact quote" --print
  python fetch_page.py https://spa.example.com/page --browser --id S02
  python fetch_page.py --file urls.txt --out web-evidence

Saving text to disk does NOT mean the model has read it. Open pages/<ID>.md
(or use --print) and actually read the relevant part before citing.
"""

import argparse
import difflib
import gzip
import html
import io
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone
from html.parser import HTMLParser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate",
}
MAX_BYTES = 8_000_000

SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "template", "iframe", "head"}
CHROME_TAGS = {"nav", "header", "footer", "aside", "form", "button", "menu", "dialog"}
BLOCK_TAGS = {"p", "div", "section", "article", "main", "li", "ul", "ol", "table", "tr", "br", "hr",
              "blockquote", "pre", "figure", "figcaption", "dd", "dt", "dl", "details", "summary"}
HEADING_TAGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
CELL_TAGS = {"td", "th"}

LOGIN_HINTS = ("sign in", "log in", "login", "登录", "登入", "请先登录")
CAPTCHA_HINTS = ("captcha", "verify you are human", "are you a robot", "checking your browser",
                 "attention required", "just a moment", "access denied", "请完成安全验证", "验证码")
JS_HINTS = ("enable javascript", "javascript is required", "please enable js", "需要启用 javascript")


class TextExtractor(HTMLParser):
    """Streaming HTML -> readable text. Drops scripts/styles/nav/footer; keeps headings,
    paragraphs, list items and table cells with line structure."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.title = ""
        self.meta = {}
        self.links = 0
        self._skip = 0        # depth inside SKIP_TAGS
        self._chrome = 0      # depth inside CHROME_TAGS (site navigation etc.)
        self._in_title = False
        self._heading = None
        self._stack = []
        self._pre = 0
        self._cell_buf = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = dict(attrs)
        if tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if key and a.get("content"):
                self.meta.setdefault(key, a["content"].strip())
            return
        if tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.meta.setdefault("canonical", a["href"])
            return
        if tag == "time" and a.get("datetime"):
            self.meta.setdefault("time_datetime", a["datetime"])
        if tag == "html" and a.get("lang"):
            self.meta.setdefault("lang", a["lang"])
        if tag == "title":
            self._in_title = True
            return
        if tag in SKIP_TAGS:
            self._skip += 1
        if tag in CHROME_TAGS:
            self._chrome += 1
        role = (a.get("role") or "").lower()
        if role in ("navigation", "banner", "contentinfo", "complementary", "search", "menu"):
            self._chrome += 1
            tag = tag + "@role"
        self._stack.append(tag)
        if self._skip or self._chrome:
            return
        if tag == "a":
            self.links += 1
        if tag in HEADING_TAGS:
            self._heading = HEADING_TAGS[tag]
            self.parts.append("\n\n" + self._heading + " ")
        elif tag == "pre":
            self._pre += 1
            self.parts.append("\n\n```\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in CELL_TAGS:
            self.parts.append(" | ")
        elif tag == "tr":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            return
        if tag in ("meta", "link"):
            return
        # pop to matching tag (tolerate bad nesting)
        while self._stack:
            t = self._stack.pop()
            base = t.split("@")[0]
            if t.endswith("@role"):
                self._chrome = max(0, self._chrome - 1)
            if base in SKIP_TAGS:
                self._skip = max(0, self._skip - 1)
            if base in CHROME_TAGS:
                self._chrome = max(0, self._chrome - 1)
            if base == "pre":
                self._pre = max(0, self._pre - 1)
                if not self._skip and not self._chrome:
                    self.parts.append("\n```\n")
            if base == tag:
                break
        if tag in HEADING_TAGS and not self._skip and not self._chrome:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self._skip or self._chrome:
            return
        if self._pre:
            self.parts.append(data)
        else:
            data = re.sub(r"[ \t\r\f\v]+", " ", data)
            data = re.sub(r"\n\s*", " ", data)
            if data.strip():
                self.parts.append(data)

    def text(self):
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r"(\n- )\s+", r"\1", raw)
        return raw.strip()


def decode_body(raw, headers):
    enc = (headers.get("Content-Encoding") or "").lower()
    try:
        if "gzip" in enc:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        elif "deflate" in enc:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:
        pass
    ctype = headers.get("Content-Type") or ""
    charset = None
    m = re.search(r"charset=([\w-]+)", ctype, re.I)
    if m:
        charset = m.group(1)
    else:
        m = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', raw[:8000], re.I)
        if m:
            charset = m.group(1).decode("ascii", "ignore")
    for cs in (charset, "utf-8", "gb18030", "latin-1"):
        if not cs:
            continue
        try:
            return raw.decode(cs), raw
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace"), raw


def http_get(url, timeout):
    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.geturl(), resp.headers, resp.read(MAX_BYTES), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read(MAX_BYTES)
        except Exception:
            body = b""
        return e.code, e.geturl() or url, e.headers, body, f"HTTP {e.code}"
    except Exception as e:
        return None, url, {}, b"", f"{type(e).__name__}: {e}"


def browser_get(url, timeout, wait_ms):
    """Render with Playwright. Returns (final_url, html, inner_text, error)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return url, "", "", "playwright not installed (pip install playwright && playwright install chromium)"
    try:
        with sync_playwright() as p:
            browser, err = None, None
            for kw in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
                try:
                    browser = p.chromium.launch(headless=True, **kw)
                    break
                except Exception as e:  # keep trying the other channels
                    err = e
            if browser is None:
                return url, "", "", f"no browser available: {str(err)[:200]}"
            ctx = browser.new_context(user_agent=BROWSER_UA, viewport={"width": 1280, "height": 900},
                                      locale="en-US")
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
            try:
                page.wait_for_load_state("networkidle", timeout=min(15000, int(timeout * 1000)))
            except Exception:
                pass
            if wait_ms:
                page.wait_for_timeout(wait_ms)
            html_text = page.content()
            try:
                inner = page.evaluate("() => document.body ? document.body.innerText : ''")
            except Exception:
                inner = ""
            final = page.url
            browser.close()
            return final, html_text, inner, None
    except Exception as e:
        return url, "", "", f"{type(e).__name__}: {str(e)[:300]}"


def pdf_text(raw):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return None, "pypdf not installed (pip install pypdf); PDF saved but not extracted"
    try:
        reader = PdfReader(io.BytesIO(raw))
        pages = []
        for i, pg in enumerate(reader.pages):
            pages.append(f"\n\n<!-- page {i + 1} -->\n" + (pg.extract_text() or ""))
        return "".join(pages).strip(), None
    except Exception as e:
        return None, f"PDF extraction failed: {e}"


def guess_published(meta, html_text):
    for k in ("article:published_time", "datepublished", "date", "pubdate", "publishdate", "dc.date",
              "dc.date.issued", "citation_publication_date", "citation_date", "og:updated_time",
              "article:modified_time", "time_datetime", "last-modified"):
        if meta.get(k):
            return meta[k], k
    m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html_text)
    if m:
        return m.group(1), "json-ld"
    return None, None


def normalize(s):
    s = s.casefold()
    s = re.sub(r"[\s　]+", " ", s)
    s = re.sub(r"[“”\"'‘’`´]", "", s)
    s = re.sub(r"[，,。.、；;：:！!？?（）()\[\]【】《》<>«»—–\-‐]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def find_quote(text, quote):
    """Return dict: found(bool), match_ratio(0-1), missing sentences, best snippet."""
    nt, nq = normalize(text), normalize(quote)
    if nq and nq in nt:
        return {"found": True, "match_ratio": 1.0, "missing": [], "note": "exact (normalized) match"}
    sents = [s.strip() for s in re.split(r"(?<=[。！？.!?;；])\s*", quote) if len(s.strip()) > 8]
    if not sents:
        sents = [quote]
    hit, missing = 0, []
    for s in sents:
        if normalize(s) in nt:
            hit += 1
        else:
            missing.append(s)
    ratio = hit / len(sents)
    # fuzzy fallback: best window similarity for short quotes
    best = 0.0
    if ratio < 1 and len(nq) <= 400:
        step = max(20, len(nq) // 4)
        for i in range(0, max(1, len(nt) - len(nq) + 1), step):
            r = difflib.SequenceMatcher(None, nq, nt[i:i + len(nq) + 40]).quick_ratio()
            if r > best:
                best = r
                if best > 0.97:
                    break
    return {"found": ratio == 1.0, "match_ratio": round(max(ratio, best if best > 0.9 else 0), 2),
            "missing": missing, "note": "partial match; the parts under 'missing' were NOT found on the page"
            if ratio < 1 else "all sentences found"}


def quality_flags(text, html_text, final_url, title, status):
    flags = {}
    low_t, low_title = text[:4000].casefold(), (title or "").casefold()
    n = len(text)
    flags["text_chars"] = n
    flags["looks_like_blocked"] = bool(status in (401, 403, 429)) or any(h in low_title for h in CAPTCHA_HINTS) \
        or (n < 1500 and any(h in low_t for h in CAPTCHA_HINTS))
    path = urllib.parse.urlsplit(final_url).path
    flags["looks_like_login_wall"] = bool(re.search(r"/(login|signin|sign-in|log-in|auth)(/|$)", path, re.I)) \
        or (n < 2500 and any(low_title.strip().startswith(h) for h in LOGIN_HINTS))
    flags["looks_like_js_shell"] = n < 500 and (html_text.lower().count("<script") >= 3 or any(h in low_t for h in JS_HINTS))
    flags["looks_like_error_page"] = status is not None and status >= 400
    flags["thin_content"] = 0 < n < 800
    return flags


def safe_id(url, idx):
    host = urllib.parse.urlsplit(url).netloc.replace(":", "_")
    return f"S{idx:02d}_{re.sub(r'[^A-Za-z0-9.-]', '_', host)[:40]}"


def process(url, args, idx):
    out = args.out
    os.makedirs(os.path.join(out, "pages"), exist_ok=True)
    sid = args.id if (args.id and idx == 1) else safe_id(url, idx + args.start - 1)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"id": sid, "url": url, "final_url": url, "fetched_at": fetched_at, "method": None,
              "http_status": None, "content_type": None, "title": None, "published": None,
              "published_from": None, "canonical": None, "lang": None, "error": None}
    text, html_text, raw = "", "", b""
    inner = ""

    if args.browser:
        result["method"] = "browser"
        final, html_text, inner, err = browser_get(url, args.timeout, args.wait)
        result["final_url"] = final
        result["error"] = err
        if err and not html_text:
            print(json.dumps(result, ensure_ascii=False))
            return result
        result["http_status"] = 200
        result["content_type"] = "text/html"
    else:
        result["method"] = "http"
        status, final, headers, raw, err = http_get(url, args.timeout)
        result.update(http_status=status, final_url=final, error=err)
        ctype = (headers.get("Content-Type") or "").lower() if headers else ""
        result["content_type"] = ctype.split(";")[0].strip() or None
        if not raw and err:
            print(json.dumps(result, ensure_ascii=False))
            return result
        if "pdf" in ctype or raw[:5] == b"%PDF-":
            result["content_type"] = "application/pdf"
            os.makedirs(os.path.join(out, "raw"), exist_ok=True)
            pdf_path = os.path.join(out, "raw", sid + ".pdf")
            with open(pdf_path, "wb") as f:
                f.write(raw)
            result["raw_file"] = pdf_path
            text, perr = pdf_text(raw)
            if perr:
                result["error"] = perr
            text = text or ""
        else:
            html_text, raw = decode_body(raw, headers)

    if html_text:
        ex = TextExtractor()
        try:
            ex.feed(html_text)
        except Exception as e:
            result["error"] = f"parse error: {e}"
        text = ex.text()
        # Browser innerText is a good fallback when the DOM was built by JS but
        # the static extractor still found little.
        if inner and len(inner.strip()) > len(text) * 1.5:
            text = re.sub(r"\n{3,}", "\n\n", inner.strip())
        result["title"] = re.sub(r"\s+", " ", ex.title).strip() or ex.meta.get("og:title") or None
        result["published"], result["published_from"] = guess_published(ex.meta, html_text)
        result["canonical"] = ex.meta.get("canonical")
        result["lang"] = ex.meta.get("lang")
        result["description"] = ex.meta.get("description") or ex.meta.get("og:description")
        result["links_in_content"] = ex.links
        if args.raw:
            os.makedirs(os.path.join(out, "raw"), exist_ok=True)
            raw_path = os.path.join(out, "raw", sid + ".html")
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(html_text)
            result["raw_file"] = raw_path

    flags = quality_flags(text, html_text, result["final_url"], result["title"], result["http_status"])
    result.update(flags)

    truncated = False
    if args.max_chars and len(text) > args.max_chars:
        text_saved = text[: args.max_chars] + f"\n\n[... truncated: {len(text) - args.max_chars} more characters not saved; "\
                     f"rerun with --max-chars 0 for the full text ...]"
        truncated = True
    else:
        text_saved = text
    result["truncated"] = truncated
    result["full_text_chars"] = len(text)

    if args.find:
        result["find"] = {q: find_quote(text, q) for q in args.find}

    md_path = os.path.join(out, "pages", sid + ".md")
    header = [
        "---",
        f"id: {sid}",
        f"url: {url}",
        f"final_url: {result['final_url']}",
        f"title: {json.dumps(result['title'], ensure_ascii=False)}",
        f"published: {result['published'] or 'unknown'}",
        f"fetched_at: {fetched_at}",
        f"method: {result['method']}",
        f"http_status: {result['http_status']}",
        f"content_type: {result['content_type']}",
        f"text_chars: {result['full_text_chars']}",
        f"truncated: {str(truncated).lower()}",
        "---",
        "",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(header) + text_saved + "\n")
    result["page_file"] = md_path
    with open(os.path.join(out, "pages", sid + ".json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    warnings = []
    if result["looks_like_blocked"]:
        warnings.append("page looks like a bot challenge / access denied; try --browser or screenshot.py")
    if result["looks_like_login_wall"]:
        warnings.append("page looks like a login wall; content behind it was NOT fetched")
    if result["looks_like_js_shell"]:
        warnings.append("almost no text; page needs JavaScript; rerun with --browser")
    if result["looks_like_error_page"]:
        warnings.append(f"HTTP {result['http_status']}: this is an error page, not the cited content")
    if truncated:
        warnings.append("text truncated; the evidence you need may be beyond the saved part")
    result["warnings"] = warnings

    print(json.dumps({k: result[k] for k in ("id", "url", "final_url", "http_status", "title", "published",
                                              "full_text_chars", "truncated", "page_file", "warnings", "error")
                      if k in result} | ({"find": result["find"]} if args.find else {}), ensure_ascii=False))
    if args.print:
        print("-" * 60)
        print(text_saved[: args.print_chars] + ("\n[... --print output cut, open the page file for more ...]"
                                              if len(text_saved) > args.print_chars else ""))
        print("-" * 60)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--file", help="file with one URL per line")
    ap.add_argument("--out", default="web-evidence", help="evidence directory (default: web-evidence)")
    ap.add_argument("--id", help="source id for a single URL (e.g. S01); default derives from host")
    ap.add_argument("--start", type=int, default=1, help="first index for auto ids when fetching many URLs")
    ap.add_argument("--timeout", type=float, default=25)
    ap.add_argument("--max-chars", type=int, default=40000, help="max characters saved (0 = unlimited)")
    ap.add_argument("--find", action="append", help="check that this quote appears in the text (repeatable)")
    ap.add_argument("--browser", action="store_true", help="render with Playwright (for JS-only pages)")
    ap.add_argument("--wait", type=int, default=1500, help="extra ms to wait after load in --browser mode")
    ap.add_argument("--raw", action="store_true", help="also save raw HTML")
    ap.add_argument("--print", action="store_true", help="print the extracted text to stdout")
    ap.add_argument("--print-chars", type=int, default=12000)
    args = ap.parse_args(argv)

    urls = list(args.urls)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            urls += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not urls:
        ap.error("no URLs given")
    if args.id and len(urls) > 1:
        ap.error("--id only works with a single URL; use --start for batches")

    rc = 0
    for i, u in enumerate(urls, 1):
        r = process(u, args, i)
        if r.get("error") and not r.get("page_file"):
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
