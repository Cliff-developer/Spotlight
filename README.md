# Spotlight

A late-night game-show trivia PWA. Static files, no backend, works offline.
Questions: [Open Trivia Database](https://opentdb.com), CC BY-SA 4.0 (attribution is shown in the app).

## Replace the sample questions with the full database
```
pip install requests
python build_questions.py      # takes several minutes: the API allows 1 request / 5 s
```
It overwrites `questions.js` (the 40 hand-written samples ship by default).
Ctrl+C saves what was fetched so far. Then **bump `VERSION` in `sw.js`** (e.g. `spotlight-v2`) and push.
Question ids are hashes of category and text, so spaced-repetition progress survives re-runs.

## Deploy
Push the folder to a new repo, then Settings, Pages, Deploy from branch, `main`, root.
Everything uses relative paths, so `username.github.io/repo-name/` works.

## Rules in brief
- Round = 10 questions (fewer if the filter has fewer). Points per right answer: 5 minus hints used (min 1), +1 if answered within 5 s with the timer on. The 50/50 hint (key H) is not offered on true/false.
- Leitner boxes 0-5, gaps 0/1/3/7/16/35 days. 50% of questions are due reviews when any exist. A right answer without a hint moves up a box; a miss or timeout resets to box 0.
- Keys: 1-4 or A-D answer, Enter next, H hint.
- Always bump `VERSION` in `sw.js` when `index.html` or `questions.js` changes.
