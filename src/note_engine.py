"""
note_engine.py — The main pipeline for Phase 1: Cornell Note generation.

This is the script you run. It orchestrates the full pipeline:
  1. Load your input text
  2. Pre-flight: ask Claude to identify the domain and calibrate the analysis
  3. Main analysis: run the 80/20 filter and extract structured notes
  4. Save results as cornell.json (and later cornell.html)

Usage:
  python3 src/note_engine.py path/to/input.txt
"""

import os
import sys
import json
import re
import shutil
from datetime import date
from pathlib import Path

# ─── Path setup ───────────────────────────────────────────────────────────────
# Add the src/ directory to Python's search path so we can import api_client.py.
# Path(__file__) is the absolute path to this file (note_engine.py).
# .parent gives us the src/ folder. We insert it at position 0 (highest priority).
sys.path.insert(0, str(Path(__file__).parent))

from api_client import get_client, call_claude

# PROJECT_ROOT is the learning-tool/ folder (two levels up from this file).
# All data is saved relative to this folder, no matter where you run the script from.
PROJECT_ROOT = Path(__file__).parent.parent
SESSIONS_DIR = PROJECT_ROOT / "data" / "sessions"


# ═════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES
# These are stored as module-level constants so they're easy to find and edit
# without touching any function logic. The prompts are the most important
# "code" in the whole system — garbage in, garbage out.
# ═════════════════════════════════════════════════════════════════════════════

# The pre-flight prompt is short and cheap.
# It asks Claude to identify the domain before we run the expensive main analysis.
# This prevents "Expert Blindness" — see research.md Section 6.
PREFLIGHT_PROMPT = """You are a domain classifier for an AI-powered study tool.

Analyze the text below and return ONLY valid JSON. No code fences, no explanation,
no text outside the JSON object — just the raw JSON.

Return this exact structure:
{
  "field": "the academic or professional field (e.g. 'Cellular Biology', 'Macroeconomics', '3D Printing')",
  "sub_domain": "the specific sub-topic within that field (e.g. 'Mitochondrial ATP Synthesis')",
  "shadow_exam": "one sentence: what real-world task would prove someone truly understands this content?",
  "heuristic_type": "exactly one of: System-Based, Skill-Based, Argument-Based, or Procedural",
  "optimal_persona": "complete this: 'An expert in [field] who specializes in [sub_domain], mentoring a student who needs to master the 20% of concepts required to [shadow_exam goal]'"
}

TEXT:
"""

# The JSON output schema for the main analysis.
# Stored as a plain string (not an f-string) so the curly braces don't
# need to be escaped. It gets concatenated into the full prompt in
# build_main_prompt().
MAIN_PROMPT_SCHEMA = """{
  "topic": "main subject of the text, 5 words or fewer",
  "field_context": {
    "field": "the detected field",
    "sub_domain": "the detected sub-domain",
    "shadow_exam": "the shadow exam sentence"
  },
  "summary": "2-3 sentence synthesis of the most important takeaways. A coherent paragraph, not a list.",
  "critical_concepts": [
    {
      "cue": "ONE question targeting ONE concept — one mechanism, one reason, or one distinction. Never join two ideas with 'and' or a comma. If a topic has two aspects, make two separate concept entries.",
      "comparison_cue": "ONE specific comparison or failure condition — e.g. 'How does X differ from Y?' or 'When does X break down?' Single-part only. No 'and', no multi-part questions.",
      "note": "The mechanism in telegraphic shorthand — NO full sentences. Use: → for causation/leads-to, ↑/↓ for increases/decreases, & for and, w/ for with, b/c for because. Max 4 lines.",
      "reference_note": "The core answer to the cue stripped to bare key phrases — the grading target. Comma-separated or line-separated keywords and mechanisms. No arrows or symbols. Max 2 lines.",
      "importance": "Generative Power — exactly 3 bullet points listing the specific facts or predictions this concept unlocks. No more than 3.",
      "relates_to": ["cue text of another concept this one connects to — or empty list []"],
      "diagram_needed": false,
      "diagram_description": "if diagram_needed is true: describe exactly what to draw, as if briefing an illustrator. Otherwise use empty string."
    }
  ],
  "supporting_details": [
    {
      "cue": "question whose answer is the detail below",
      "note": "the supporting detail, exception, or nuance",
      "parent_concept_index": 0,
      "detail_type": "supporting_detail OR important_exception OR clinical_application OR intersystem_link"
    }
  ],
  "key_terms": [
    {
      "term": "the vocabulary word or proper noun",
      "definition": "brief definition anchored to the mechanism — not a dictionary definition",
      "why_memorize": "why this cannot be derived from understanding the mechanism alone"
    }
  ],
  "gap_analysis": {
    "content_filtered_out": "plain English: what was omitted from the 80/20 cut and why",
    "intersystem_links_found": "any cross-system or cross-domain causal connections identified",
    "important_nuances_omitted": "exceptions or edge cases that carry clinical or practical risk",
    "omission_risk": "low, medium, or high — followed by one sentence of justification"
  }
}"""


