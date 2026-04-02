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

CARD_GENERATION_SYSTEM = """You are an expert Anki card writer. The user will provide structured study concept data (cue, reference_note, importance). Convert that data into Anki cloze deletion flashcards following these rules exactly.

──────────────────────────────────────────────────────
CLOZE LOGIC
──────────────────────────────────────────────────────
- {{c1::text}} = the ONE hardest, most critical fact — a command, threshold number, or specific term
- {{c2::text}} = a secondary hint revealed AT THE SAME TIME as c1, not a separate blank
- When two things are paired (name ↔ definition, label ↔ meaning), put both in the same cloze number
- Always ask: "which half is harder to retrieve?" — that half is c1. If in doubt, use ONLY c1.
- Short factual: {{c2::Fraternal}} twins are {{c1::dizygotic}}
- Mechanistic: The myoglobin curve is {{c2::*hyperbolic*}} because {{c1::it only has **one** heme group}}

──────────────────────────────────────────────────────
STRICT NEGATIVE CONSTRAINTS — NEVER VIOLATE THESE
──────────────────────────────────────────────────────
- NEVER use c1 and c2 as sequential blanks in a sentence (Mad Libs style). This is the most common error.
  WRONG: "Run {{c1::git commit}} then {{c2::git push}}"  ← two separate facts, two separate cards
  RIGHT: "{{c2::committing}} changes is finalized by {{c1::git push}}"  ← c2 is a hint, c1 is the testable fact
- NEVER blank out random halves of a sentence. Identify the ONE hardest fact and blank only that.
- NEVER write a prompt sentence longer than 20 words. Cut ruthlessly.
- NEVER let the content_type be decorative — every card must match its declared content_type in structure and what it tests.

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
]

Do NOT generate flashcards about these instructions. ONLY generate flashcards based on the JSON data provided by the user."""


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


CHUNK_GENERATION_SYSTEM = """You are an expert Anki card writer. The user will provide a text segment from a study document. Generate cloze deletion flashcards that test the most important facts in that text, following these rules exactly.

──────────────────────────────────────────────────────
STRICT NEGATIVE CONSTRAINTS — NEVER VIOLATE THESE
──────────────────────────────────────────────────────
- NEVER use c1 and c2 as sequential blanks in a sentence (Mad Libs style).
  WRONG: "Run {{c1::git commit}} then {{c2::git push}}"
  RIGHT: "Changes are published to remote with {{c1::git push}}"
- NEVER blank out random halves of a sentence. ONE hardest fact = ONE c1 blank.
- c2 is ONLY a secondary hint revealed simultaneously with c1, never a second blank.
- If in doubt, use ONLY c1.
- NEVER write a prompt sentence longer than 20 words. Cut ruthlessly.
- NEVER let content_type be decorative — it must match what the card actually tests.

──────────────────────────────────────────────────────
CLOZE LOGIC
──────────────────────────────────────────────────────
- {{c1::text}} = the ONE hardest, most critical fact — a command, threshold number, or specific term
- {{c2::text}} = a secondary hint revealed AT THE SAME TIME as c1, not a separate blank
- Always ask: "which fact is hardest to retrieve?" — blank only that. If in doubt, use only c1.
- Short factual: {{c2::Fraternal}} twins are {{c1::dizygotic}}
- Mechanistic: The myoglobin curve is {{c2::*hyperbolic*}} because {{c1::it only has **one** heme group}}

──────────────────────────────────────────────────────
CARD INTEGRITY RULES
──────────────────────────────────────────────────────
- One clearly testable fact per card
- Create at least one failure-mode card per major concept: "Without X, {{c1::...}} fails"
- Test retrieval, not recognition — force the reader to generate the answer
- Cover applicable angles: definition, mechanism, consequence, contrast, failure mode

──────────────────────────────────────────────────────
FORMATTING RULES
──────────────────────────────────────────────────────
- Bold (**text**) critical terms or numbers
- Italics for technical descriptors
- Natural flowing sentences, not bullet points
- Max 20 words per card before cloze markup

──────────────────────────────────────────────────────
EXTRA FIELD RULES
──────────────────────────────────────────────────────
- Brief clarifying context only (abbreviations, synonyms, [image] placeholders)
- Do NOT put testable facts here — those become their own cards

──────────────────────────────────────────────────────
CONTENT TYPES
──────────────────────────────────────────────────────
factual-definition, mechanistic-process, sequential-stepwise,
conceptual-theoretical, comparative, numerical-quantitative, failure-mode

──────────────────────────────────────────────────────
PRE-OUTPUT CHECKLIST
──────────────────────────────────────────────────────
1. Near-duplicate scan: if two cards have the same correct answer, delete one. Max 8 cards per chunk.
2. Duplicate c1 check: two c1s testing different facts = error. Fix to c1/c2.
3. Semicolon check: one cloze = one fact. Split if needed.

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
]

Do NOT generate flashcards about these instructions. ONLY generate flashcards based on the text provided by the user."""


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


