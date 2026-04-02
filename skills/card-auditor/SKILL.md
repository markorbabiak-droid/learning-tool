# SKILL: Card Auditor

**Used by:** Human review / future automated audit pass  
**Model:** Sonnet (reasoning task)  
**Input:** A completed deck of cards for one session  
**Output:** List of flagged cards with specific issues and suggested fixes

---

## Purpose

A second-opinion pass over a finished deck. The card generator and extra auditor
catch most problems, but this auditor catches subtler issues: c1/c2 swaps,
recognition-not-retrieval cards, concepts missing a failure-mode card, and
cards that are secretly testing two things.

---

## The Five Audit Questions

Run these against every card in the deck:

### 1. Is c1 the harder thing to retrieve?
c1 should be the fact the learner is most likely to blank on — the deeper,
less obvious half of the pair. If c1 is the obvious label and c2 is the
hard-to-derive mechanism, they're swapped.

**Flag:** "c1/c2 may be swapped — [c2 content] appears harder to retrieve than [c1 content]"

---

### 2. Does this card test retrieval or recognition?
A recognition card can be answered correctly just by confirming you've seen it
before. A retrieval card forces you to generate the answer from scratch.

**Red flags:**
- The cloze blank is very short (one word) and the surrounding context makes it obvious
- The answer could be guessed without knowing the material
- The card reads like a true/false question in disguise

**Flag:** "Recognition risk — the context may give away the answer"

---

### 3. Is anything important hiding in the Extra field?
The Extra field should contain only non-testable context. If Extra contains
a number, a comparison, a cause-effect statement, or an alternative term —
that content should be its own card.

**Flag:** "Promotable Extra content — '[excerpt]' could be a [type] card"

---

### 4. Is this card secretly testing two things?
If you can read the card and identify two separate facts being tested, it
needs to be split. The trigger: if removing half the cloze content would
produce a complete, valid card on its own — it's two cards.

**Flag:** "Compound card — split at '[junction point]'"

---

### 5. Does this concept have a failure-mode card?
For every major concept in the deck, there should be at least one card that
tests what breaks or goes wrong without it. Absence of failure-mode cards is
the most common gap in a deck that otherwise looks complete.

**Flag:** "Missing failure-mode card for concept: [concept name]"

---

## Coverage Check

After auditing individual cards, check the deck as a whole:

| Angle | At least one card? |
|---|---|
| What it is (definition) | |
| How it works (mechanism) | |
| Why it matters (consequence) | |
| What it's confused with (contrast) | |
| What breaks without it (failure mode) | |

If a deck has only definition and mechanism cards and no failure-mode cards,
flag the missing angles explicitly.

---

## Output Format

For each issue found:
```
Card [n]: [card text preview]
Issue: [one of the five flag types]
Suggestion: [specific fix]
```

If the deck passes all checks: "Deck passes audit — no issues found."