# ═════════════════════════════════════════════════════════════════════════════
# PIPELINE FUNCTIONS
# Each function does exactly one job. If something breaks, you can test
# each function in isolation to find which step failed.
# ═════════════════════════════════════════════════════════════════════════════

def load_text(file_path):
    """
    Opens the input text file and returns its contents as a string.

    Also counts the words and prints a warning if the text is very short —
    the 80/20 filter needs enough material to work with.

    Arguments:
      file_path — a string or Path pointing to the input .txt file

    Returns: the file contents as a Python string.
    """
    path = Path(file_path)

    # Check the file exists before trying to open it
    if not path.exists():
        print()
        print(f"  ERROR: Could not find the file: {file_path}")
        print()
        print("  Make sure the path is correct. Example:")
        print("    python3 src/note_engine.py data/sessions/my-topic/input.txt")
        print()
        sys.exit(1)

    text = path.read_text(encoding="utf-8").strip()

    if not text:
        print()
        print(f"  ERROR: The file at {file_path} is empty.")
        print("  Paste your study text into it and try again.")
        print()
        sys.exit(1)

    word_count = len(text.split())

    # Warn if the text is very short — but continue anyway.
    # The 80/20 filter works best with 200+ words. Below 100, notes will be thin.
    if word_count < 100:
        print()
        print(f"  ⚠  Short text detected ({word_count} words).")
        print("     The 80/20 filter works best with 200+ words.")
        print("     Continuing — notes may be limited.")
        print()

    return text


def build_preflight_prompt(raw_text):
    """
    Assembles the short pre-flight prompt by appending the raw text
    to the PREFLIGHT_PROMPT template.

    This is a simple string join — the template is a constant defined
    at the top of this file, making it easy to adjust without touching
    any logic.

    Returns: the complete pre-flight prompt as a string.
    """
    return PREFLIGHT_PROMPT + raw_text


def detect_field(client, raw_text):
    """
    Runs the pre-flight prompt and returns domain context as a dictionary.

    This is Step 1 of the two-step AI call. It identifies:
      - What field the text belongs to (e.g. 'Cellular Biology')
      - The specific sub-domain (e.g. 'Mitochondrial ATP Production')
      - The shadow exam (the real-world test of understanding)
      - The 80/20 heuristic type (System-Based, Skill-Based, etc.)
      - The calibrated expert persona for the main analysis

    Why do this separately? Without it, the main analysis uses a generic
    lens and often picks complex concepts over foundational ones.
    See research.md Section 6: "The Expert Blindness Problem."

    Returns: a Python dict with keys: field, sub_domain, shadow_exam,
             heuristic_type, optimal_persona.
    """
    prompt = build_preflight_prompt(raw_text)

    # Use fewer tokens here — the pre-flight response is small
    response = call_claude(client, prompt, max_tokens=500)

    try:
        # parse_response handles stripping markdown fences if present
        field_context = parse_response(response)
        return field_context

    except (ValueError, KeyError) as e:
        # If pre-flight fails, use safe fallback defaults so the main
        # analysis can still run — just without calibration
        print(f"  ⚠  Pre-flight detection failed ({e}). Using generic defaults.")
        return {
            "field": "General",
            "sub_domain": "General Study Content",
            "shadow_exam": "Apply the core concepts to a novel, real-world problem",
            "heuristic_type": "System-Based",
            "optimal_persona": "An expert educator mentoring a student who needs to master the 20% of concepts required to apply this knowledge to a real-world problem"
        }