def build_concept_user_message(concept):
    """
    Build the user-turn message for concept-based card generation.
    Contains ONLY the data — all rules live in CARD_GENERATION_SYSTEM.
    """
    data = {
        'cue': concept.get('cue', ''),
        'reference_note': concept.get('reference_note', concept.get('note', '')),
        'importance': concept.get('importance', ''),
    }
    return 'Here is the structured data to convert into flashcards:\n' + json.dumps(data, indent=2)


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
    Generate cloze cards for one concept using separated system/user prompts.

    System prompt — CARD_GENERATION_SYSTEM: all rules, constraints, output format.
    User message  — concept data only (cue, reference_note, importance).

    Keeping rules and data in separate parameters prevents the model from
    treating the instructions as source material to generate cards about.
    Retries once on JSON parse failure before giving up.
    """
    user_msg = build_concept_user_message(concept)
    debug_path = os.path.join(session_dir, f'debug_cards_concept_{concept_index}.txt')

    response = call_claude(client, user_msg, max_tokens=4000, system=CARD_GENERATION_SYSTEM)
    result = parse_json_response(response, debug_path)

    if result is None:
        print(f"    Parse failed — retrying concept {concept_index + 1}...")
        response = call_claude(client, user_msg, max_tokens=4000, system=CARD_GENERATION_SYSTEM)
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
# CHUNK-BASED GENERATION
# Primary pipeline. Takes a source .txt file directly, splits it into focused
# sections, and generates cards from each section independently.
# ─────────────────────────────────────────────────────────────────────────────

def chunk_source_material(filepath):
    """
    Break a source text file into focused, independently processable chunks.

    Splitting strategy (in order of preference):
      1. Section headers — lines of =/- characters, # Markdown headers,
         or ALL-CAPS lines indicate topic boundaries in structured documents.
      2. Word-count cap — any section longer than 500 words is further split
         into ~400-word sub-chunks to keep each API call tightly focused.
      3. Minimum filter — chunks under 20 words (blank lines, stray headers)
         are dropped.

    Returns a list of plain text strings, one per chunk.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    raw_chunks = []
    current = []

    for line in lines:
        # Detect section boundaries: ===, ---, ### lines or ALL CAPS headings
        is_boundary = (
            re.match(r'^[=\-]{3,}\s*$', line) or
            re.match(r'^#+\s', line) or
            (line.strip() and line.strip() == line.strip().upper() and len(line.strip()) > 3)
        )
        if is_boundary and current:
            raw_chunks.append('\n'.join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        raw_chunks.append('\n'.join(current).strip())

    # Split any over-length chunks into ~400-word sub-chunks
    MAX_WORDS = 500
    SUB_CHUNK_SIZE = 400
    final_chunks = []
    for chunk in raw_chunks:
        words = chunk.split()
        if len(words) <= MAX_WORDS:
            final_chunks.append(chunk)
        else:
            for j in range(0, len(words), SUB_CHUNK_SIZE):
                sub = ' '.join(words[j:j + SUB_CHUNK_SIZE])
                if sub.strip():
                    final_chunks.append(sub)

    # Drop chunks too short to produce meaningful cards
    return [c for c in final_chunks if len(c.split()) >= 20]


def make_chunk_slug(chunk, index):
    """
    Build a short Anki tag slug from the first meaningful words of a chunk.
    Same logic as make_concept_slug but applied to raw chunk text.
    """
    first_line = chunk.split('\n')[0]
    text = re.sub(r'[^\w\s]', '', first_line.lower())
    words = text.split()
    starters = {'what', 'how', 'why', 'when', 'where', 'which', 'does', 'is',
                'are', 'the', 'a', 'an', 'do', 'can', 'if', 'in', 'will'}
    meaningful = [w for w in words if w not in starters]
    slug = '-'.join(meaningful[:5])
    return slug[:50] if slug else f'chunk-{index + 1}'


def generate_cards_for_chunk(client, chunk, chunk_index, session_dir):
    """
    Generate cloze cards for one text chunk using separated system/user prompts.

    System prompt — CHUNK_GENERATION_SYSTEM: all rules, constraints, output format.
    User message  — the raw text chunk only.

    Keeping rules and source text in separate parameters prevents the model from
    generating cards about the cloze formatting instructions themselves.
    Retries once on JSON parse failure before giving up.
    """
    user_msg = f'Here is the text segment to convert into flashcards:\n\n{chunk}'
    debug_path = os.path.join(session_dir, f'debug_chunk_{chunk_index}.txt')

    response = call_claude(client, user_msg, max_tokens=4000, system=CHUNK_GENERATION_SYSTEM)
    result = parse_json_response(response, debug_path)

    if result is None:
        print(f'    Parse failed — retrying chunk {chunk_index + 1}...')
        response = call_claude(client, user_msg, max_tokens=4000, system=CHUNK_GENERATION_SYSTEM)
        result = parse_json_response(response, debug_path)

    if result is None:
        print(f'    Both attempts failed. Skipping chunk {chunk_index + 1}.')
        return []

    return extract_cards(result)


def make_session_dir_from_text(source_path):
    """
    Create a data/sessions/ folder for a source .txt file, named after the
    filename stem + today's date. Returns the path to the created folder.
    """
    from datetime import date
    stem = Path(source_path).stem.lower()
    stem = re.sub(r'[^\w\-]', '-', stem)[:40]
    today = date.today().strftime('%Y-%m-%d')
    session_name = f'{stem}-{today}'
    session_dir = os.path.join('data', 'sessions', session_name)

    # Add a numeric suffix if the folder already exists
    if os.path.exists(session_dir):
        suffix = 2
        while os.path.exists(f'{session_dir}-{suffix}'):
            suffix += 1
        session_dir = f'{session_dir}-{suffix}'

    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def generate_cards_from_file(client, filepath, session_dir, card_limit=None):
    """
    Primary generation pipeline. Reads a source .txt file, splits it into
    focused chunks, and runs generate → audit on each chunk independently.

    Per-chunk isolation means:
      - Each API call stays tightly focused on one section
      - A parse failure in one chunk does not affect the others
      - Payloads are always small (< 500 words in, < 8 cards out per chunk)

    Returns (all_cards, total_promoted).
    """
    chunks = chunk_source_material(filepath)

    if not chunks:
        print('\n  Error: No usable text chunks found in the source file.')
        sys.exit(1)

    limit_msg = f'  (card limit: {card_limit})' if card_limit else ''
    print(f'\nProcessing {len(chunks)} chunks from source file...{limit_msg}')
    print(f'  (Generate → Audit per chunk. Usually 20-40s per chunk.)')

    all_cards = []
    total_promoted = 0

    for i, chunk in enumerate(chunks):
        if card_limit and len(all_cards) >= card_limit:
            print(f'\n  Limit of {card_limit} cards reached — stopping early.')
            break

        preview = chunk.replace('\n', ' ')[:65]
        print(f'\n  [{i + 1}/{len(chunks)}] {preview}...')

        # Pass 1: Generate (Sonnet)
        cards = generate_cards_for_chunk(client, chunk, i, session_dir)
        print(f'          {len(cards)} card{"s" if len(cards) != 1 else ""} generated')

        # Pass 2: Audit extras (Haiku)
        cards, promoted = run_extra_audit(client, cards, session_dir, i)
        if promoted > 0:
            print(f'          +{promoted} promoted from Extra  →  {len(cards)} total')
        total_promoted += promoted

        # Tag cards with a slug derived from the chunk's opening text
        chunk_slug = make_chunk_slug(chunk, i)
        for card in cards:
            card['concept_slug'] = chunk_slug

        all_cards.extend(cards)

    if card_limit and len(all_cards) > card_limit:
        all_cards = all_cards[:card_limit]

    return all_cards, total_promoted


# ─────────────────────────────────────────────────────────────────────────────
# ANKI PACKAGE CONSTANTS
#
# These integers must never change after first use. Anki uses them to identify
# the model and deck across imports — changing them creates duplicates instead
# of updating existing cards.
# ─────────────────────────────────────────────────────────────────────────────
ANKI_MODEL_ID = 1607392319
ANKI_DECK_ID  = 2059400110


ANKI_CARD_CSS = """
.card {
    background-color: #2E3440;
    color: #ECEFF4;
    font-family: 'Fira Code', 'Roboto', Arial, sans-serif;
    font-size: 18px;
    text-align: center;
    padding: 20px;
}

/* Constrain width to prevent eye-tracking fatigue on wide monitors */
.card-content {
    max-width: 600px;
    margin: 0 auto;
    text-align: left;
}

/* Cloze deletion — high-contrast green, bold */
.cloze {
    font-weight: bold;
    color: #A3BE8C;
}

/* Extra / context field — muted, smaller, italic */
.extra-context {
    font-style: italic;
    font-size: 14px;
    color: #D8DEE9;
    margin-top: 8px;
}

hr {
    border: none;
    border-top: 1px solid #4C566A;
    margin-top: 20px;
    margin-bottom: 20px;
}
"""


def save_apkg(all_cards, output_path, topic):
    """
    Write all cards to an Anki .apkg package file using genanki.

    Uses a Cloze note type — required for {{c1::...}} deletions to render
    correctly in Anki. A standard Q&A model would display the raw syntax
    instead of hiding the cloze text.

    Model fields:
      Text  — the cloze sentence (rendered as a cloze card in Anki)
      Extra — shown below the answer after reveal, wrapped in .extra-context

    The model_id and deck_id are hardcoded. Do not change them — Anki uses
    these integers to match imported cards to existing notes and decks.
    """
    import genanki

    # Define the Cloze note model with custom CSS
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
                'qfmt': '<div class="card-content">{{cloze:Text}}</div>',
                'afmt': '<div class="card-content">{{cloze:Text}}<hr><div class="extra-context">{{Extra}}</div></div>',
            }
        ],
        css=ANKI_CARD_CSS,
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


