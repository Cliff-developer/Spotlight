#!/usr/bin/env python3
"""Pull every question from the Open Trivia Database and write questions.js.

    pip install requests
    python build_questions.py

Questions: Open Trivia Database (opentdb.com), CC BY-SA 4.0.
The API allows one request per IP every 5 seconds, so a full pull takes
several minutes. Stop it any time with Ctrl+C: what was fetched so far is saved.
"""
import hashlib
import html
import json
import sys
import time

import requests

API = "https://opentdb.com"
GAP = 5.5  # seconds between requests (limit is 1 per 5 s, per IP)
OUT = "questions.js"

session = requests.Session()
session.headers["User-Agent"] = "spotlight-trivia-builder/1.0"
_last = 0.0


def call(path, **params):
    """GET one API endpoint, honouring the rate limit; retry on HTTP 429 / response_code 5."""
    global _last
    for attempt in range(1, 9):
        wait = GAP - (time.time() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.time()
        try:
            r = session.get(f"{API}/{path}", params=params, timeout=30)
            if r.status_code == 429:
                raise RuntimeError("HTTP 429")
            r.raise_for_status()
            data = r.json()
            if data.get("response_code") == 5:
                raise RuntimeError("response_code 5 (rate limit)")
            return data
        except (requests.RequestException, RuntimeError, ValueError) as e:
            pause = 6 * attempt
            print(f"  retry {attempt}/8 ({e}); sleeping {pause}s")
            time.sleep(pause)
    sys.exit("Giving up after 8 retries. Try again in a minute.")


def clean(r, cat):
    """Return a compact question dict, or None if the entry is malformed."""
    try:
        q = html.unescape(r["question"]).strip()
        a = html.unescape(r["correct_answer"]).strip()
        w = [html.unescape(x).strip() for x in r["incorrect_answers"]]
        typ, diff = r["type"], r["difficulty"]
    except (KeyError, TypeError):
        return None
    if typ not in ("multiple", "boolean") or diff not in ("easy", "medium", "hard"):
        return None
    if not q or not a or any(not x for x in w):
        return None
    if len(w) != (1 if typ == "boolean" else 3):
        return None
    if len({a.lower(), *[x.lower() for x in w]}) != len(w) + 1:
        return None  # duplicate answer text
    qid = hashlib.sha1(f"{cat}|{q}".encode()).hexdigest()[:8]  # stable across rebuilds
    return {"id": qid, "cat": cat, "diff": diff, "type": typ, "q": q, "a": a, "w": w}


def write(items):
    items.sort(key=lambda x: (x["cat"], x["diff"], x["id"]))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.QUESTIONS=" + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"Wrote {len(items)} questions to {OUT}")


def main():
    cats = call("api_category.php")["trivia_categories"]
    token = call("api_token.php", command="request")["token"]
    items, seen, dropped = [], set(), 0
    try:
        for c in cats:
            cid, cname = c["id"], html.unescape(c["name"])
            count = call("api_count.php", category=cid).get("category_question_count", {})
            remaining = count.get("total_question_count") or 10**6  # fall back to "until empty"
            amount, got = 50, 0
            print(f"{cname}: ~{remaining if remaining < 10**6 else '?'} questions")
            while remaining > 0:
                amount = min(amount, remaining)
                d = call("api.php", amount=amount, category=cid, token=token)
                code = d.get("response_code")
                if code == 0:
                    for r in d["results"]:
                        item = clean(r, cname)
                        key = (cname, item["q"].lower()) if item else None
                        if not item or key in seen:
                            dropped += 1
                            continue
                        seen.add(key)
                        items.append(item)
                        got += 1
                    remaining -= len(d["results"])
                elif code in (1, 4):
                    # Not enough left for this amount (or token exhausted): shrink, stop at 1.
                    if amount == 1:
                        break
                    amount = max(1, amount // 2)
                elif code == 3:  # token expired (6 h idle)
                    token = call("api_token.php", command="request")["token"]
                else:
                    print(f"  unexpected response_code {code}; skipping rest of category")
                    break
            print(f"  kept {got}")
    except KeyboardInterrupt:
        print("\nInterrupted: saving what we have.")
    write(items)
    print(f"Dropped {dropped} duplicate or malformed entries.")


if __name__ == "__main__":
    main()
