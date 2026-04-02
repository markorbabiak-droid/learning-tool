# SKILL: Extra Field Auditor

**Used by:** `src/anki_export.py` — Pass 2 of the per-concept loop  
**Model:** Haiku (classification task, not generation)  
**Input:** All cards for one concept `{index, text, extra}`  
**Output:** JSON with `promoted_cards` array and `updated_extras` map  
**Timing:** Runs immediately after card generation, before moving to the next concept

---

## Purpose

Scans every Extra field for content that is genuinely testable — and promotes it
to a new card. Extra fields should contain only non-testable clarifying context.
If a fact is worth knowing, it needs its own card.

---

## The Four Trigger Questions

Ask all four for every Extra field:

1. **Number/threshold/quantity?** → `numerical-quantitative` card
2. **Comparison between two things?** → `comparative` card
3. **Cause-effect or consequence?** → `mechanistic-process` or `failure-mode` card
4. **Synonym, alias, or alternative term worth testing?** → `factual-definition` card

If yes to any: write the card, remove the content from Extra.

---

## What NOT to Promote

Do not promote content that is truly just clarifying context:
- Abbreviation expansions (e.g., "TCA = tricarboxylic acid")
- Pronunciation hints
- `[image]` placeholders
- Statements the learner would never be tested on

---

## Promote-Don't-Keep Rule

When content is promoted to a card, it must be **removed** from the Extra field.
The updated Extra field is returned in `updated_extras`. If the Extra becomes
empty after promotion, return an empty string for that index.

---

## Architecture Note

This audit runs per-concept (not across the whole session) to:
- Keep payloads small (typically 3–8 cards per concept)
- Contain failures — if one concept's audit fails, the rest continue
- Stay within token limits reliably

Maximum cards per audit call: 20 (enforced by per-concept chunking).

---

## Output Format

```json
{
  "promoted_cards": [
    {
      "text": "cloze sentence here",
      "extra": "brief context if needed",
      "content_type": "comparative",
      "promoted_from_card_index": 3
    }
  ],
  "updated_extras": {
    "3": "updated extra for card index 3, with promoted content removed"
  }
}
```

If nothing should be promoted: `{"promoted_cards": [], "updated_extras": {}}`