def build_main_prompt(raw_text, field_context):
    """
    Assembles the full 80/20 analysis prompt by combining:
      1. The persona and rules (f-string — needs variable injection)
      2. The output schema (plain string — braces must not be escaped)
      3. The input text (f-string — needs variable injection)

    The schema is stored as the MAIN_PROMPT_SCHEMA constant to keep
    this function readable.

    Returns: the complete analysis prompt as a string.
    """
    persona      = field_context.get("optimal_persona", "an expert educator")
    shadow_exam  = field_context.get("shadow_exam", "apply this knowledge to a real problem")
    heuristic_type = field_context.get("heuristic_type", "System-Based")

    # Compute word count and target card count: ~1 card per 300 words, min 3, max 15
    word_count   = len(raw_text.split())
    target_count = max(3, min(15, round(word_count / 300)))

    # Map each heuristic type to a plain-English description for the prompt
    heuristic_descriptions = {
        "System-Based":  "Feedback loops and regulators — the single variable that, when changed, shifts the whole system.",
        "Skill-Based":   "Fail-safe principles — things that, if ignored, cause the entire project to fail.",
        "Argument-Based":"Load-bearing premises — the one idea that, if removed, collapses the entire argument.",
        "Procedural":    "Meta-principles — not 'how to do X' but 'how to know when X is needed and when it is not'."
    }
    heuristic_desc = heuristic_descriptions.get(
        heuristic_type,
        "Foundational concepts with maximum explanatory power."
    )

    # Part 1: persona, task, and rules — uses f-string for variable injection
    header = f"""[PERSONA]
You are {persona}.

[TASK]
Analyze the text below and extract structured Cornell notes, applying strict 80/20 filtering.

[CRITICAL RULES]
- Return ONLY valid JSON. No code fences, no explanation, no text outside the JSON object.
- The JSON must exactly match the schema below.
- 80/20 IS A RATIO, NOT A NUMBER. You have a mental budget. Only include a concept if its
  Generative Power — its ability to let the student predict 5 or more other facts — justifies
  its inclusion. A short text may produce 2 concepts. A dense chapter may produce 15. Scale naturally.
- Generative Power test: can a student who knows this deeply predict 5+ related facts
  without being told them? If not, this concept does not belong in the critical 20%.
- Domain heuristic for this content ({heuristic_type}): {heuristic_desc}
- The shadow exam for this content is: "{shadow_exam}"
  Filter for the concepts a student needs to perform well on that exact application.
- Every critical concept must include a comparison_cue — a question of the form
  "How does X differ from Y?" or "Under what conditions would X fail?"
- Explicitly look for Intersystem Links: places where a concept in one system or domain
  causally affects another. These are rarely stated but always high-yield.
- Flag clinically or practically dangerous exceptions.
- The "importance" field must be specific: list the actual facts this concept predicts.
- CARD COUNT: This text is {word_count} words. Generate approximately {target_count} critical
  concept cards (1 per ~300 words, min 3, max 15). Do not pad with weak concepts to hit the
  target. One concept per card — if a topic has multiple distinct ideas, split into separate cards.

[CONTENT STRUCTURE RULES — apply to every concept without exception]
1. CUE FIELD: One question, one idea. If a concept has two aspects, create two separate
   concept entries. Never use "and" or a comma to join two ideas in a single cue.
2. NOTE FIELD: Telegraphic shorthand only — NO full sentences. Use → for causation,
   ↑/↓ for increase/decrease, & = and, w/ = with, b/c = because. Max 4 lines.
3. REFERENCE_NOTE FIELD: The grading target. Same content as note but plain phrases
   only — no arrows or symbols. Comma-separated or line-separated. Max 2 lines.
4. COMPARISON CUE FIELD: One specific comparison or one failure condition. Single-part
   only. "How does X differ from Y?" is correct. "How do X, Y, and Z relate?" is not.
5. IMPORTANCE FIELD: Exactly 3 bullet points. No more. Each bullet is one specific
   fact or prediction the concept unlocks — not a restatement of the concept itself.

[OUTPUT SCHEMA]
"""

    # Part 2: the JSON schema — plain string, no f-string, braces are literal
    schema = MAIN_PROMPT_SCHEMA

    # Part 3: the text to analyze — uses f-string for variable injection
    footer = f"""

TEXT TO ANALYZE:
{raw_text}"""

    return header + schema + footer


