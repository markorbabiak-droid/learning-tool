# ATLAS — Project Status
*Last updated: 2026-04-01*

---

## What Has Been Built

### Phase 1 — Note Engine (Complete)
The full pipeline is working end-to-end. Given any `.txt` file, ATLAS:

1. Detects the academic field and sub-domain
2. Runs an 80/20 filter via Claude API (Sonnet 4.6) to extract the ~13 most critical concepts per ~4,000 words (scales: 1 card per 300 words, min 3, max 15)
3. Generates Cornell-style notes in **telegraphic shorthand** (→, ↑/↓, &, w/, b/c) — no full sentences
4. Outputs a `reference_note` per card (plain-phrase grading target, no symbols)
5. Builds a fully self-contained, offline HTML file with:
   - Cornell note layout per concept (cue / note / summary)
   - Textarea + mic button side-by-side for Feynman practice answers
   - Web Speech API live transcription (Chrome recommended)
   - Submit button that calls Anthropic API (Haiku 4.5) to grade the answer
   - Color-coded inline diff: green = match, yellow = fuzzy, red = miss
   - Missed concepts rendered as red badges below the model answer

### Key Files
| File | Role |
|------|------|
| `src/note_engine.py` | Pipeline entry point — reads input, calls API, builds HTML |
| `src/api_client.py` | Anthropic API wrapper (Sonnet 4.6 for note generation) |
| `src/html_builder.py` | Builds the entire self-contained HTML output |
| `requirements.txt` | `anthropic`, `python-dotenv` |
| `.env` | `ANTHROPIC_API_KEY=sk-ant-...` (never commit this) |

### How to Run
```bash
python3 src/note_engine.py path/to/input.txt
# Output: data/sessions/<topic-date>/cornell.html
```

---

## Current Status

**Phase 1 is complete and tested.** Verified on:
- Short text (39-word mitochondria test)
- Research paper (~4,300 words — integrated memory/context paper)
- Claude Code research paper (~3,850 words — 13 cards, grading working)

Model assignments are locked:
- Note generation → `claude-sonnet-4-6`
- In-browser grading → `claude-haiku-4-5-20251001`

---

## Known Limitations / Watch Items

- **Grading silently skips** if `.env` API key is missing or browser is offline — it just reveals the model answer with no diff. This is intentional.
- **Mic is Chrome-only** in practice. The hint text "Mic works best in Chrome." is shown but no hard block.
- **Vector DB MCP memory pattern omitted** from card treatment at scale (noted by omission risk flag on the Claude Code session). Not a bug — just a gap in the source text.
- **No Phases 2–4 yet** (Anki export, Feynman scoring, MCAT testing).

---

## Next Steps / TODOs

### Immediate (next session)
- [ ] Review the grading output quality on the Claude Code research paper session — does Haiku 4.5 grade accurately enough, or do we need Sonnet?
- [ ] Decide if the telegraphic note style feels right after actual practice, or if it needs tuning

### Phase 2 — Anki Export
- [ ] Add `anki_export()` function to `note_engine.py`
- [ ] Output `cornell.csv` in Anki cloze format alongside the HTML
- [ ] Cloze should wrap the `reference_note` content, not the telegraphic note

### Phase 3 — Feynman Scoring
- [ ] Move grading out of the browser and into Python (optional — browser grading already works)
- [ ] Add a numeric confidence score per concept (user self-rates 1–5)
- [ ] Track scores across sessions to surface weak concepts

### Phase 4 — MCAT-Difficulty Testing
- [ ] Generate 5–10 UWorld-style multiple choice questions per session
- [ ] Add explanation panel per question (correct + why each wrong answer is wrong)
- [ ] Output as a second HTML file: `test.html`

---

## Key Decisions Made

| Decision | Reason |
|----------|--------|
| Plain string + `.replace()` for JS templates, not f-strings | JS has too many `{}` — f-strings require `{{}}` everywhere, messy |
| `\U0001F3A4` not `\uD83C\uDFA4` for 🎤 emoji | Surrogate pair causes UnicodeEncodeError on UTF-8 write |
| API key injected at build time as JS const | Avoids a backend server; works offline for everything except grading |
| `white-space: pre-line` on note text | Preserves telegraphic line breaks without `<br>` tags in the HTML |
| Haiku for grading, Sonnet for notes | Grading is a simple match/fuzzy/miss classification — Haiku is sufficient and much cheaper |
| Draft area starts visible (no trigger button) | Removes one unnecessary click; textarea is always ready |
