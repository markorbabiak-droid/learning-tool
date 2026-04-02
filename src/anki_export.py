"""
anki_export.py — Converts cornell.json into Anki-ready cloze cards.

Run: python3 src/anki_export.py data/sessions/my-topic/cornell.json
Output: data/sessions/my-topic/cornell.csv

Per-concept two-pass process:
  For each concept:
    Pass 1 — Generate cloze cards (Sonnet)
    Pass 2 — Audit Extra fields, promote testable content (Haiku)
  Then save all cards to CSV.

Skill references:
  skills/card-generation/SKILL.md  — card writing rules and prompt
  skills/extra-auditor/SKILL.md    — Extra field audit rules and prompt
  skills/card-auditor/SKILL.md     — self-audit checklist
"""

import json
import csv
import re
import sys
import os
from pathlib import Path

# Add the src/ directory to Python's import path so we can import api_client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_client import get_client, call_claude


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT TEMPLATES
#
# We use plain strings with .replace() instead of f-strings or .format()
# because both prompts contain many curly braces (Anki cloze notation +
# JSON examples). f-strings require escaping every { and } as {{ and }} —
# messy and error-prone. .replace() with named placeholders is cleaner.
#
# Full rationale for each rule lives in:
#   skills/card-generation/SKILL.md
#   skills/extra-auditor/SKILL.md
# ─────────────────────────────────────────────────────────────────────────────

CARD_GENERATION_PROMPT = """You are an expert Anki card writer. Convert the following study concept into Anki cloze deletion cards.

CONCEPT CUE (the question this concept answers):
__CUE__

REFERENCE NOTE (the plain-language fact to convert):
__REFERENCE_NOTE__

IMPORTANCE (what this concept predicts or explains):
__IMPORTANCE__

──────────────────────────────────────────────────────
CLOZE LOGIC
──────────────────────────────────────────────────────
- {{c1::text}} = the single most important fact being tested — the harder thing to remember
- {{c2::text}} = supporting detail, secondary label, or explanatory context revealed together
- When two things are paired (name ↔ definition, label ↔ meaning), put both in the same cloze number so they're revealed together
- Always ask: "which half of this pair is harder to retrieve?" — that half becomes c1
- Short factual: {{c2::Fraternal}} twins are {{c1::dizygotic}}
- Mechanistic: The myoglobin curve is {{c2::*hyperbolic*}} because {{c1::it only has **one** heme group and cannot exhibit cooperative binding}}

──────────────────────────────────────────────────────
CARD INTEGRITY RULES
──────────────────────────────────────────────────────
- One clearly testable fact per card — if you feel the urge to use "and" in a cloze, split into two cards
- Never put the most important information only in the Extra field — if it matters, it needs its own card
- For every concept, create at least one failure-mode card: "Without X, Y fails because {{c1::...}}"
- Test retrieval, not recognition — the card should force the reader to generate the answer from scratch

Cover all applicable angles for this concept:
  - What it is (definition)
  - How it works (mechanism)
  - Why it matters (consequence/stakes)
  - What it's confused with (contrast)
  - What breaks without it (failure mode)

Not every concept needs all five — use judgment.

──────────────────────────────────────────────────────
FORMATTING RULES
──────────────────────────────────────────────────────
- Bold (**text**) truly critical terms or numbers
- Italics for technical descriptors (curve shapes, categories)
- Write as natural flowing sentences, not bullet points
- One clear testable fact per card — max ~25 words before cloze markup

──────────────────────────────────────────────────────
EXTRA FIELD RULES
──────────────────────────────────────────────────────
- Add brief clarifying context (abbreviation expansions, synonyms, alternative terms)
- Write [image] as a placeholder where a diagram would help
- Do NOT put testable facts here — those become their own cards

──────────────────────────────────────────────────────
CONTENT TYPE GUIDE
──────────────────────────────────────────────────────
- factual-definition → test term against meaning, or paired labels (name ↔ definition)
- mechanistic-process → cloak the why and how, test reasoning chains and cause-effect
- sequential-stepwise → test order of steps, what comes before/after, what triggers each step
- conceptual-theoretical → test the core principle and what it explains or predicts
- comparative → test what distinguishes two similar things (A does X while B does Y)
- numerical-quantitative → bold the number, cloak the unit or context it applies to
- failure-mode → test what breaks, why, and what the consequence is

──────────────────────────────────────────────────────
SELF-AUDIT (apply before finalizing each card)
──────────────────────────────────────────────────────
- Is c1 the harder thing to retrieve, not the easier one?
- Does this card test retrieval or just recognition?
- Is anything important hiding in the Extra field that should be its own card?
- Is this card testing one thing, or secretly two?
- Does this concept need a failure-mode card that hasn't been written yet?

──────────────────────────────────────────────────────
PRE-OUTPUT CHECKLIST (run on the full concept card set before returning)
──────────────────────────────────────────────────────
Run these three checks after drafting all cards, before finalizing output.
Prevention at generation is cheaper than correction at audit.

1. NEAR-DUPLICATE SCAN
   Scan for cards that test the same underlying fact from slightly different angles.
   If two cards would have the same correct answer, merge or delete one.
   Depth is fine — redundancy is waste:
     - 10 cards covering 10 distinct angles = good
     - 10 cards covering 3 angles with repetition = bad
   Target: 8-10 cards per concept maximum.
   If you exceed 10, remove near-duplicates first.
   If genuinely distinct facts justify going over 10, justify each card beyond card 8.

2. DUPLICATE c1 CHECK
   Check every card for two {{c1::...}} deletions testing DIFFERENT facts.
   That is a cloze logic error — one must become c2.
   The only valid reason for two c1s: both deletions reveal as a single unified answer.

3. SEMICOLON / TWO-DEFINITION CHECK
   If a single cloze deletion contains a semicolon, "and", or defines two separate
   things — split it into two cards. One cloze = one retrievable fact, no exceptions.

──────────────────────────────────────────────────────
OUTPUT FORMAT
──────────────────────────────────────────────────────
Return ONLY a valid JSON array. No prose, no explanation, no markdown fences.
The response must start with [ and end with ].

[
  {
    "text": "Card text with {{c1::cloze}} deletions",
    "extra": "Context or explanation",
    "content_type": "mechanistic-process"
  }
]"""


