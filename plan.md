# ATLAS — Phase 1 Build Plan: The Note Engine

*This plan translates research.md into a concrete build sequence.*
*Every decision here traces back to research.md. Check there for the "why."*

---

## What We Are Building

A command-line tool that accepts a text file as input and outputs two files:
1. `cornell.json` — the structured notes data (machine-readable, human-inspectable)
2. `cornell.html` — a fully interactive Cornell notes page that opens in any browser

The user pastes text into `input.txt`, runs one command, and gets a browser-ready
study session in seconds.

---

## Part 1: Every File We Will Create

### Files You Write Once (permanent project files)

---

**`requirements.txt`**
Location: `~/Desktop/learning-tool/requirements.txt`

A plain text file listing the two Python packages we need to install. Python reads this
file and installs both packages with one command. We keep it here so anyone who picks
up this project later knows exactly what to install.

The two packages:
- `anthropic` — the official Python library for talking to Claude's API
- `python-dotenv` — a tiny library that reads your secret API key from a separate file
  so you never have to type it into your code

---

**`.env`**
Location: `~/Desktop/learning-tool/.env`

A file that stores your Claude API key. It looks like this:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```
This file is **never** shared, emailed, or committed to git. It lives only on your
computer. The `.gitignore` file (next) ensures git ignores it completely.

Why a separate file? If your API key is typed directly into Python code, and you ever
share that code or push it to GitHub, your key is exposed and anyone could use it on
your bill. The `.env` pattern keeps secrets separate from code.

---

**`.gitignore`**
Location: `~/Desktop/learning-tool/.gitignore`

A file that tells git which files to never track. We add `.env` here so the API key
is never accidentally committed. We also add `__pycache__/` (Python's internal temp
files) and `.DS_Store` (Mac folder metadata files).

---

**`src/api_client.py`**
Location: `~/Desktop/learning-tool/src/api_client.py`

One job: communicate with Claude's API. Every other part of the system that needs to
talk to Claude calls this file. Keeping all API communication in one place means if
anything changes about how we call Claude (different model, different settings), we
change it in one file, not everywhere.

Contains two functions. (See Part 2 for full function descriptions.)

---

**`src/note_engine.py`**
Location: `~/Desktop/learning-tool/src/note_engine.py`

The brain of Phase 1. This is the main script you run from the terminal. It
orchestrates the entire pipeline: reads your text file, calls Claude twice (pre-flight
then full analysis), validates the result, saves the JSON, calls the HTML builder,
and saves the HTML. It is the script you point at an `input.txt` file to get your
notes.

Contains eight functions plus the `main()` entry point. (See Part 2.)

---

**`src/html_builder.py`**
Location: `~/Desktop/learning-tool/src/html_builder.py`

One job: take the notes dictionary that `note_engine.py` produces and turn it into a
complete, self-contained HTML file. This file never talks to Claude and never reads from
disk — it only receives a Python dictionary and returns a string of HTML. Keeping it
separate from `note_engine.py` means we can improve or redesign the HTML output
without ever touching the analysis logic.

Contains nine functions. (See Part 2.)

---

### Files Created Automatically at Runtime (one per study session)

These are not written by us — they are created by the pipeline each time you run it.

---

**`data/sessions/[topic]-[date]/input.txt`**

The raw text you paste in before running the pipeline. You create this manually.
Example path: `data/sessions/RAAS-2025-08-14/input.txt`

---

**`data/sessions/[topic]-[date]/cornell.json`**

The structured notes data produced by Claude's analysis. This is the intermediary
format — all the information in a clean, organized structure — before it gets turned
into HTML. You can open this file in any text editor to see exactly what Claude
extracted. If the HTML ever looks wrong, you inspect this file first to see whether
the problem is in the AI analysis or in the HTML builder.

---

**`data/sessions/[topic]-[date]/cornell.html`**

The finished product. A single self-contained file with all CSS and JavaScript embedded.
Open it in any browser. Works offline. Contains: concept map, spaced repetition review
dates, Cornell two-column layout with Force Draft mode, terminology section, gap
analysis, and a personal reflections area.

---

**Summary of all files:**

```
learning-tool/
├── .env                          ← your API key (never shared)
├── .gitignore                    ← tells git to ignore .env
├── requirements.txt              ← packages to install
├── src/
│   ├── api_client.py             ← all Claude API communication
│   ├── note_engine.py            ← main pipeline script (you run this)
│   └── html_builder.py           ← builds the HTML output
└── data/
    └── sessions/
        └── RAAS-2025-08-14/      ← one folder per study session
            ├── input.txt         ← the text you pasted in
            ├── cornell.json      ← structured notes data
            └── cornell.html      ← your finished notes (open this)
