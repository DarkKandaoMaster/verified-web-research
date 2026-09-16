#!/usr/bin/env python3
"""
ledger.py - Evidence ledger: which sources were actually read, which claims rest on what.

Standard library only. State lives in <out>/ledger.json (default out: ./web-evidence).

Why a ledger: an answer with links is not the same as an answer whose links were
opened, read and found to support the sentence they are attached to. The ledger
records those three facts separately so the final answer can only cite what was
really checked, and `validate` tells you what is still missing.

Commands
  init          create the ledger                      ledger.py init --question "..." [--cutoff 2026-09-17]
  add-source    register a URL, get an ID (S01, S02…)  ledger.py add-source URL --title "..." --how search
  set-source    update fields on a source              ledger.py set-source S01 --status OK --page pages/S01.md --group official
  import-check  merge check_links.py --json results    ledger.py import-check links.json
  import-pages  merge fetch_page.py page metadata      ledger.py import-pages          (scans <out>/pages/*.json)
  add-claim     record a claim + its evidence           ledger.py add-claim "text" --support S01,S02 --quote "..." --quote-from S01
  set-claim     update a claim                          ledger.py set-claim C01 --confidence medium --note "..."
  validate      report gaps (exit 1 if any error)       ledger.py validate
  render        print Sources block + claims table      ledger.py render [--lang zh|en]
  show          dump the ledger as JSON

Source fields: id, url, final_url, title, how (search|fetch|browser|screenshot|user|memory), status
(from check_links), page (path of fetched text), shot (path of screenshot), read (none|snippet|text|screenshot|both),
published, accessed, group (independence group, e.g. "reuters-wire", "official"), kind
(primary|secondary|tertiary), note.

Claim fields: id, text, support (source ids), contra (source ids), quote, quote_from, quote_verified,
confidence (high|medium|low), basis, as_of (date the claim is true as of), note.
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VALID_READ = {"none", "snippet", "text", "screenshot", "both"}
VALID_CONF = {"high", "medium", "low"}
DEAD_STATUSES = {"GONE", "UNREACHABLE", "SUSPECT_SOFT404"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def path(args):
    return os.path.join(args.out, "ledger.json")


def load(args):
    p = path(args)
    if not os.path.exists(p):
        sys.exit(f"no ledger at {p}; run: ledger.py init --out {args.out} --question \"...\"")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(args, data):
    data["updated_at"] = now()
    os.makedirs(args.out, exist_ok=True)
    with open(path(args), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize(s):
    s = (s or "").casefold()
    s = re.sub(r"[\s　]+", " ", s)
    s = re.sub(r"[“”\"'‘’`´]", "", s)
    s = re.sub(r"[，,。.、；;：:！!？?（）()\[\]【】《》<>«»—–\-‐]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_url(u):
    u = (u or "").strip()
    u = re.sub(r"#.*$", "", u)
    u = re.sub(r"^http://", "https://", u)
    return u.rstrip("/")


def next_id(items, prefix):
    n = 0
    for it in items:
        m = re.match(prefix + r"(\d+)", it["id"])
        if m:
            n = max(n, int(m.group(1)))
    return f"{prefix}{n + 1:02d}"


def find_source(data, key):
    for s in data["sources"]:
        if s["id"] == key or norm_url(s["url"]) == norm_url(key) or norm_url(s.get("final_url")) == norm_url(key):
            return s
    return None


def find_claim(data, key):
    for c in data["claims"]:
        if c["id"] == key:
            return c
    return None


def read_page_text(args, page_path):
    if not page_path:
        return None
    p = page_path if os.path.isabs(page_path) or os.path.exists(page_path) else os.path.join(args.out, page_path)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    # strip the metadata header written by fetch_page.py
    if txt.startswith("---"):
        parts = txt.split("\n---\n", 1)
        if len(parts) == 2:
            txt = parts[1]
    return txt


def verify_quote(args, data, claim):
    q, src_id = claim.get("quote"), claim.get("quote_from")
    if not q or not src_id:
        claim["quote_verified"] = None
        return
    src = find_source(data, src_id)
    texts = []
    if src:
        for key in ("page", "shot_text"):
            t = read_page_text(args, src.get(key))
            if t:
                texts.append(t)
    if not texts:
        claim["quote_verified"] = False
        claim["quote_check"] = f"no fetched text for {src_id}; fetch the page (or --how screenshot and verify visually)"
        return
    nq = normalize(q)
    for t in texts:
        if nq and nq in normalize(t):
            claim["quote_verified"] = True
            claim["quote_check"] = "quote found in fetched text"
            return
    claim["quote_verified"] = False
    claim["quote_check"] = "quote NOT found in fetched text (paraphrase? wrong page? truncated fetch?)"


# ----------------------------------------------------------------------------- commands

def cmd_init(args):
    p = path(args)
    if os.path.exists(p) and not args.force:
        sys.exit(f"{p} exists; use --force to overwrite")
    data = {"question": args.question, "cutoff": args.cutoff, "created_at": now(),
            "sources": [], "claims": [], "notes": []}
    save(args, data)
    print(f"ledger created: {p}")


def cmd_add_source(args):
    data = load(args)
    existing = find_source(data, args.url)
    if existing:
        print(json.dumps({"id": existing["id"], "url": existing["url"], "note": "already registered"}, ensure_ascii=False))
        return
    src = {"id": args.id or next_id(data["sources"], "S"), "url": args.url, "final_url": None, "title": args.title,
           "how": args.how, "status": None, "page": None, "shot": None, "read": "none", "published": None,
           "accessed": now(), "group": args.group, "kind": args.kind, "note": args.note}
    data["sources"].append(src)
    save(args, data)
    print(json.dumps({"id": src["id"], "url": src["url"]}, ensure_ascii=False))


def cmd_set_source(args):
    data = load(args)
    src = find_source(data, args.source)
    if not src:
        sys.exit(f"unknown source {args.source}")
    for k in ("title", "status", "page", "shot", "shot_text", "read", "published", "group", "kind", "note", "final_url", "how"):
        v = getattr(args, k, None)
        if v is not None:
            src[k] = v
    if src.get("read") not in VALID_READ:
        sys.exit(f"--read must be one of {sorted(VALID_READ)}")
    if src.get("page") and src.get("read") == "none":
        src["read"] = "text"
    if src.get("shot") and src.get("read") == "none":
        src["read"] = "screenshot"
    save(args, data)
    print(json.dumps(src, ensure_ascii=False))


def cmd_import_check(args):
    data = load(args)
    with open(args.json_file, encoding="utf-8") as f:
        res = json.load(f)
    n_new, n_upd = 0, 0
    for r in res.get("results", []):
        src = find_source(data, r["url"])
        if not src:
            if not args.add_missing:
                continue
            src = {"id": next_id(data["sources"], "S"), "url": r["url"], "final_url": None, "title": None,
                   "how": "user", "status": None, "page": None, "shot": None, "read": "none", "published": None,
                   "accessed": now(), "group": None, "kind": None, "note": None}
            data["sources"].append(src)
            n_new += 1
        src["status"] = r.get("status")
        src["http_status"] = r.get("http_status")
        src["final_url"] = r.get("final_url")
        if r.get("title") and not src.get("title"):
            src["title"] = r["title"]
        if r.get("wayback") and r["wayback"].get("url"):
            src["wayback"] = r["wayback"]["url"]
        src["checked_at"] = r.get("checked_at")
        n_upd += 1
    save(args, data)
    print(f"imported {n_upd} results ({n_new} new sources)")


def cmd_import_pages(args):
    data = load(args)
    n = 0
    for jp in sorted(glob.glob(os.path.join(args.out, "pages", "*.json"))):
        with open(jp, encoding="utf-8") as f:
            meta = json.load(f)
        # Match by URL only: fetch_page.py's auto ids (S01_host) are not ledger ids.
        src = find_source(data, meta.get("url", ""))
        if not src:
            if not args.add_missing:
                continue
            src = {"id": next_id(data["sources"], "S"), "url": meta["url"], "final_url": None, "title": None,
                   "how": "fetch", "status": None, "page": None, "shot": None, "read": "none", "published": None,
                   "accessed": meta.get("fetched_at") or now(), "group": None, "kind": None, "note": None}
            data["sources"].append(src)
        src["page"] = os.path.relpath(meta["page_file"], args.out) if meta.get("page_file") else src.get("page")
        src["final_url"] = meta.get("final_url") or src.get("final_url")
        src["title"] = src.get("title") or meta.get("title")
        src["published"] = src.get("published") or meta.get("published")
        src["fetch_warnings"] = meta.get("warnings") or []
        src["text_chars"] = meta.get("full_text_chars")
        # An error page, bot challenge, login wall or empty JS shell is not "read".
        unusable = meta.get("looks_like_error_page") or meta.get("looks_like_blocked")             or meta.get("looks_like_login_wall") or meta.get("looks_like_js_shell")             or (meta.get("full_text_chars") or 0) < 200
        if src.get("read") in (None, "none", "snippet") and not unusable:
            src["read"] = "text"
        if unusable and src.get("read") == "text":
            src["read"] = "none"
        n += 1
    save(args, data)
    print(f"imported {n} page records")


def cmd_add_claim(args):
    data = load(args)
    support = [s.strip() for s in (args.support or "").split(",") if s.strip()]
    contra = [s.strip() for s in (args.contra or "").split(",") if s.strip()]
    for sid in support + contra:
        if not find_source(data, sid):
            sys.exit(f"unknown source id {sid}; add-source it first")
    if args.confidence and args.confidence not in VALID_CONF:
        sys.exit(f"--confidence must be one of {sorted(VALID_CONF)}")
    claim = {"id": args.id or next_id(data["claims"], "C"), "text": args.text, "support": support, "contra": contra,
             "quote": args.quote, "quote_from": args.quote_from or (support[0] if (args.quote and len(support) == 1) else None),
             "quote_verified": None, "confidence": args.confidence, "basis": args.basis, "as_of": args.as_of,
             "note": args.note, "added_at": now()}
    verify_quote(args, data, claim)
    data["claims"].append(claim)
    save(args, data)
    print(json.dumps({k: claim[k] for k in ("id", "text", "support", "contra", "quote_verified", "quote_check", "confidence")
                      if k in claim}, ensure_ascii=False))


def cmd_set_claim(args):
    data = load(args)
    claim = find_claim(data, args.claim)
    if not claim:
        sys.exit(f"unknown claim {args.claim}")
    if args.support is not None:
        claim["support"] = [s.strip() for s in args.support.split(",") if s.strip()]
    if args.contra is not None:
        claim["contra"] = [s.strip() for s in args.contra.split(",") if s.strip()]
    for k in ("text", "quote", "quote_from", "confidence", "basis", "as_of", "note"):
        v = getattr(args, k, None)
        if v is not None:
            claim[k] = v
    if claim.get("confidence") and claim["confidence"] not in VALID_CONF:
        sys.exit(f"--confidence must be one of {sorted(VALID_CONF)}")
    verify_quote(args, data, claim)
    save(args, data)
    print(json.dumps(claim, ensure_ascii=False))


def validate(args, data):
    errors, warnings = [], []
    cited = {}
    for c in data["claims"]:
        for sid in c["support"] + c["contra"]:
            cited.setdefault(sid, []).append(c["id"])
    for s in data["sources"]:
        sid = s["id"]
        is_cited = sid in cited
        if s.get("how") == "memory" and not s.get("status"):
            errors.append(f"{sid}: URL came from memory and was never checked (run check_links.py)")
        if is_cited:
            if s.get("status") in DEAD_STATUSES:
                errors.append(f"{sid}: cited by {cited[sid]} but link status is {s['status']}")
            if s.get("status") == "BLOCKED" and s.get("read") in ("none", "snippet"):
                warnings.append(f"{sid}: BLOCKED for scripts and not read another way; use screenshot.py/--browser or say so in the answer")
            if s.get("read") in (None, "none"):
                errors.append(f"{sid}: cited by {cited[sid]} but never read (no page text, no screenshot)")
            elif s.get("read") == "snippet":
                warnings.append(f"{sid}: cited by {cited[sid]} on the basis of a search snippet only; fetch the page before relying on it")
            if not s.get("status"):
                warnings.append(f"{sid}: link never checked with check_links.py (may still be fine if fetched OK)")
            if s.get("fetch_warnings"):
                warnings.append(f"{sid}: fetch warnings: {'; '.join(s['fetch_warnings'])}")
        elif s.get("read") not in (None, "none"):
            pass  # read but unused; fine
    groups = {}
    for s in data["sources"]:
        groups[s["id"]] = s.get("group") or s["id"]
    for c in data["claims"]:
        cid = c["id"]
        if not c["support"]:
            errors.append(f"{cid}: no supporting source (either add one or state in the answer that it is unverified)")
        if c.get("quote") and c.get("quote_verified") is False:
            errors.append(f"{cid}: quote not found in fetched text of {c.get('quote_from')} ({c.get('quote_check')})")
        if not c.get("quote") and c["support"]:
            warnings.append(f"{cid}: no quote recorded; where on the page does the support come from?")
        indep = {groups[s] for s in c["support"] if s in groups}
        if c.get("confidence") == "high" and len(indep) < 2:
            warnings.append(f"{cid}: confidence=high with only {len(indep)} independent source group(s); "
                            f"lower it or explain why one primary source suffices")
        if not c.get("confidence"):
            warnings.append(f"{cid}: no confidence set")
        if not c.get("as_of") and not data.get("cutoff"):
            warnings.append(f"{cid}: no as_of date; time-sensitive claims need one")
    return errors, warnings


def cmd_validate(args):
    data = load(args)
    errors, warnings = validate(args, data)
    for e in errors:
        print("ERROR   " + e)
    for w in warnings:
        print("WARNING " + w)
    n_read = sum(1 for s in data["sources"] if s.get("read") not in (None, "none"))
    print(f"\nsources: {len(data['sources'])} registered, {n_read} read; claims: {len(data['claims'])}; "
          f"errors: {len(errors)}; warnings: {len(warnings)}")
    return 1 if errors else 0


def cmd_render(args):
    data = load(args)
    zh = args.lang == "zh"
    cited = set()
    for c in data["claims"]:
        cited.update(c["support"] + c["contra"])
    print("## " + ("来源" if zh else "Sources"))
    for s in data["sources"]:
        if args.cited_only and s["id"] not in cited:
            continue
        read = s.get("read") or "none"
        read_zh = {"none": "未读取", "snippet": "仅摘要", "text": "已读正文", "screenshot": "已看截图", "both": "正文+截图"}[read]
        status = s.get("status") or ("unchecked" if not zh else "未检测")
        acc = (s.get("accessed") or "")[:10]
        pub = s.get("published") or ("unknown" if not zh else "未知")
        title = s.get("title") or s["url"]
        url = s.get("final_url") or s["url"]
        if zh:
            print(f"- [{s['id']}] {title} — {url} （发布：{pub}；访问：{acc}；链接：{status}；{read_zh}）")
        else:
            print(f"- [{s['id']}] {title} — {url} (published: {pub}; accessed: {acc}; link: {status}; read: {read})")
    print()
    print("## " + ("论断核验表" if zh else "Claims"))
    hdr = "| ID | " + ("论断" if zh else "Claim") + " | " + ("支持" if zh else "Support") + " | " + ("反证" if zh else "Contra") + \
          " | " + ("原文已核" if zh else "Quote verified") + " | " + ("可信度" if zh else "Confidence") + " |"
    print(hdr)
    print("|---|---|---|---|---|---|")
    for c in data["claims"]:
        qv = c.get("quote_verified")
        qv_s = ("是" if zh else "yes") if qv else (("否" if zh else "no") if qv is False else "—")
        print(f"| {c['id']} | {c['text']} | {', '.join(c['support']) or '—'} | {', '.join(c['contra']) or '—'} | "
              f"{qv_s} | {c.get('confidence') or '—'} |")


def cmd_show(args):
    print(json.dumps(load(args), ensure_ascii=False, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="web-evidence", help="evidence directory holding ledger.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("--question", required=True); p.add_argument("--cutoff")
    p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_init)

    p = sub.add_parser("add-source"); p.add_argument("url"); p.add_argument("--id"); p.add_argument("--title")
    p.add_argument("--how", default="search", choices=["search", "fetch", "browser", "screenshot", "user", "memory"])
    p.add_argument("--group"); p.add_argument("--kind", choices=["primary", "secondary", "tertiary"]); p.add_argument("--note")
    p.set_defaults(fn=cmd_add_source)

    p = sub.add_parser("set-source"); p.add_argument("source")
    for k in ("title", "status", "page", "shot", "shot_text", "read", "published", "group", "note", "final_url"):
        p.add_argument("--" + k.replace("_", "-"), dest=k)
    p.add_argument("--kind", choices=["primary", "secondary", "tertiary"])
    p.add_argument("--how", choices=["search", "fetch", "browser", "screenshot", "user", "memory"])
    p.set_defaults(fn=cmd_set_source)

    p = sub.add_parser("import-check"); p.add_argument("json_file"); p.add_argument("--add-missing", action="store_true")
    p.set_defaults(fn=cmd_import_check)

    p = sub.add_parser("import-pages"); p.add_argument("--add-missing", action="store_true"); p.set_defaults(fn=cmd_import_pages)

    p = sub.add_parser("add-claim"); p.add_argument("text"); p.add_argument("--id"); p.add_argument("--support")
    p.add_argument("--contra"); p.add_argument("--quote"); p.add_argument("--quote-from", dest="quote_from")
    p.add_argument("--confidence"); p.add_argument("--basis"); p.add_argument("--as-of", dest="as_of"); p.add_argument("--note")
    p.set_defaults(fn=cmd_add_claim)

    p = sub.add_parser("set-claim"); p.add_argument("claim"); p.add_argument("--text"); p.add_argument("--support")
    p.add_argument("--contra"); p.add_argument("--quote"); p.add_argument("--quote-from", dest="quote_from")
    p.add_argument("--confidence"); p.add_argument("--basis"); p.add_argument("--as-of", dest="as_of"); p.add_argument("--note")
    p.set_defaults(fn=cmd_set_claim)

    p = sub.add_parser("validate"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("render"); p.add_argument("--lang", default="zh", choices=["zh", "en"])
    p.add_argument("--cited-only", action="store_true"); p.set_defaults(fn=cmd_render)
    p = sub.add_parser("show"); p.set_defaults(fn=cmd_show)

    args = ap.parse_args(argv)
    rc = args.fn(args)
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