EXTRA_AUDIT_PROMPT = """You are auditing Anki flashcard Extra fields for testable content that should become its own card.

Here are the current cards and their Extra fields:
__CARDS_JSON__

──────────────────────────────────────────────────────
AUDIT RULES
──────────────────────────────────────────────────────
For each Extra field, ask all four questions:
1. Does it contain a number, threshold, or quantity? → write a numerical-quantitative card
2. Does it compare two things? → write a comparative card
3. Does it state a cause-effect or consequence? → write a mechanistic-process or failure-mode card
4. Does it name a synonym, alias, or alternative term worth testing? → write a factual-definition card

Only promote content that makes a genuinely useful study card.
Do NOT promote: abbreviation expansions, pronunciation hints, [image] placeholders.
When you promote content to a card, remove that content from the Extra field.

──────────────────────────────────────────────────────
OUTPUT FORMAT
──────────────────────────────────────────────────────
Return ONLY valid JSON. No prose, no explanation, no markdown fences.

If nothing should be promoted:
{"promoted_cards": [], "updated_extras": {}}

If content should be promoted:
{"promoted_cards": [{"text": "cloze sentence", "extra": "brief context if needed", "content_type": "comparative", "promoted_from_card_index": 3}], "updated_extras": {"3": "updated extra for card index 3 with the promoted content removed"}}"""


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def load_json(file_path):
    """
    Read cornell.json from disk and return the notes dictionary.
    Exits with a clear message if the file doesn't exist.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"\n  Error: File not found: {file_path}")
        print("  Make sure you've run note_engine.py first to generate cornell.json")
        sys.exit(1)

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def make_concept_slug(cue, index):
    """
    Build a short, readable Anki tag from the concept's cue question.

    Strips common question openers (What, How, Why, etc.) that add no meaning
    to a tag. Takes the first 5 meaningful words, lowercased and hyphen-joined.
    Falls back to 'concept-{n}' if the cue is empty.

    Example:
      "What are the three major stages of aerobic respiration?"
      → "three-major-stages-aerobic-respiration"
    """
    if not cue:
        return f'concept-{index + 1}'

    # Remove punctuation, lowercase
    text = re.sub(r'[^\w\s]', '', cue.lower())
    words = text.split()

    # Strip common question starters that add no tag meaning
    starters = {'what', 'how', 'why', 'when', 'where', 'which', 'does', 'is',
                'are', 'the', 'a', 'an', 'do', 'can', 'if', 'in', 'will'}
    meaningful = [w for w in words if w not in starters]

    slug = '-'.join(meaningful[:5])
    return slug[:50] if slug else f'concept-{index + 1}'


def build_card_prompt(concept):
    """
    Inject one concept's data into the card generation prompt.
    Uses .replace() because the prompt contains Anki cloze braces and JSON
    examples — f-strings would require escaping every { and } as {{ and }}.
    """
    return (CARD_GENERATION_PROMPT
            .replace('__CUE__', concept.get('cue', ''))
            .replace('__REFERENCE_NOTE__', concept.get('reference_note', concept.get('note', '')))
            .replace('__IMPORTANCE__', concept.get('importance', '')))


def build_audit_prompt(cards):
    """
    Inject the current card batch into the Extra audit prompt.
    Only passes index, text, and extra — content_type is internal metadata.
    """
    cards_for_audit = [
        {'index': i, 'text': c.get('text', ''), 'extra': c.get('extra', '')}
        for i, c in enumerate(cards)
    ]
    return EXTRA_AUDIT_PROMPT.replace('__CARDS_JSON__', json.dumps(cards_for_audit, indent=2))


def parse_json_response(response_string, debug_path=None):
    """
    Extract a JSON value from Claude's response.

    Strips markdown code fences if Claude hallucinated them, then parses.
    Normalises the result: the card generation prompt returns a JSON array;
    older prompts returned {"cards": [...]}. Both are accepted and always
    returned as a plain Python value (list or dict) — callers decide which
    they expect.

    On failure: logs the raw response to debug_path and returns None.
    """
    text = response_string.strip()

    # Strip markdown fences — Claude sometimes adds these even when told not to.
    # Handles ```json, ```JSON, ``` with or without a language tag.
    if text.startswith('```'):
        lines = text.split('\n')
        # Drop the opening fence line and the closing fence line
        text = '\n'.join(lines[1:-1]).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        if debug_path:
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(response_string)
            print(f"    Warning: Could not parse Claude's JSON response.")
            print(f"    Raw response saved to: {debug_path}")
            print(f"    Parse error: {e}")
        return None


def extract_cards(result):
    """
    Normalise the parsed JSON from a card generation call into a plain list.

    Accepts both the new format (JSON array) and the legacy format
    ({"cards": [...]}) so old debug files stay compatible.
    Returns an empty list if the result is neither.
    """
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get('cards', [])
    return []


def generate_cards_for_concept(client, concept, concept_index, session_dir):
    """
    Call Claude (Sonnet) to generate cloze cards for one concept.

    On a JSON parse failure, retries the API call once before giving up.
    This catches transient formatting errors without silently losing a concept.

    Returns a list of card dicts. Returns empty list if both attempts fail.
    """
    prompt = build_card_prompt(concept)
    debug_path = os.path.join(session_dir, f'debug_cards_concept_{concept_index}.txt')

    response = call_claude(client, prompt, max_tokens=4000)
    result = parse_json_response(response, debug_path)

    if result is None:
        # Retry once — transient formatting errors are common enough to warrant this
        print(f"    Parse failed — retrying concept {concept_index + 1}...")
        response = call_claude(client, prompt, max_tokens=4000)
        result = parse_json_response(response, debug_path)

    if result is None:
        print(f"    Both attempts failed. Skipping concept {concept_index + 1}.")
        return []

    return extract_cards(result)


def run_extra_audit(client, concept_cards, session_dir, concept_index):
    """
    Audit Extra fields for one concept's card batch.

    Called immediately after card generation for each concept — per-concept
    chunking keeps payloads small (typically 3-8 cards per concept) and
    contains errors to one concept at a time rather than the whole session.

    Uses Haiku — promotion/classification is a simpler task than card
    generation and doesn't require Sonnet-level reasoning.

    Returns (updated_cards, number_promoted).
    """
    if not concept_cards:
        return concept_cards, 0

    prompt = build_audit_prompt(concept_cards)
    debug_path = os.path.join(session_dir, f'debug_audit_concept_{concept_index}.txt')

    # Haiku for audit — cheaper, sufficient for this classification task
    response = call_claude(client, prompt, max_tokens=4000, model="claude-haiku-4-5-20251001")
    result = parse_json_response(response, debug_path)

    if result is None:
        print(f"    Warning: Extra audit failed for concept {concept_index + 1}. Skipping.")
        return concept_cards, 0

    # Update extras in-place for any cards where content was promoted out
    updated_extras = result.get('updated_extras', {})
    for idx_str, new_extra in updated_extras.items():
        idx = int(idx_str)
        if idx < len(concept_cards):
            concept_cards[idx]['extra'] = new_extra

    # Append promoted cards to this concept's batch
    promoted_cards = result.get('promoted_cards', [])
    for card in promoted_cards:
        card.pop('promoted_from_card_index', None)
        concept_cards.append(card)

    return concept_cards, len(promoted_cards)


# ─────────────────────────────────────────────────────────────────────────────
# ANKI PACKAGE CONSTANTS
#
# These integers must never change after first use. Anki uses them to identify
# the model and deck across imports — changing them creates duplicates instead
# of updating existing cards.
# ─────────────────────────────────────────────────────────────────────────────
ANKI_MODEL_ID = 1607392319
ANKI_DECK_ID  = 2059400110


def save_apkg(all_cards, output_path, topic):
    """
    Write all cards to an Anki .apkg package file using genanki.

    Uses a Cloze note type — required for {{c1::...}} deletions to render
    correctly in Anki. A standard Q&A model would display the raw syntax
    instead of hiding the cloze text.

    Model fields:
      Text  — the cloze sentence (rendered as a cloze card in Anki)
      Extra — shown below the answer after reveal

    The model_id and deck_id are hardcoded. Do not change them — Anki uses
    these integers to match imported cards to existing notes and decks.
    """
    import genanki

    # Define the Cloze note model
    model = genanki.Model(
        ANKI_MODEL_ID,
        'ATLAS Cloze',
        model_type=genanki.Model.CLOZE,
        fields=[
            {'name': 'Text'},
            {'name': 'Extra'},
        ],
        templates=[
            {
                'name': 'ATLAS Cloze Card',
                'qfmt': '{{cloze:Text}}',
                'afmt': '{{cloze:Text}}<br><hr><br>{{Extra}}',
            }
        ]
    )

    deck = genanki.Deck(ANKI_DECK_ID, f'ATLAS - {topic}')

    for card in all_cards:
        note = genanki.Note(
            model=model,
            fields=[
                card.get('text', ''),
                card.get('extra', ''),
            ]
        )
        deck.add_note(note)

    genanki.Package(deck).write_to_file(output_path)


def save_csv(all_cards, output_path, topic):
    """
    Write all cards to a tab-separated file that Anki can import directly.

    Tags format: atlas {topic-slug} {concept-slug}
    This lets you filter cards by topic or by specific concept in Anki's browser.

    Anki import header lines tell Anki which note type, deck, and columns to use.
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        f.write('#separator:tab\n')
        f.write('#html:true\n')
        f.write('#notetype:Cloze\n')
        f.write(f'#deck:ATLAS - {topic}\n')
        f.write('#columns:Text\tBack Extra\tTags\n')

        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)

        topic_tag = topic.replace(' ', '-').lower()

        for card in all_cards:
            text = card.get('text', '')
            extra = card.get('extra', '')
            concept_slug = card.get('concept_slug', 'unknown')
            tags = f'atlas {topic_tag} {concept_slug}'

            writer.writerow([text, extra, tags])


