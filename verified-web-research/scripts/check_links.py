#!/usr/bin/env python3
"""
check_links.py - Batch URL liveness checker for AI-generated citations.

Standard library only (no pip install needed). Python 3.9+.

What it does for every URL:
  1. HEAD request with a browser-like User-Agent, following redirects.
  2. If HEAD fails or returns >= 400, retries with GET (many servers mishandle HEAD).
  3. Reads the first part of the body (GET) to detect "soft 404" pages,
     login walls, and bot challenges that hide behind HTTP 200.
  4. Retries once on timeout / connection reset before believing the failure.
  5. Optionally asks the Wayback Machine for an archived copy of dead URLs.

Status meanings (see SKILL.md, "状态含义"):
  OK               reachable, looks like a real page
  OK_REDIRECTED    reachable after redirect(s); final_url differs (check it still is the intended page)
  SUSPECT_SOFT404  HTTP 200 but page text says "not found" / redirected to the site root
  LOGIN_WALL       HTTP 200 but the page is a sign-in page
  BLOCKED          401/403/429 or a bot-challenge page: the server refused an automated client,
                   NOT proof the page is gone. Verify in a browser / screenshot.py.
  GONE             404 / 410
  SERVER_ERROR     5xx
  UNREACHABLE      DNS failure, timeout, SSL error, connection refused
  UNSUPPORTED      non-http(s) scheme or malformed URL

Usage:
  python check_links.py https://a.com/x https://b.org/y
  python check_links.py --file urls.txt
  python check_links.py --from-text answer.md --json links.json --wayback
"""

import argparse
import concurrent.futures
import gzip
import html
import io
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate",
}
BOT_BLOCK_STATUSES = {401, 403, 429}
BODY_LIMIT = 200_000  # bytes read from GET body for heuristics

URL_RE = re.compile(r"""https?://[^\s<>"'()\[\]{}]+""")

