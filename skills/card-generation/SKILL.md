# SKILL: Card Generation

**Used by:** `src/anki_export.py` — Pass 1 of the per-concept loop  
**Model:** Sonnet (creative generation task)  
**Input:** concept `cue`, `reference_note`, `importance` from cornell.json  
**Output:** JSON array of card objects `{text, extra, content_type}`

---

## Purpose

Converts one `reference_note` (plain-language fact) into a set of Anki cloze
deletion cards that together cover the concept from multiple testable angles.

---

## Cloze Logic

- `{{c1::text}}` — the single most important fact being tested. The **harder** thing to remember.
- `{{c2::text}}` — supporting detail, secondary label, or explanatory context revealed together.
- Paired facts (name ↔ definition, label ↔ meaning) go in the **same** cloze number so they reveal together.
- Always ask: *"which half of this pair is harder to retrieve?"* — that half is c1.

**Short factual example:**  
`{{c2::Fraternal}} twins are {{c1::dizygotic}}`

**Mechanistic example:**  
`The myoglobin curve is {{c2::*hyperbolic*}} because {{c1::it only has **one** heme group and cannot exhibit cooperative binding}}`

---

## Card Integrity Rules

1. One clearly testable fact per card. If you feel the urge to use "and" in a cloze, split into two cards.
2. Never put the most important information only in the Extra field — if it matters, it needs its own card.
3. For every concept, write at least one failure-mode card: *"Without X, Y fails because {{c1::...}}"*
4. Test retrieval, not recognition — the card should force the reader to generate the answer from scratch.

---

## Angles to Cover (not all required — use judgment)

| Angle | Question it answers |
|---|---|
| What it is | Definition |
| How it works | Mechanism |
| Why it matters | Consequence / stakes |
| What it's confused with | Contrast |
| What breaks without it | Failure mode |

---

## Formatting Rules

- **Bold** (`**text**`) truly critical terms or numbers
- *Italics* for technical descriptors (curve shapes, categories)
- Natural flowing sentences, not bullet points
- Max ~25 words per card before cloze markup

---

## Extra Field Rules

- Brief clarifying context only (abbreviation expansions, synonyms, [image] placeholders)
- Do **not** put testable facts here — those become their own cards
- The Extra field audit (see `extra-auditor/SKILL.md`) will catch anything that slips through

---

## Content Types

| Type | When to use |
|---|---|
| `factual-definition` | Term ↔ meaning, paired labels |
| `mechanistic-process` | Why/how something works, cause-effect chains |
| `sequential-stepwise` | Order of steps, what triggers each step |
| `conceptual-theoretical` | Core principle and what it explains or predicts |
| `comparative` | What distinguishes two similar things |
| `numerical-quantitative` | Numbers, thresholds, quantities |
| `failure-mode` | What breaks, why, and the consequence |

---

## Self-Audit (run before finalizing)

- [ ] Is c1 the **harder** thing to retrieve, not the easier one?
- [ ] Does this card test retrieval or just recognition?
- [ ] Is anything important hiding in the Extra field?
- [ ] Is this card secretly testing two things?
- [ ] Does this concept need a failure-mode card that hasn't been written yet?