```

---

## Part 2: Every Function We Will Write

### In `src/api_client.py`

---

**`get_client()`**
- **Takes in:** nothing
- **Gives back:** a configured Anthropic client object
- **Plain English:** reads your API key from the `.env` file, creates a connection
  object to Claude's API, and returns it ready to use. Called once at the start of
  the pipeline.

---

**`call_claude(client, prompt, max_tokens=4000)`**
- **Takes in:** the client object, a prompt string, an optional token limit
- **Gives back:** Claude's response as a plain string
- **Plain English:** sends your prompt to Claude, waits for the response, and returns
  just the text. Handles the API call mechanics so nothing else has to think about
  them. If the API returns an error, catches it and explains it in plain English.

---

### In `src/note_engine.py`

---

**`load_text(file_path)`**
- **Takes in:** a file path string (e.g., `"data/sessions/RAAS-2025-08-14/input.txt"`)
- **Gives back:** the contents of the file as a string
- **Plain English:** opens the text file and reads everything in it. If the file
  doesn't exist, prints a clear message explaining what went wrong and where to look,
  rather than showing a Python error message.

---

**`build_preflight_prompt(raw_text)`**
- **Takes in:** the raw text string
- **Gives back:** a short prompt string ready to send to Claude
- **Plain English:** wraps the input text in the pre-flight instructions that ask
  Claude to identify the field, sub-domain, shadow exam, and 80/20 heuristic type.
  This is a short, cheap call — it only produces a small JSON object used to calibrate
  the main analysis. See research.md Section 6 for why we do this first.

---

**`detect_field(client, raw_text)`**
- **Takes in:** the API client, the raw text string
- **Gives back:** a Python dictionary with keys: `field`, `sub_domain`, `shadow_exam`,
  `heuristic_type`, `optimal_persona`
- **Plain English:** runs the pre-flight prompt through Claude and parses the result.
  This is Step 1 of the two-step AI call. The result tells the main analysis exactly
  what domain it is operating in, what level of expertise to assume, and what
  real-world application to filter for. Prevents the Expert Blindness problem described
  in research.md Section 7.

---

**`build_main_prompt(raw_text, field_context)`**
- **Takes in:** the raw text string, the field_context dictionary from `detect_field()`
- **Gives back:** the full analysis prompt string, ready to send to Claude
- **Plain English:** assembles the complete analysis instructions by injecting the
  domain, persona, shadow exam, and heuristic type from the pre-flight result into
  the prompt template. Also includes the full JSON output schema. This is the most
  important function in the codebase — the quality of the notes depends on it.
  The prompt template lives as a constant at the top of the file, not buried here.

---

**`parse_response(response_string)`**
- **Takes in:** the raw string Claude returned
- **Gives back:** a Python dictionary (the parsed JSON), or raises a clear error
- **Plain English:** Claude sometimes wraps its JSON response in code fences
  (```json ... ```) even when told not to. This function strips those if present,
  then converts the JSON text into a Python dictionary using Python's built-in
  `json.loads()`. If the JSON is malformed, saves the raw response to a debug file
  and explains exactly what went wrong.

---

**`validate_notes(notes_dict)`**
- **Takes in:** the parsed Python dictionary
- **Gives back:** True if valid, raises a descriptive error if not
- **Plain English:** checks that all required fields exist in the dictionary
  (`topic`, `summary`, `critical_concepts`, `key_terms`, `gap_analysis`). Checks
  that `critical_concepts` is not empty. Tells the user in plain English if anything
  is missing and what to try.

---

**`create_session_folder(topic, base_dir="data/sessions")`**
- **Takes in:** a topic string (from Claude's analysis), the base directory path
- **Gives back:** the path to the newly created session folder as a string
- **Plain English:** creates a folder named `[topic]-[today's date]` inside
  `data/sessions/`. If that folder already exists, adds `-2`, `-3`, etc. to avoid
  overwriting previous sessions. Returns the full path so other functions know where
  to save files.

---

**`save_session_json(notes_dict, session_dir)`**
- **Takes in:** the notes dictionary, the session folder path
- **Gives back:** the path to the saved file
- **Plain English:** writes the notes dictionary to `cornell.json` in the session
  folder, formatted with clean indentation so it is human-readable. Nothing else.

---

**`main(input_path)`**
- **Takes in:** the path to an `input.txt` file (passed from the terminal command)
- **Gives back:** nothing — its job is to run the pipeline and print progress
- **Plain English:** the entry point. When you run `python src/note_engine.py
  data/sessions/RAAS-2025-08-14/input.txt`, Python calls this function. It calls
  every other function in sequence, prints a status message at each step so you can
  see what is happening, and finishes by printing the path to the HTML file you
  should open.

---

### In `src/html_builder.py`

---

**`build_css()`**
- **Takes in:** nothing
- **Gives back:** a string containing all the CSS for the notes page
- **Plain English:** returns the complete stylesheet as a string. Includes the
  two-column Cornell layout, color coding for concept types, styles for diagram
  placeholders, Force Draft text area, the blurred summary, Watch Out amber styling,
  and a print stylesheet so the notes look good on paper too.

---

**`build_javascript()`**
- **Takes in:** nothing
- **Gives back:** a string containing all the JavaScript for the notes page
- **Plain English:** returns the complete interaction code as a string. Handles:
  hide/reveal toggle for main notes, the Force Draft gate (textarea must have content
  before revealing), the progress counter, and the summary unlock (only available
  after all notes are revealed).

---

**`build_concept_map_svg(critical_concepts)`**
- **Takes in:** the `critical_concepts` list from the notes dictionary
- **Gives back:** an SVG string — a small visual diagram
- **Plain English:** creates a simple box-and-line diagram showing each concept as a
  labeled box, with lines connecting boxes that are linked via `relates_to`. This is
  embedded at the top of the HTML page so the learner can see the knowledge structure
  before diving into details. Intentionally simple — boxes and lines, no complex
  layout algorithm.

---

**`build_spaced_repetition_block(creation_date)`**
- **Takes in:** today's date as a string
- **Gives back:** an HTML string showing review schedule
- **Plain English:** calculates the four review dates (+1 day, +3 days, +7 days,
  +14 days) from the creation date and returns a styled banner at the top of the page
  showing when to reopen the file. This is not a scheduling system — it is a visible
  nudge. See research.md Section 4.

---

**`build_concept_row(concept, index)`**
- **Takes in:** one concept dictionary from `critical_concepts`, and its position
  number
- **Gives back:** an HTML string for one complete cue/note row
- **Plain English:** builds one row of the Cornell layout — the cue question on the
  left, the Force Draft textarea + reveal button + main note on the right. If the
  concept has `diagram_needed: true`, the diagram placeholder is embedded inside the
  note, immediately above the explanatory text (not in a separate section — cognitive
  load rule from research.md Section 7).

---

**`build_supporting_details(details, parent_index)`**
- **Takes in:** the full `supporting_details` list, the index of the parent concept
- **Gives back:** an HTML string for all supporting details belonging to that parent
- **Plain English:** filters the supporting details list for entries matching
  `parent_concept_index`, then builds a collapsible `<details>` block for each one.
  `important_exception` and `intersystem_link` types get amber "Watch Out" styling.
  These blocks appear collapsed inside their parent concept row.

---

**`build_terminology_section(key_terms)`**
- **Takes in:** the `key_terms` list from the notes dictionary
- **Gives back:** an HTML string for the full terminology section
- **Plain English:** builds a clean vocabulary section at the bottom of the notes,
  separate from the Cornell layout. Each term gets its mechanism-anchored definition
  and a note on why it must be memorized explicitly (it cannot be derived from
  understanding alone). See research.md Section 1 — Mechanism-Terminology Split.

---

**`build_gap_section(gap_analysis)`**
- **Takes in:** the `gap_analysis` dictionary from the notes
- **Gives back:** an HTML string for the gap analysis section
- **Plain English:** builds a transparent summary of what was filtered out and why.
  Shows: what content was omitted, any intersystem links found, important nuances that
  carry risk, and the overall omission risk rating. Styled distinctly from the main
  notes so the learner knows this is meta-information about the filtering, not the
  notes themselves.

---

**`build_html(notes_dict)`**
- **Takes in:** the complete notes dictionary
- **Gives back:** one long string — the entire, complete HTML file
- **Plain English:** calls every other function in this file and assembles their
  outputs into a single, valid HTML document. The structure is: DOCTYPE → head (with
  CSS) → body (concept map → spaced repetition → Cornell layout → terminology →
  gap analysis → reflections div → JavaScript). Returns the whole thing as one string.

---

**Summary of all functions:**

```
api_client.py
  get_client()                    reads .env, returns Claude connection
  call_claude()                   sends prompt, returns response text

note_engine.py
  load_text()                     reads input.txt, returns string
  build_preflight_prompt()        wraps text in pre-flight instructions
  detect_field()                  runs pre-flight, returns domain context
  build_main_prompt()             assembles full analysis prompt
  parse_response()                extracts JSON from Claude's response
  validate_notes()                checks all required fields exist
  create_session_folder()         creates data/sessions/[topic]-[date]/
  save_session_json()             writes cornell.json
  main()                          runs the whole pipeline

html_builder.py
  build_css()                     returns complete CSS string
  build_javascript()              returns complete JS string
  build_concept_map_svg()         returns SVG concept diagram
  build_spaced_repetition_block() returns review date banner HTML
  build_concept_row()             returns HTML for one cue/note pair
  build_supporting_details()      returns HTML for collapsed detail blocks
  build_terminology_section()     returns HTML for key terms section
  build_gap_section()             returns HTML for gap analysis section
  build_html()                    assembles everything into complete HTML
```

---

## Part 3: The Build Order

The order matters because each piece depends on the one before it.

---

### Stage 0: Environment Setup
**What:** `requirements.txt`, `.env`, `.gitignore`

**Why first:** Nothing else can run until the API connection works. Setting up the
environment and credentials first means every subsequent stage can be immediately
tested.

**Steps:**
1. Create `requirements.txt` with two lines: `anthropic` and `python-dotenv`
2. Run `pip install -r requirements.txt` to install both packages
3. Create `.env` and add your API key
4. Create `.gitignore` and add `.env` to it
5. Verify setup by confirming Python can import both packages

---

### Stage 1: API Client
**What:** `src/api_client.py` — both functions

**Why second:** `note_engine.py` depends on `api_client.py`. You cannot test any
analysis logic until you can successfully call Claude. Build the smallest possible
thing that proves Claude works.

**Steps:**
1. Write `get_client()`
2. Write `call_claude()`
3. Write a temporary 10-line test at the bottom of the file that sends "Say hello"
   to Claude and prints the response

---

### ✅ CHECKPOINT 1: API Connection Confirmed
**What you do:** Run `python src/api_client.py` from the terminal
**What you see:** Claude's response to "Say hello" printed in your terminal
**What it proves:** Your API key works, the package is installed correctly, and you
can receive responses from Claude
**Before continuing:** The response must appear. If it doesn't, we debug here before
writing anything else.

---

### Stage 2: Core Pipeline (Without HTML)
**What:** All functions in `src/note_engine.py`

**Why third:** The pipeline logic is the core of the feature. Building it before the
HTML builder means we can verify the AI analysis is working correctly before worrying
about presentation. We can see the JSON output and confirm it looks right.

**Steps (in this exact order within the file):**
1. Write `load_text()` — test it by loading a short text file
2. Write `build_preflight_prompt()` — just string assembly, easy to verify
3. Write `detect_field()` — test it by printing the pre-flight result for sample text
4. Write `build_main_prompt()` — test it by printing the assembled prompt (do not send
   to Claude yet — just verify it looks correct)
5. Write `parse_response()` — test it with a sample JSON string
6. Write `validate_notes()` — test it with a sample dictionary
7. Write `create_session_folder()` — test it by creating a test folder
8. Write `save_session_json()` — test it by saving a small dictionary
9. Write `main()` — wire everything together, but make `build_html()` a placeholder
   that just returns the string `"HTML goes here"` for now

---

### ✅ CHECKPOINT 2: JSON Output Confirmed
**What you do:**
1. Create `data/sessions/test-session/input.txt` and paste a paragraph of text
2. Run `python src/note_engine.py data/sessions/test-session/input.txt`

**What you see:**
```
Detecting field...
  Field: [detected field]
  Shadow exam: [detected application]
  Heuristic: [System-Based / Skill-Based / etc.]

Analyzing text (this takes 10-20 seconds)...
  Found 7 critical concepts
  Found 4 supporting details
  Found 3 key terms
  Omission risk: low

Creating session folder: data/sessions/[topic]-[date]/
Saved: cornell.json

HTML builder not yet built — skipping.
```

**What you see in `cornell.json`:**
Open the file in a text editor. You should see a clean, indented JSON structure with
`topic`, `summary`, `critical_concepts`, `supporting_details`, `key_terms`, and
`gap_analysis` fields populated with real content about your text.

**Before continuing:** The JSON must contain meaningful content — real questions in the
`cue` fields, real explanations in the `note` fields, and a sensible `summary`. If
it looks like generic filler, the prompt needs adjustment before we build the HTML.

---

### Stage 3: HTML Builder
**What:** All functions in `src/html_builder.py`, then wiring it into `note_engine.py`

**Why fourth:** The HTML builder takes a verified, correct data structure and turns it
into a visual output. Building this last means we are always working with real data,
not made-up test data.

**Steps (in this exact order within the file):**
1. Write `build_css()` — the layout and styling
2. Write `build_javascript()` — the interactive behaviors
3. Write a temporary `build_html()` stub that produces a minimal valid HTML page
   with just the CSS and JS (no content yet) — open it in a browser to confirm the
   stylesheet loads correctly
4. Write `build_spaced_repetition_block()` — add it to the stub, verify in browser
5. Write `build_concept_map_svg()` — add it to the stub with sample data, verify in
   browser
6. Write `build_concept_row()` — add it to the stub with one sample concept, verify
   hide/reveal and Force Draft gate work in browser
7. Write `build_supporting_details()` — add to a row, verify collapse/expand works
8. Write `build_terminology_section()` — add to stub, verify styling
9. Write `build_gap_section()` — add to stub, verify styling
10. Write the real `build_html()` that assembles all pieces together
11. Replace the placeholder `build_html()` call in `note_engine.py` with the real one
12. Run the full pipeline end-to-end

---

### ✅ CHECKPOINT 3: Full End-to-End Working
**What you do:**
1. Drop a real piece of text into `input.txt` (a textbook paragraph, an article section,
   anything substantive)
2. Run `python src/note_engine.py data/sessions/[folder]/input.txt`
3. Open the resulting `cornell.html` in your browser

**What you see in the terminal:**
```
Detecting field...
  Field: [field]
  Shadow exam: [application]

Analyzing text...
  Found [N] critical concepts, [N] supporting details, [N] key terms

Session: data/sessions/[topic]-[date]/
  ✓ Saved cornell.json
  ✓ Saved cornell.html

Open your notes:
  open data/sessions/[topic]-[date]/cornell.html
```

**What you see in the browser:**
- A page that looks like a Cornell notes sheet, not a generic webpage
- A small concept map at the top showing boxes connected by lines
- Review dates: "Next review: tomorrow | +3 days | +7 days"
- Two-column layout: questions on the left, notes hidden on the right
- Clicking a question shows a text box: "Write your answer before revealing"
- Typing something and clicking "Reveal" shows the full note
- A progress counter: "3 of 7 reviewed"
- Supporting details visible inside `<details>` blocks (click to expand)
- A Terminology section at the bottom
- A Gap Analysis section showing what was filtered out
- A blank "Your Notes & Reflections" area you can type in

**Before moving on to Phase 2:** The notes must be genuinely useful. Read them. Would
you actually study from this? If the 80/20 filter surfaced good concepts, the cue
questions are clear, and the summary is accurate — Phase 1 is complete.

---

## Part 4: The Finished Feature — Exact Usage

### Setup (done once, ever):
```bash
cd ~/Desktop/learning-tool
pip install -r requirements.txt
```
(You already have your `.env` file with the API key.)

### Every time you want to make notes:

**Step 1:** Create a session folder and paste your text
```bash
mkdir -p data/sessions/my-topic
```
Then open `data/sessions/my-topic/input.txt` in any text editor, paste your text, save.

**Step 2:** Run the pipeline
```bash
python src/note_engine.py data/sessions/my-topic/input.txt
```

**Step 3:** Open your notes
```bash
open data/sessions/my-topic/cornell.html
```
(On Mac, `open` launches the file in your default browser.)

### What appears in your terminal:
```
═══════════════════════════════════════════
 ATLAS — Note Engine
═══════════════════════════════════════════

Step 1/4  Detecting field...
          Field:       Cardiovascular Physiology
          Sub-domain:  Renin-Angiotensin-Aldosterone System
          Shadow exam: Diagnose and manage a hypertensive patient
                       with acute kidney injury
          Heuristic:   System-Based (Feedback Loops)

Step 2/4  Analyzing with 80/20 filter...
          (this usually takes 15–25 seconds)

Step 3/4  Building output...
          Critical concepts: 8
          Supporting details: 5
          Key terms: 4
          Omission risk: low

Step 4/4  Saving session...
          Session: data/sessions/RAAS-2025-08-14/
          ✓ data/sessions/RAAS-2025-08-14/cornell.json
          ✓ data/sessions/RAAS-2025-08-14/cornell.html

═══════════════════════════════════════════
 Done. Open your notes:
 open data/sessions/RAAS-2025-08-14/cornell.html
═══════════════════════════════════════════
```

### What your notes file contains:
- A self-contained `.html` file with no external dependencies
- Works offline, on any computer, forever
- Every interactive feature described in research.md Section 4

---

## Part 5: Edge Cases

These are situations the pipeline will encounter. We handle them before they become
silent failures.

---

### Edge Case 1: Very Short Text (fewer than ~150 words)

**What happens:** Claude cannot meaningfully apply 80/20 filtering to a paragraph.
There is not enough material to distinguish foundational concepts from supporting
details. The JSON will likely have 1-2 concepts and an empty or useless summary.

**How we handle it:**
- `load_text()` counts the words in the input before making any API calls
- If the word count is below 150, it prints a warning:
  ```
  Warning: Your text is only 87 words. The 80/20 filter works best with 
  at least 300 words. Paste more content for better results.
  Do you want to continue anyway? (y/n)
  ```
- If the user says yes, we proceed. If no, we exit cleanly with no API calls made
  (important because API calls cost money).

---

### Edge Case 2: Very Long Text (more than ~8,000 words)

**What happens:** Claude has a context window limit. A very long text might exceed
what can be sent in one prompt. Even if it doesn't hit the limit, Claude may produce
too many concepts to be useful — 30 critical concepts is not a useful 80/20 filter.

**How we handle it:**
- `load_text()` also counts words and triggers a different warning above 8,000:
  ```
  Warning: Your text is 11,400 words. Very long texts can produce too many concepts
  to study effectively. Consider:
    1. Paste one section at a time (recommended)
    2. Continue anyway — the mental budget instruction will limit output size
  Which would you prefer? (1/2)
  ```
- If they continue, the "mental budget" instruction in the prompt (from research.md)
  naturally limits the concept count. Claude is instructed not to exceed a density
  appropriate to the material.

---

### Edge Case 3: Text With No Clear Structure (stream of consciousness, bullet dumps)

**What happens:** If the text is unstructured — a list of loosely related facts, a
stream of notes with no logical flow, mixed topics — Claude may struggle to identify
meaningful critical concepts. It may produce generic cues or surface the wrong 20%.

**How we handle it:**
- This is handled at the prompt level. The pre-flight step detects the structure and
  the `heuristic_type` guides the main analysis. Claude is explicitly told to look for
  the highest-connectivity concepts regardless of where they appear in the text.
- In `validate_notes()`, we check whether the `importance` field on each concept
  contains meaningful content (more than 5 words). If all importance fields are short
  or identical, we print a warning: "The analysis may not have identified clear 80/20
  concepts. Consider using a more focused piece of text."
- We never crash. We produce whatever notes the AI generated, flagged with the warning.

---

### Edge Case 4: API Key Not Set or Invalid

**What happens:** `get_client()` will fail immediately.

**How we handle it:**
- Catch the authentication error in `get_client()`
- Print a clear message:
  ```
  Error: No API key found.
  
  To fix this:
  1. Open the file ~/Desktop/learning-tool/.env
  2. Make sure it contains this line:
     ANTHROPIC_API_KEY=your-key-here
  3. Get your key from: console.anthropic.com
  ```
- Exit cleanly. No crash, no stack trace.

---

### Edge Case 5: Claude Returns Malformed JSON

**What happens:** Occasionally, despite instructions, Claude returns JSON with a syntax
error, or wraps it in unexpected formatting.

**How we handle it:**
- `parse_response()` strips markdown fences first (the most common issue)
- If `json.loads()` still fails, save the raw response to
  `data/sessions/debug_response.txt` so no information is lost
- Print: "The AI response was not valid JSON. The raw response has been saved to
  debug_response.txt so you can inspect it. This is rare — try running again."
- Exit cleanly. Never silently discard the AI's response.

---

### Edge Case 6: Network Interruption Mid-Call

**What happens:** The API call starts but the connection drops before a response arrives.

**How we handle it:**
- The Anthropic library raises a specific network exception
- Catch it in `call_claude()` and print: "Network error during API call. Check your
  internet connection and try again. (Your input.txt was not modified.)"
- Exit cleanly.

---

## Part 6: Build Order Summary

```
Stage 0: Environment Setup
  → requirements.txt, .env, .gitignore
  → install packages
  → verify imports work

Stage 1: API Client
  → src/api_client.py (get_client, call_claude)
  → quick test: send "Say hello" to Claude

✅ CHECKPOINT 1: Claude responds in terminal

Stage 2: Core Pipeline (no HTML yet)
  → src/note_engine.py (all 8 functions + main)
  → main() calls a placeholder instead of build_html
  → test with real input text

✅ CHECKPOINT 2: cornell.json contains real, meaningful notes

Stage 3: HTML Builder
  → src/html_builder.py (all 9 functions)
  → built and verified in browser incrementally
  → wire into note_engine.py main()
  → run full end-to-end test

✅ CHECKPOINT 3: cornell.html opens in browser, fully interactive

Phase 1 complete.
```

---

## Decisions Log

The following decisions were made during planning. Each is logged in `.claude/decisions.md`
as well.

| Decision | Reason |
|----------|--------|
| Split into 3 files (api_client, note_engine, html_builder) | Single responsibility — each file has one job. If the HTML changes, only html_builder.py changes. |
| Two-step AI call (pre-flight + main) | Pre-flight eliminates Expert Blindness. Main analysis is calibrated to the correct domain and level. |
| Build pipeline before HTML | Can verify data quality before worrying about presentation. JSON is inspectable. |
| Word count check before API call | API calls cost money. Don't make an expensive call on 50 words of text. |
| Save raw response on JSON parse failure | Never discard AI output silently. The response may be recoverable. |
| Session folders named [topic]-[date] | Human-readable, sortable by date, one folder = one complete study session. |