def parse_response(response_string):
    """
    Extracts and parses the JSON from Claude's response text.

    Claude sometimes wraps JSON in markdown code fences (```json ... ```)
    even when told not to. This function strips those if present,
    then finds the outermost JSON object and parses it.

    If parsing fails, the raw response is saved to data/debug_response.txt
    so nothing is lost — even broken responses may be recoverable.

    Returns: a Python dictionary.
    Raises: ValueError with a plain-English message if parsing fails.
    """
    text = response_string.strip()

    # Strip markdown code fences (```json...``` or ```...```)
    if text.startswith("```"):
        # Remove the opening fence line (e.g. "```json\n")
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3].strip()

    # Find the outermost { ... } — the JSON object we want
    start = text.find("{")
    end   = text.rfind("}") + 1

    if start == -1 or end == 0:
        _save_debug(response_string)
        raise ValueError(
            "No JSON object found in Claude's response.\n"
            "Raw response saved to data/debug_response.txt"
        )

    json_text = text[start:end]

    try:
        return json.loads(json_text)

    except json.JSONDecodeError as e:
        _save_debug(response_string)
        raise ValueError(
            f"JSON was found but could not be parsed: {e}\n"
            "Raw response saved to data/debug_response.txt\n"
            "Try running again — this is usually a one-time glitch."
        )


def _save_debug(raw_response):
    """
    Saves a raw Claude response to a debug file when parsing fails.

    This is a private helper (the underscore prefix is a Python convention
    meaning 'internal use only'). We call it when something goes wrong
    so the response isn't lost.
    """
    debug_path = PROJECT_ROOT / "data" / "debug_response.txt"
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    debug_path.write_text(raw_response, encoding="utf-8")


def validate_notes(notes_dict):
    """
    Checks that the parsed notes dictionary contains all required fields.

    Claude is reliable but not perfect. This function catches cases where
    a required section is missing so we can give the user a clear message
    instead of a confusing Python error later.

    Returns: True if everything looks good.
    Raises: ValueError with a plain-English explanation if something is missing.
    """
    required_fields = ["topic", "summary", "critical_concepts", "key_terms", "gap_analysis"]

    for field in required_fields:
        if field not in notes_dict:
            raise ValueError(
                f"The AI response is missing the '{field}' section.\n"
                "This sometimes happens with very short texts.\n"
                "Try adding more content to your input.txt and running again."
            )

    # critical_concepts must not be empty — that means the filter found nothing
    if not notes_dict["critical_concepts"]:
        raise ValueError(
            "No critical concepts were identified.\n"
            "Your input text may be too short or too unstructured.\n"
            "Try pasting a paragraph or more of substantive content."
        )

    return True


def create_session_folder(topic):
    """
    Creates a session folder named [topic]-[today's date] inside data/sessions/.

    The topic comes from Claude's analysis (e.g. "Mitochondrial ATP Production").
    We sanitize it to be a valid folder name, append today's date, and create it.

    If a folder with that name already exists (you ran the same topic today),
    we append -2, -3, etc. rather than overwriting previous work.

    Returns: a Path object pointing to the new session folder.
    """
    # Sanitize the topic string for use as a folder name:
    # lowercase → remove special chars → replace spaces with hyphens → truncate
    clean = topic.lower()
    clean = re.sub(r"[^a-z0-9\s\-]", "", clean)   # Keep only letters, numbers, spaces, hyphens
    clean = re.sub(r"\s+", "-", clean.strip())       # Spaces → hyphens
    clean = clean[:40]                                # Max 40 characters
    clean = clean.strip("-")                          # No leading/trailing hyphens

    folder_name = f"{clean}-{date.today().isoformat()}"
    session_dir = SESSIONS_DIR / folder_name

    # If it already exists (ran the same topic today), add a counter
    if session_dir.exists():
        counter = 2
        while session_dir.exists():
            session_dir = SESSIONS_DIR / f"{folder_name}-{counter}"
            counter += 1

    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def save_session_json(notes_dict, session_dir):
    """
    Writes the notes dictionary to cornell.json in the session folder.

    Uses indent=2 so the file is human-readable — open it in any text editor
    to inspect exactly what Claude extracted before the HTML is built.

    Returns: the Path to the saved file.
    """
    json_path = Path(session_dir) / "cornell.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(notes_dict, f, indent=2, ensure_ascii=False)

    return json_path


