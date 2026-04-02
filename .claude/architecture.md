# ATLAS — System Architecture (North Star)

*This is the reference map for every design decision in the project.*

---

## Pipeline Overview

```
[Raw Input Text]
       |
       v
  Phase 1: Cornell Notes
  - Extract key concepts (80/20 rule: 20% of ideas = 80% of value)
  - Organize into: Cue Column | Notes Column | Summary
  - Output: HTML file that renders as a real Cornell note page
       |
       v
  Phase 2: Anki Cloze Cards
  - Convert key facts into cloze-deletion flashcards
    (e.g. "The mitochondria is the {{c1::powerhouse}} of the cell")
  - Output: CSV file importable directly into Anki
       |
       v
  Phase 3: Feynman Practice
  - Present concepts back to the user one at a time
  - User explains in their own words
  - System scores the explanation and identifies gaps
  - Output: HTML interactive practice session with scoring
       |
       v
  Phase 4: MCAT-Style Test
  - Generate passage-based questions at MCAT difficulty
  - Include UWorld-style explanations (why right AND why wrong)
  - Output: HTML test file with score tracking and review mode
```

---

## Data Flow

```
/data/sessions/[topic-date]/
  ├── input.txt          — the raw text you paste in
  ├── cornell.json       — structured notes data
  ├── cornell.html       — rendered Cornell notes (open in browser)
  ├── anki_export.csv    — flashcards ready for Anki import
  ├── feynman.json       — practice session data
  ├── feynman.html       — interactive Feynman practice page
  ├── test.json          — test questions and answers
  └── test.html          — interactive MCAT-style test
```

---

## Design Principles

1. **Offline-first**: Every output file works with no internet connection
2. **Single-file outputs**: Each HTML file is fully self-contained (CSS and JS embedded)
3. **Human-readable data**: JSON and CSV files you can open and read yourself
4. **One session = one folder**: Easy to find, back up, or delete any study session
5. **No black boxes**: Every step of the pipeline is a separate, readable Python script

---

## Phase Details

### Phase 1 — Cornell Notes
- 80/20 filter: surface the highest-yield concepts
- Three-column layout: Cues (questions) | Notes (answers/details) | Summary
- Color-coded by concept importance

### Phase 2 — Anki Cards
- Cloze format: `{{c1::answer}}` syntax Anki understands natively
- One card per key fact
- Tags by topic for easy deck organization

### Phase 3 — Feynman Practice
- Shows one concept at a time
- Text box for user's explanation
- Scoring rubric: completeness, accuracy, simplicity
- Flags gaps for review

### Phase 4 — MCAT Test
- Passage-based (like real MCAT)
- 4-answer multiple choice
- Each answer has a full explanation
- Score tracked per session, reviewable after completion
