# ATLAS — Session Reviews

---

## 2026-04-02

### 1. Completed Work

| File | Status | What changed and why |
|---|---|---|
| `src/anki_export.py` | Created | Primary Phase 2 deliverable. Full pipeline: chunk source text → generate cloze cards per chunk (Sonnet) → audit Extra fields per chunk (Haiku) → export `.csv` + `.apkg`. Iterated heavily on prompts, architecture, and error handling throughout the session. |
| `src/api_client.py` | Modified | Added optional `model` parameter to `call_claude()` so the audit pass can use Haiku without touching note generation. Added optional `system` parameter to separate rules from source data in API calls — fixes instruction bleed. |
| `requirements.txt` | Modified | Added `genanki` for `.apkg` export. |
| `.gitignore` | Modified | Added `data/sessions/*` (generated, reproducible), `data/debug_response.txt` + `data/sessions/debug_*.txt` (API failure artifacts), and scratch files. |
| `skills/card-generation/SKILL.md` | Created | Reference doc capturing full card writing rules, cloze logic, content type guide, pre-output checklist, and negative constraints. Canonical source for prompt design decisions. |
| `skills/extra-auditor/SKILL.md` | Created | Reference doc for the Extra field audit pass: the four trigger questions, promote-don't-keep rule, architecture rationale (per-chunk, Haiku model). |
| `skills/card-auditor/SKILL.md` | Created | Reference doc for human/automated deck review: seven audit questions including the duplicate c1 error check and compound cloze check added late in the session. |
| `ClaudeCode_CheatSheet.txt` | Added | Source material for the Phase 2 deck. Lives in repo root so the pipeline command is reproducible. |

---

### 2. Current State

**Build:** All four modules import cleanly. 13/13 smoke tests pass (imports, chunking, slugging, JSON parsing, extract_cards, session dir creation, API signature).

**Pipeline:** Fully functional end-to-end. Running:
```bash
python3 src/anki_export.py ClaudeCode_CheatSheet.txt
```
produces a `cornell.apkg` ready to drag into Anki. Output verified: 143 cards from 17 chunks, dark-slate CSS styling, `.extra-context` field separation.

**Known issues / TODOs:**
- No formal test suite (`pytest` or equivalent). All tests are ad-hoc smoke tests run inline.
- Chunk slug for separator-only sections (e.g. `===...`) produces unhelpful slugs like `chunk-3`. The first real content line is the better slug source — not yet fixed.
- `ClaudeCode_CheatSheet.txt` and `.gitignore` changes are staged but not yet committed (pending approval at end of session).
- Card quality has not yet been evaluated inside Anki itself — CSS rendering and cloze reveal behavior are untested in the actual app.

---

### 3. Roadblocks

**Token limit truncation (hit twice)**
First runs with `max_tokens=2000` produced truncated JSON — Claude hit the limit mid-card and the response was unparseable. Bumped to 4000 for both generation and audit. Root cause: the mitochondria test concept had an unusually long `importance` field that triggered long card sets.

**Instruction bleed**
The model was generating flashcards *about* the cloze formatting rules themselves (e.g. cards testing what `{{c1::}}` means). Root cause: rules and source data were mixed in the same user turn. Fixed by moving all rules into the `system` parameter and putting only the source data in the `messages` user turn. Required understanding the Anthropic API system/user separation and updating `call_claude()` signature.

**Mad Libs style cloze errors**
The model kept using `{{c1::X}}` and `{{c2::Y}}` as sequential sentence blanks ("fill in both words") rather than a primary fact + simultaneous hint. Required adding explicit WRONG/RIGHT examples to the prompt and a NEVER VIOLATE header to force the constraint. Took two prompt iterations to stick.

**Wrong source file**
An early test run used `/Users/markobabiak/Desktop/ClaudeCode_CheatSheet.txt` (no longer exists) instead of `ClaudeCode_CheatSheet.txt` inside the project. The pipeline succeeded silently because the file had been copied to a session folder earlier — the error wasn't caught until the user flagged it.

**Edit tool drift**
One `Edit` call failed because the file had been modified since the last `Read` and the exact string no longer matched. Required re-reading the full file and rewriting the target section. Lesson: always re-read before editing after any intervening modifications.

**Audit architecture iteration**
The first audit design audited all cards for a session in one call. This hit token limits on larger sessions (65+ cards). Redesigned to per-concept / per-chunk audit (one call per chunk, Haiku model). This also improved error containment — a single failed audit no longer silences the rest of the session.

---

### 4. Next Steps

**First command tomorrow:**
```bash
# Commit the pending .gitignore and source file changes
git add .gitignore ClaudeCode_CheatSheet.txt
git commit -m "Add source material and exclude debug artifacts from git"
git push
```

**Then:**
1. **Import `cornell.apkg` into Anki and review 10-15 cards manually.** Check that CSS renders correctly (dark background, green cloze, muted Extra), cloze reveals work, and no cards about formatting instructions slipped through. Report any quality issues back for prompt tuning.
2. **Fix chunk slug for separator-only sections.** Chunks that start with `===` or `---` get meaningless slugs. The fix is to skip leading punctuation/separator lines when building the slug and fall through to the first real content line.
3. **Decide on Phase 3 scope.** STATUS.md lists Feynman scoring (move grading to Python, add confidence self-rating 1–5, track weak concepts across sessions). Evaluate whether the in-browser grading already in `html_builder.py` is sufficient or if Python-side scoring is worth building.
