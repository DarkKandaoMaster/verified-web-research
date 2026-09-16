#!/usr/bin/env python3
"""
screenshot.py - Capture a web page as image evidence (plus rendered text).

Backends, tried in order:
  1. Playwright (pip install playwright; then `playwright install chromium`, or it will
     reuse an installed Edge/Chrome via the msedge/chrome channels without any download).
  2. Headless Edge/Chrome CLI (no Python packages needed; viewport-only capture,
     no --find-text / --selector support).

Outputs (under --out, default ./web-evidence/shots):
  <name>.png            viewport screenshot (default) or clipped region
  <name>_full_01.png…   full page split into readable segments (--full-page)
  <name>.txt            rendered page text (document.body.innerText) — Playwright only
  <name>.json           metadata: url, final_url, title, captured_at, viewport, files, backend

Usage:
  python screenshot.py https://example.com/page --name S03
  python screenshot.py https://example.com/page --name S03 --full-page
  python screenshot.py https://example.com/page --name S03 --find-text "Revenue grew 12%"
  python screenshot.py https://example.com/page --name S03 --selector "table.results"
  python screenshot.py https://example.com/page --name S03 --pdf   # also save print-to-PDF

A saved PNG is not evidence until it has been looked at. After capturing, open the
image with your image-viewing tool and read the relevant region; note in the
ledger what the screenshot shows and what it does not.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

HIGHLIGHT_JS = """
(needle) => {
  const norm = s => s.replace(/\\s+/g, ' ').trim().toLowerCase();
  const target = norm(needle);
  if (!target) return null;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let best = null;
  while (walker.nextNode()) {
    const n = walker.currentNode;
    if (!n.parentElement) continue;
    const style = window.getComputedStyle(n.parentElement);
    if (style.display === 'none' || style.visibility === 'hidden') continue;
    if (norm(n.textContent).includes(target)) { best = n.parentElement; break; }
  }
  if (!best) {
    // fall back: first block whose text contains the first ~40 chars
    const short = target.slice(0, 40);
    for (const el of document.querySelectorAll('p,li,td,th,h1,h2,h3,h4,h5,h6,div,span,blockquote')) {
      if (norm(el.innerText || '').includes(short)) { best = el; break; }
    }
  }
  if (!best) return null;
  best.scrollIntoView({block: 'center', inline: 'nearest'});
  best.style.outline = '3px solid #ff3b30';
  best.style.outlineOffset = '2px';
  const r = best.getBoundingClientRect();
  return {x: r.left + window.scrollX, y: r.top + window.scrollY, width: r.width, height: r.height,
          text: (best.innerText || best.textContent || '').slice(0, 300)};
}
"""


def _launch(p):
    err = None
    for kw in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
        try:
            return p.chromium.launch(headless=True, **kw), None
        except Exception as e:
            err = e
    return None, f"no Chromium/Edge/Chrome available for Playwright: {str(err)[:200]}"


def capture_playwright(args, base):
    from playwright.sync_api import sync_playwright
    meta = {"backend": "playwright", "files": []}
    with sync_playwright() as p:
        browser, err = _launch(p)
        if browser is None:
            return None, err
        ctx = browser.new_context(user_agent=BROWSER_UA, viewport={"width": args.width, "height": args.height},
                                  device_scale_factor=args.scale, locale="zh-CN" if args.zh else "en-US")
        page = ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=int(args.timeout * 1000))
        try:
            page.wait_for_load_state("networkidle", timeout=min(15000, int(args.timeout * 1000)))
        except Exception:
            pass
        if args.wait:
            page.wait_for_timeout(args.wait)
        # Nudge lazy-loaded images/charts into existence before a full-page shot.
        if args.full_page:
            try:
                page.evaluate("""async () => {
                    const h = document.body.scrollHeight; let y = 0;
                    while (y < h && y < 30000) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); y += 700; }
                    window.scrollTo(0, 0);
                }""")
                page.wait_for_timeout(400)
            except Exception:
                pass
        meta["final_url"] = page.url
        meta["title"] = page.title()
        meta["viewport"] = {"width": args.width, "height": args.height, "scale": args.scale}

        try:
            text = page.evaluate("() => document.body ? document.body.innerText : ''")
            with open(base + ".txt", "w", encoding="utf-8") as f:
                f.write(text)
            meta["text_file"] = base + ".txt"
            meta["text_chars"] = len(text)
        except Exception:
            pass

        if args.find_text:
            box = page.evaluate(HIGHLIGHT_JS, args.find_text)
            page.wait_for_timeout(200)
            if box:
                pad = args.margin
                clip = {"x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad),
                        "width": min(args.width + 2 * pad, box["width"] + 2 * pad),
                        "height": min(args.max_segment, box["height"] + 2 * pad)}
                path = base + ".png"
                page.screenshot(path=path, clip=clip, full_page=True)
                meta["files"].append(path)
                meta["find_text"] = {"found": True, "region": clip, "matched_text": box["text"]}
            else:
                path = base + ".png"
                page.screenshot(path=path)
                meta["files"].append(path)
                meta["find_text"] = {"found": False,
                                     "note": "text not found in rendered DOM; captured the viewport instead"}
        elif args.selector:
            loc = page.locator(args.selector).first
            try:
                loc.scroll_into_view_if_needed(timeout=5000)
                path = base + ".png"
                loc.screenshot(path=path)
                meta["files"].append(path)
                meta["selector"] = {"found": True, "selector": args.selector}
            except Exception as e:
                path = base + ".png"
                page.screenshot(path=path)
                meta["files"].append(path)
                meta["selector"] = {"found": False, "selector": args.selector, "error": str(e)[:150],
                                    "note": "selector not found; captured the viewport instead"}
        elif args.full_page:
            total = page.evaluate("() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
            meta["page_height"] = total
            seg = args.max_segment
            if total <= seg:
                path = base + "_full.png"
                page.screenshot(path=path, full_page=True)
                meta["files"].append(path)
            else:
                # Tall pages are split so the model can read each part at legible size
                # instead of one 20,000px image scaled down to a blur.
                y, i, overlap = 0, 1, 80
                while y < total and i <= args.max_segments:
                    h = min(seg, total - y)
                    path = f"{base}_full_{i:02d}.png"
                    page.screenshot(path=path, full_page=True,
                                    clip={"x": 0, "y": y, "width": args.width, "height": h})
                    meta["files"].append(path)
                    y += h - overlap
                    i += 1
                if y < total:
                    meta["note"] = f"page taller than {args.max_segments} segments; captured the first {args.max_segments}"
        else:
            path = base + ".png"
            page.screenshot(path=path)
            meta["files"].append(path)

        if args.pdf:
            try:
                page.emulate_media(media="print")
                page.pdf(path=base + ".pdf", format="A4", print_background=True)
                meta["pdf_file"] = base + ".pdf"
            except Exception as e:
                meta["pdf_error"] = str(e)[:150]
        browser.close()
    return meta, None


def find_browser_exe():
    candidates = []
    if sys.platform.startswith("win"):
        pf = [os.environ.get("ProgramFiles", r"C:\Program Files"),
              os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
              os.environ.get("LOCALAPPDATA", "")]
        for base in pf:
            candidates += [os.path.join(base, r"Microsoft\Edge\Application\msedge.exe"),
                           os.path.join(base, r"Google\Chrome\Application\chrome.exe"),
                           os.path.join(base, r"Chromium\Application\chrome.exe")]
    elif sys.platform == "darwin":
        candidates += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                       "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                       "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"):
        w = shutil.which(name)
        if w:
            candidates.append(w)
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def capture_cli(args, base):
    exe = find_browser_exe()
    if not exe:
        return None, "no Edge/Chrome/Chromium executable found for CLI fallback"
    path = os.path.abspath(base + ".png")
    height = args.height if not args.full_page else min(args.max_segment * 2, 6000)
    # A throwaway profile: Edge/Chrome refuse to run headless against a profile
    # that a normal browser window already has open.
    profile = tempfile.mkdtemp(prefix="vwr-shot-")
    cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
           f"--user-data-dir={profile}", f"--user-agent={BROWSER_UA}", f"--window-size={args.width},{height}",
           f"--screenshot={path}", f"--timeout={int(args.timeout * 1000)}", args.url]
    try:
        subprocess.run(cmd, capture_output=True, timeout=args.timeout + 30)
    except Exception as e:
        return None, f"CLI capture failed: {e}"
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not os.path.exists(path):
        return None, "CLI capture produced no file"
    return {"backend": "cli:" + os.path.basename(exe), "files": [path], "final_url": None, "title": None,
            "viewport": {"width": args.width, "height": height},
            "note": "CLI fallback: viewport-only capture; final URL/title unknown; --find-text/--selector ignored"}, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--name", help="base file name (e.g. the source id S03); default derives from host")
    ap.add_argument("--out", default=os.path.join("web-evidence", "shots"))
    ap.add_argument("--full-page", action="store_true", help="capture the whole page (split into segments)")
    ap.add_argument("--find-text", help="scroll to this text, highlight it, and capture the region around it")
    ap.add_argument("--selector", help="CSS selector of the element to capture (e.g. a table or chart)")
    ap.add_argument("--margin", type=int, default=120, help="pixels of context around --find-text")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--scale", type=float, default=1.0, help="device scale factor (2 = sharper small text)")
    ap.add_argument("--max-segment", type=int, default=1800, help="max px height per full-page segment")
    ap.add_argument("--max-segments", type=int, default=8)
    ap.add_argument("--wait", type=int, default=1500, help="extra ms to wait after load")
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--pdf", action="store_true", help="also save a print-to-PDF (Playwright only)")
    ap.add_argument("--zh", action="store_true", help="request zh-CN locale")
    ap.add_argument("--cli", action="store_true", help="force the headless-browser CLI fallback")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    name = args.name or re.sub(r"[^A-Za-z0-9.-]", "_", re.sub(r"^https?://", "", args.url))[:60]
    base = os.path.join(args.out, name)

    meta, err = None, None
    if not args.cli:
        try:
            import playwright  # noqa: F401
            meta, err = capture_playwright(args, base)
        except ImportError:
            err = "playwright not installed; falling back to headless browser CLI"
        except Exception as e:
            err = f"playwright failed: {type(e).__name__}: {str(e)[:200]}"
    if meta is None:
        meta2, err2 = capture_cli(args, base)
        if meta2 is None:
            print(json.dumps({"ok": False, "url": args.url, "error": f"{err}; {err2}"}, ensure_ascii=False))
            return 1
        meta = meta2
        meta["fallback_reason"] = err

    meta.update(ok=True, url=args.url, captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                full_page=bool(args.full_page))
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    meta["meta_file"] = base + ".json"
    print(json.dumps(meta, ensure_ascii=False))
    print("reminder: open the PNG and read it before treating it as evidence.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