def main(json_path):
    """
    Entry point for the Anki export pipeline.

    Per-concept loop:
      For each concept:
        1. Generate cloze cards (Sonnet)
        2. Immediately audit Extra fields (Haiku)
        3. Tag all cards with the concept slug
      Then save everything to cornell.csv.
    """
    print()
    print('═' * 47)
    print('  ATLAS — Anki Cloze Export')
    print('═' * 47)

    # ── Load ──────────────────────────────────────────
    print('\nLoading notes...')
    notes = load_json(json_path)

    topic = notes.get('topic', 'Unknown Topic')
    concepts = notes.get('critical_concepts', [])
    session_dir = str(Path(json_path).parent)

    print(f'  Topic:    {topic}')
    print(f'  Concepts: {len(concepts)}')

    if not concepts:
        print('\n  Error: No critical_concepts found in the JSON.')
        print('  Make sure you are pointing at a valid cornell.json file.')
        sys.exit(1)

    client = get_client()
    all_cards = []
    total_promoted = 0

    # ── Per-concept loop ──────────────────────────────
    print(f'\nProcessing concepts...')
    print(f'  (Generate → Audit per concept. Usually 20-40s per concept.)')

    for i, concept in enumerate(concepts):
        concept_slug = make_concept_slug(concept.get('cue', ''), i)
        cue_preview = concept.get('cue', '')[:65]
        print(f'\n  [{i + 1}/{len(concepts)}] {cue_preview}...')

        # Pass 1: Generate cards (Sonnet)
        cards = generate_cards_for_concept(client, concept, i, session_dir)
        print(f'          {len(cards)} card{"s" if len(cards) != 1 else ""} generated')

        # Pass 2: Audit extras (Haiku)
        cards, promoted = run_extra_audit(client, cards, session_dir, i)
        if promoted > 0:
            print(f'          +{promoted} promoted from Extra  →  {len(cards)} total')
        total_promoted += promoted

        # Tag every card with its concept slug so Anki can filter by concept
        for card in cards:
            card['concept_slug'] = concept_slug

        all_cards.extend(cards)

    # ── Save ──────────────────────────────────────────
    print(f'\n{"─" * 47}')
    print(f'  {len(all_cards)} total cards  ({total_promoted} promoted from Extra)')

    csv_path  = os.path.join(session_dir, 'cornell.csv')
    apkg_path = os.path.join(session_dir, 'cornell.apkg')

    save_csv(all_cards, csv_path, topic)
    print(f'\n  ✓ {csv_path}')

    save_apkg(all_cards, apkg_path, topic)
    print(f'  ✓ {apkg_path}')

    print()
    print('═' * 47)
    print('  Done. To import into Anki:')
    print('  File → Import → select cornell.apkg')
    print('  (cornell.csv also available for manual import)')
    print('═' * 47)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print()
        print('  Usage: python3 src/anki_export.py data/sessions/my-topic/cornell.json')
        print()
        sys.exit(1)

    main(sys.argv[1])