# ═════════════════════════════════════════════════════════════════════════════
# MAIN — the entry point that orchestrates the whole pipeline
# ═════════════════════════════════════════════════════════════════════════════

def main(input_path):
    """
    Runs the full note generation pipeline from start to finish.

    This function calls every other function in sequence and prints
    a status update at each step so you can see exactly what's happening.

    It's called at the bottom of this file when you run:
      python3 src/note_engine.py path/to/input.txt
    """
    print()
    print("═" * 55)
    print("  ATLAS — Note Engine")
    print("═" * 55)
    print()

    # ── Step 1: Load the input text ───────────────────────────────────────
    raw_text = load_text(input_path)
    word_count = len(raw_text.split())
    print(f"  Input: {input_path} ({word_count} words)")
    print()

    # ── Step 2: Pre-flight — detect the field and calibrate the analysis ──
    print("Step 1/4  Detecting field...")
    client = get_client()
    field_context = detect_field(client, raw_text)

    shadow_preview = field_context["shadow_exam"]
    if len(shadow_preview) > 65:
        shadow_preview = shadow_preview[:65] + "..."

    print(f"          Field:       {field_context['field']}")
    print(f"          Sub-domain:  {field_context['sub_domain']}")
    print(f"          Heuristic:   {field_context['heuristic_type']}")
    print(f"          Shadow exam: {shadow_preview}")
    print()

    # ── Step 3: Run the full 80/20 analysis ───────────────────────────────
    print("Step 2/4  Analyzing with 80/20 filter...")
    print("          (this usually takes 15–30 seconds)")

    prompt   = build_main_prompt(raw_text, field_context)
    response = call_claude(client, prompt, max_tokens=8000)

    try:
        notes_dict = parse_response(response)
        validate_notes(notes_dict)
    except ValueError as e:
        print()
        print(f"  ERROR: {e}")
        sys.exit(1)

    concept_count = len(notes_dict.get("critical_concepts", []))
    detail_count  = len(notes_dict.get("supporting_details", []))
    term_count    = len(notes_dict.get("key_terms", []))
    risk          = notes_dict.get("gap_analysis", {}).get("omission_risk", "unknown")

    print()
    print(f"          Critical concepts:  {concept_count}")
    print(f"          Supporting details: {detail_count}")
    print(f"          Key terms:          {term_count}")
    print(f"          Omission risk:      {risk}")
    print()

    # ── Step 4: Save the session ───────────────────────────────────────────
    print("Step 3/4  Creating session folder...")
    session_dir = create_session_folder(notes_dict["topic"])
    print(f"          {session_dir.relative_to(PROJECT_ROOT)}/")

    # Copy the input file into the session folder so everything is in one place
    shutil.copy(input_path, session_dir / "input.txt")

    json_path = save_session_json(notes_dict, session_dir)
    print(f"          ✓ input.txt")
    print(f"          ✓ cornell.json")
    print()

    # ── Step 5: Build the HTML file ───────────────────────────────────────
    print("Step 4/4  Building HTML...")
    from html_builder import build_html
    # Pass the API key so the HTML can make grading calls directly from the browser.
    # The key is already loaded via load_dotenv() inside get_client() above.
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    html_content = build_html(notes_dict, api_key=api_key)
    html_path = Path(session_dir) / "cornell.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"          ✓ cornell.html")
    print()

    # ── Done ──────────────────────────────────────────────────────────────
    print("═" * 55)
    print("  Done. Open your notes:")
    print(f'  open "{html_path}"')
    print("═" * 55)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
#
# sys.argv is the list of things typed after "python3" in the terminal.
# sys.argv[0] is always the script name itself.
# sys.argv[1] is the first argument — in our case, the path to input.txt.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print()
        print("  Usage: python3 src/note_engine.py path/to/input.txt")
        print()
        print("  Example:")
        print("    python3 src/note_engine.py data/sessions/my-topic/input.txt")
        print()
        sys.exit(1)

    main(sys.argv[1])