SOFT404_TITLE_HINTS = (
    "not found", "404", "page doesn't exist", "page does not exist", "no longer available",
    "页面不存在", "找不到", "无法找到", "页面丢失", "不存在", "已删除", "抱歉", "出错了",
    "ページが見つかりません", "nicht gefunden", "introuvable",
)
LOGIN_HINTS = (
    "sign in", "log in", "login", "登录", "登入", "请先登录", "会员登录",
)
CAPTCHA_HINTS = (
    "captcha", "verify you are human", "are you a robot", "checking your browser",
    "attention required", "cloudflare", "access denied", "请完成安全验证", "验证码",
    "just a moment",
)
JS_HINTS = (
    "enable javascript", "javascript is required", "please enable js", "需要启用 javascript",
    "请开启javascript",
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Used only to count redirects; we let urllib follow them but record the chain."""
    def __init__(self):
        super().__init__()
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append((code, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _decode_body(raw, resp_headers):
    enc = (resp_headers.get("Content-Encoding") or "").lower()
    try:
        if "gzip" in enc:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        elif "deflate" in enc:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:
        pass
    charset = "utf-8"
    ctype = resp_headers.get("Content-Type") or ""
    m = re.search(r"charset=([\w-]+)", ctype, re.I)
    if m:
        charset = m.group(1)
    else:
        m = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', raw[:5000], re.I)
        if m:
            charset = m.group(1).decode("ascii", "ignore")
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _title_and_text(html_text):
    t = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
    title = html.unescape(re.sub(r"\s+", " ", t.group(1))).strip() if t else ""
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html_text, flags=re.I | re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    body = html.unescape(re.sub(r"\s+", " ", body)).strip()
    return title, body


def _request(url, method, timeout, read_body):
    redirector = _NoRedirect()
    opener = urllib.request.build_opener(redirector, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    req = urllib.request.Request(url, headers=HEADERS, method=method)
    body = b""
    try:
        with opener.open(req, timeout=timeout) as resp:
            status = resp.status
            final_url = resp.geturl()
            resp_headers = resp.headers
            if read_body:
                body = resp.read(BODY_LIMIT)
    except urllib.error.HTTPError as e:
        status = e.code
        final_url = e.geturl() or url
        resp_headers = e.headers
        if read_body:
            try:
                body = e.read(BODY_LIMIT)
            except Exception:
                body = b""
    return status, final_url, resp_headers, body, redirector.chain


def _classify_error(exc):
    if isinstance(exc, socket.timeout) or "timed out" in str(exc).lower():
        return "Timeout"
    if isinstance(exc, ssl.SSLError):
        return "SSL Error"
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
            return "Timeout"
        if isinstance(reason, socket.gaierror) or "getaddrinfo" in str(reason) or "Name or service" in str(reason):
            return "DNS failure"
        if isinstance(reason, ssl.SSLError) or "SSL" in str(reason) or "CERTIFICATE" in str(reason):
            return "SSL Error"
        return f"Connection Error: {reason}"
    if isinstance(exc, (ConnectionResetError, ConnectionRefusedError, ConnectionAbortedError)):
        return "Connection Error"
    return f"Error: {type(exc).__name__}: {exc}"


def _host(netloc):
    h = netloc.split(":")[0].lower()
    return h[4:] if h.startswith("www.") else h


def _heuristics(url, final_url, status, ctype, title, text, html_text):
    """Return (status_label, notes) from body heuristics for a 2xx HTML response."""
    notes = []
    script_heavy = html_text.lower().count("<script") >= 3
    low_title = title.lower()
    low_text = text[:3000].lower()

    if any(h in low_title for h in CAPTCHA_HINTS) or (len(text) < 1500 and any(h in low_text for h in CAPTCHA_HINTS)):
        return "BLOCKED", ["bot challenge / captcha page"]

    if any(h in low_title for h in SOFT404_TITLE_HINTS):
        notes.append(f"title looks like an error page: {title[:80]!r}")
    if len(text) < 400 and any(h in low_text for h in SOFT404_TITLE_HINTS):
        notes.append("short body containing not-found wording")
    # Redirected from a deep path to the site root or a generic landing page.
    o, f = urllib.parse.urlsplit(url), urllib.parse.urlsplit(final_url)
    if o.path.strip("/") and f.path.strip("/") == "" and _host(o.netloc) == _host(f.netloc):
        notes.append("redirected from a deep path to the site root")
    if notes:
        return "SUSPECT_SOFT404", notes

    if re.search(r"/(login|signin|sign-in|log-in|account/login|auth)(/|$|\?)", f.path + "?", re.I) or \
       (len(text) < 2500 and any(h == low_title.strip() or low_title.startswith(h) for h in LOGIN_HINTS)):
        return "LOGIN_WALL", ["final page is a sign-in page"]

    if len(text) < 300:
        if any(h in low_text for h in JS_HINTS) or script_heavy:
            notes.append("almost no text; page probably needs JavaScript (use fetch_page.py --browser or screenshot.py)")
        else:
            notes.append(f"very little text ({len(text)} chars); verify content manually")

    if status == 200 and "text/html" not in ctype and "pdf" not in ctype and "json" not in ctype and "xml" not in ctype and "text/" not in ctype:
        notes.append(f"unusual content-type: {ctype}")

    label = "OK_REDIRECTED" if final_url.rstrip("/") != url.rstrip("/") else "OK"
    return label, notes


def wayback_lookup(url, timeout):
    api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    try:
        req = urllib.request.Request(api, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        snap = (data.get("archived_snapshots") or {}).get("closest") or {}
        if snap.get("available"):
            return {"url": snap.get("url"), "timestamp": snap.get("timestamp")}
    except Exception as e:
        return {"error": str(e)[:120]}
    return None


def check_one(url, timeout=15, retries=1, wayback=False, soft404=True):
    started = time.time()
    result = {
        "url": url,
        "final_url": url,
        "status": None,
        "http_status": None,
        "content_type": None,
        "redirects": 0,
        "method": None,
        "title": None,
        "notes": [],
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": None,
    }
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        result["status"] = "UNSUPPORTED"
        result["notes"].append("not an http(s) URL")
        return result

    # Resolve the host first: a name that does not resolve at all is the most
    # common signature of an invented URL, and worth saying explicitly.
    try:
        socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        result.update(status="UNREACHABLE", elapsed_s=round(time.time() - started, 2))
        result["notes"].append("DNS failure: host name does not resolve")
        if wayback:
            result["wayback"] = wayback_lookup(url, timeout)
        return result
    except Exception:
        pass

    attempt = 0
    while True:
        attempt += 1
        try:
            status, final_url, hdrs, body, chain = _request(url, "HEAD", timeout, read_body=False)
            method = "HEAD"
            if status >= 400 or status == 405 or soft404:
                # GET either because HEAD failed / is unsupported, or because we
                # want the body for soft-404 / login-wall heuristics.
                status, final_url, hdrs, body, chain = _request(url, "GET", timeout, read_body=True)
                method = "GET"
            break
        except Exception as e:
            err = _classify_error(e)
            if attempt <= retries and err in ("Timeout", "Connection Error"):
                time.sleep(1.0)
                continue
            result.update(status="UNREACHABLE", method="GET", elapsed_s=round(time.time() - started, 2))
            result["notes"].append(err)
            if wayback:
                result["wayback"] = wayback_lookup(url, timeout)
            return result

    ctype = (hdrs.get("Content-Type") or "").lower()
    result.update(http_status=status, final_url=final_url, content_type=ctype.split(";")[0].strip() or None,
                  redirects=len(chain), method=method)
    if chain:
        result["redirect_chain"] = [u for _, u in chain]

    if status in BOT_BLOCK_STATUSES:
        result["status"] = "BLOCKED"
        result["notes"].append(f"HTTP {status}: server refused an automated client; not proof the page is gone")
    elif status in (404, 410):
        result["status"] = "GONE"
        result["notes"].append(f"HTTP {status}")
    elif status >= 500:
        result["status"] = "SERVER_ERROR"
        result["notes"].append(f"HTTP {status} (may be transient; retry later)")
    elif status >= 400:
        result["status"] = "GONE" if status in (404, 410) else "BLOCKED"
        result["notes"].append(f"HTTP {status}")
    else:
        if body and ("html" in ctype or "xml" in ctype or not ctype):
            text_html = _decode_body(body, hdrs)
            title, text = _title_and_text(text_html)
            result["title"] = title or None
            result["text_chars_sampled"] = len(text)
            label, notes = _heuristics(url, final_url, status, ctype, title, text, text_html)
            result["status"] = label
            result["notes"].extend(notes)
        else:
            result["status"] = "OK_REDIRECTED" if final_url.rstrip("/") != url.rstrip("/") else "OK"
            if "pdf" in ctype:
                result["notes"].append("PDF document (use fetch_page.py to extract text)")

    if wayback and result["status"] in ("GONE", "UNREACHABLE", "SUSPECT_SOFT404", "SERVER_ERROR"):
        result["wayback"] = wayback_lookup(url, timeout)

    result["elapsed_s"] = round(time.time() - started, 2)
    return result


def extract_urls(text):
    urls = []
    for m in URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;:!?'\"）」』】>")
        # Balance a trailing ')' that belongs to markdown link syntax.
        while u.endswith(")") and u.count("(") < u.count(")"):
            u = u[:-1]
        u = html.unescape(u)
        if u not in urls:
            urls.append(u)
    return urls


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*", help="URLs to check")
    ap.add_argument("--file", help="file with one URL per line")
    ap.add_argument("--from-text", help="extract every http(s) URL from this text/markdown file")
    ap.add_argument("--timeout", type=float, default=15)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--retries", type=int, default=1, help="retries on timeout/connection reset")
    ap.add_argument("--wayback", action="store_true", help="look up Wayback Machine snapshots for dead URLs")
    ap.add_argument("--no-soft404", action="store_true", help="skip body heuristics (HEAD only, faster)")
    ap.add_argument("--json", help="write full results to this JSON file")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any URL is GONE/UNREACHABLE/SUSPECT_SOFT404")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    urls = list(args.urls)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            urls += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if args.from_text:
        with open(args.from_text, encoding="utf-8", errors="replace") as f:
            urls += extract_urls(f.read())
    seen, ordered = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    if not ordered:
        ap.error("no URLs given")

    results = [None] * len(ordered)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {ex.submit(check_one, u, args.timeout, args.retries, args.wayback, not args.no_soft404): i
                for i, u in enumerate(ordered)}
        for fut in concurrent.futures.as_completed(futs):
            results[futs[fut]] = fut.result()

    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1

    if not args.quiet:
        w = max(len(r["status"]) for r in results)
        for r in results:
            line = f"{r['status']:<{w}}  {r['url']}"
            if r["http_status"] is not None:
                line += f"  [HTTP {r['http_status']}]"
            if r["final_url"] != r["url"]:
                line += f"\n{'':<{w}}  -> {r['final_url']}"
            for n in r["notes"]:
                line += f"\n{'':<{w}}  · {n}"
            wb = r.get("wayback")
            if wb and wb.get("url"):
                line += f"\n{'':<{w}}  · wayback: {wb['url']}"
            print(line)
        print()
        print("summary: " + ", ".join(f"{k}={v}" for k, v in sorted(summary.items())))
        print("note: BLOCKED means the server refused a script, not that the page is dead; "
              "OK means reachable, not that the page supports any claim.")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "summary": summary, "results": results}, f, ensure_ascii=False, indent=2)
        if not args.quiet:
            print(f"json: {args.json}")

    bad = {"GONE", "UNREACHABLE", "SUSPECT_SOFT404"}
    if args.strict and any(r["status"] in bad for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
