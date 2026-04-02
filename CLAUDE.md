# ATLAS — Adaptive Total Learning & Assessment System

## What it does
Takes any input text and runs it through a 4-phase learning pipeline:
1. Cornell notes with 80/20 filtering
2. Anki cloze card export
3. Feynman technique practice with scoring
4. MCAT-difficulty testing with UWorld-style explanations

## Stack
- **Python**: all processing and pipeline scripts
- **HTML/CSS/JS**: all interactive browser outputs (single files, no external dependencies)
- **Data**: JSON for session data, CSV for Anki export

## Folder structure
- `/src` — Python pipeline scripts
- `/data/sessions/[topic-date]/` — one folder per study session
- `/tools` — deterministic utility scripts, no AI
- `/templates` — HTML templates for note and test outputs
- `/.claude` — session files (decisions, lessons, plans)

## Conventions
- Every Python function gets a plain English comment
- Keep functions small — one job per function
- All HTML outputs must be single self-contained files
- Never use external CDNs or internet dependencies
- All interactive features must work offline

## Commands

**Generate Cornell notes from a text file:**
```
python3 src/note_engine.py data/sessions/my-topic/input.txt
```

**Test API connection:**
```
python3 src/api_client.py
```

**Install dependencies (first time only):**
```
pip3 install -r requirements.txt
```

## Never do without asking me
- Delete anything in /data
- Change the data format of existing session files
- Add external dependencies without explaining why

## Learning mode
- I am a complete beginner
- Comment all code in plain English
- Explain what an error means before fixing it
- Tell me why you chose one approach over another
- When I could learn something, teach me