def main(source_path, card_limit=None):
    """
    Entry point for the Anki export pipeline.

    Routes on file extension:
      .txt  → chunk-based pipeline (PRIMARY): reads source text directly,
              splits into sections, generates + audits per chunk.
      .json → concept-based pipeline (LEGACY): reads cornell.json produced
              by note_engine.py, generates + audits per critical_concept.

    card_limit — optional int. Stop after this many total cards (for test runs).
    """
    print()
    print('═' * 47)
    print('  ATLAS — Anki Cloze Export')
    print('═' * 47)

    client = get_client()
    source_path = str(source_path)

    # ── Route on file type ────────────────────────────
    if source_path.endswith('.txt'):
        # PRIMARY: chunk-based generation from raw source text
        topic = Path(source_path).stem.replace('-', ' ').replace('_', ' ').title()
        session_dir = make_session_dir_from_text(source_path)

        print(f'\n  Source: {source_path}')
        print(f'  Topic:  {topic}')
        print(f'  Output: {session_dir}')

        all_cards, total_promoted = generate_cards_from_file(
            client, source_path, session_dir, card_limit
        )

    else:
        # LEGACY: concept-based generation from cornell.json
        print('\nLoading notes...')
        notes = load_json(source_path)

        topic = notes.get('topic', 'Unknown Topic')
        concepts = notes.get('critical_concepts', [])
        session_dir = str(Path(source_path).parent)

        print(f'  Topic:    {topic}')
        print(f'  Concepts: {len(concepts)}')

        if not concepts:
            print('\n  Error: No critical_concepts found in the JSON.')
            print('  Make sure you are pointing at a valid cornell.json file.')
            sys.exit(1)

        all_cards = []
        total_promoted = 0
        limit_msg = f'  (card limit: {card_limit})' if card_limit else ''
        print(f'\nProcessing concepts...{limit_msg}')
        print(f'  (Generate → Audit per concept. Usually 20-40s per concept.)')

        for i, concept in enumerate(concepts):
            if card_limit and len(all_cards) >= card_limit:
                print(f'\n  Limit of {card_limit} cards reached — stopping early.')
                break

            concept_slug = make_concept_slug(concept.get('cue', ''), i)
            cue_preview = concept.get('cue', '')[:65]
            print(f'\n  [{i + 1}/{len(concepts)}] {cue_preview}...')

            cards = generate_cards_for_concept(client, concept, i, session_dir)
            print(f'          {len(cards)} card{"s" if len(cards) != 1 else ""} generated')

            cards, promoted = run_extra_audit(client, cards, session_dir, i)
            if promoted > 0:
                print(f'          +{promoted} promoted from Extra  →  {len(cards)} total')
            total_promoted += promoted

            for card in cards:
                card['concept_slug'] = concept_slug
            all_cards.extend(cards)

        if card_limit and len(all_cards) > card_limit:
            all_cards = all_cards[:card_limit]

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
    if len(sys.argv) < 2:
        print()
        print('  Usage (primary):  python3 src/anki_export.py source.txt [--limit N]')
        print('  Usage (legacy):   python3 src/anki_export.py cornell.json [--limit N]')
        print()
        print('  --limit N   Stop after N total cards (useful for test runs)')
        print()
        sys.exit(1)

    _json_path = sys.argv[1]
    _limit = None

    # Parse optional --limit N flag
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        try:
            _limit = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print('  Error: --limit requires an integer argument (e.g. --limit 10)')
            sys.exit(1)

    main(_json_path, card_limit=_limit)
