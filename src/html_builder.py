"""
html_builder.py — Builds the self-contained HTML Cornell notes file.

One job: take a notes dictionary (from note_engine.py) and return
a complete HTML string. Never reads from disk, never calls any API.
"""

import html
from datetime import date, timedelta


def _e(text):
    """Escape HTML special characters. Called on every piece of user/AI content."""
    return html.escape(str(text))


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

def build_css():
    """Returns the complete stylesheet as a string. All styles are embedded —
    no external files, no CDNs, works offline forever."""
    return """
    :root {
        --bg:           #fafaf7;
        --bg-cue:       #f0ede0;
        --accent:       #2c5f9e;
        --accent-lt:    #e8f0fb;
        --warn:         #c96a0b;
        --warn-lt:      #fef3e2;
        --green:        #2a7a50;
        --green-lt:     #e8f5ef;
        --purple:       #6b4a8f;
        --purple-lt:    #f3eefb;
        --text:         #1a1a2e;
        --muted:        #6b7280;
        --border:       #d8d4c8;
        --border-dk:    #b0ad9f;
        --shadow:       0 2px 8px rgba(0,0,0,0.07);
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: Georgia, 'Times New Roman', serif;
        font-size: 15px;
        line-height: 1.65;
        color: var(--text);
        background: var(--bg);
        padding: 20px;
        max-width: 1120px;
        margin: 0 auto;
    }
    h1 { font-size: 1.5rem; color: var(--accent); letter-spacing: -0.02em; }
    p  { margin: 0; }

    /* Buttons */
    button {
        font-family: Arial, sans-serif;
        font-size: 0.8rem;
        cursor: pointer;
        border-radius: 5px;
        padding: 6px 14px;
        border: 1px solid var(--border);
        background: white;
        color: var(--text);
        transition: background 0.15s, color 0.15s, border-color 0.15s;
    }
    button:hover:not(:disabled) { background: var(--accent); color: white; border-color: var(--accent); }
    button:disabled { opacity: 0.38; cursor: not-allowed; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.7} }
    button.ready { background: var(--accent); color: white; border-color: var(--accent); animation: pulse 2.5s ease-in-out infinite; }

    /* Page header */
    .page-header {
        display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
        padding: 18px 22px; background: white;
        border: 1px solid var(--border); border-radius: 8px;
        margin-bottom: 13px; box-shadow: var(--shadow);
    }
    .field-label { font-family: Arial, sans-serif; font-size: 0.8rem; color: var(--muted); margin-top: 5px; }
    .header-controls { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
    .progress-display {
        font-family: Arial, sans-serif; font-size: 0.8rem; color: var(--muted);
        background: var(--bg); padding: 4px 12px;
        border-radius: 20px; border: 1px solid var(--border); white-space: nowrap;
    }

    /* Review banner */
    .review-banner {
        display: flex; align-items: center; flex-wrap: wrap; gap: 8px 18px;
        padding: 9px 16px; background: var(--accent-lt);
        border: 1px solid var(--accent); border-radius: 6px;
        margin-bottom: 13px; font-family: Arial, sans-serif; font-size: 0.8rem; color: var(--accent);
    }
    .review-banner b { margin-right: 4px; }
    .rdates { display: flex; gap: 16px; flex-wrap: wrap; }
    .rdate b { font-weight: bold; }

    /* Concept map */
    .map-container {
        background: white; border: 1px solid var(--border); border-radius: 8px;
        padding: 14px 18px; margin-bottom: 13px; overflow-x: auto;
    }
    .section-label {
        font-family: Arial, sans-serif; font-size: 0.7rem;
        text-transform: uppercase; letter-spacing: 0.09em;
        color: var(--muted); margin-bottom: 10px;
    }

    /* Cornell layout */
    .cornell-wrap {
        border: 1px solid var(--border); border-radius: 8px;
        overflow: hidden; margin-bottom: 13px; box-shadow: var(--shadow);
    }
    .cornell-head {
        display: grid; grid-template-columns: 35% 65%;
        background: var(--accent); color: white;
        font-family: Arial, sans-serif; font-size: 0.7rem;
        text-transform: uppercase; letter-spacing: 0.09em;
    }
    .cornell-head > div { padding: 8px 16px; }

    .crow {
        display: grid; grid-template-columns: 35% 65%;
        border-bottom: 1px solid var(--border); background: white;
    }
    .crow:last-child { border-bottom: none; }
    .crow.revealed { background: #fdfcf8; }

    /* Cue column */
    .cue-col {
        background: var(--bg-cue); padding: 16px;
        border-right: 2px solid var(--accent);
        display: flex; flex-direction: column; gap: 10px;
    }
    .crow.revealed .cue-col { background: var(--accent-lt); }
    .cue-q  { font-size: 0.92rem; line-height: 1.55; }
    .cmp-cue {
        font-family: Arial, sans-serif; font-size: 0.79rem; font-style: italic;
        color: var(--muted); padding-left: 9px;
        border-left: 3px solid var(--warn); line-height: 1.5;
    }

    /* Notes column */
    .notes-col { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
    .show-draft-btn { align-self: flex-start; }

    /* Force Draft gate */
    .draft-area { display: none; flex-direction: column; gap: 7px; }
    .draft-area textarea {
        width: 100%; padding: 9px 12px;
        border: 1px solid var(--border); border-radius: 5px;
        font-family: Georgia, serif; font-size: 0.88rem;
        line-height: 1.5; color: var(--text); background: var(--bg);
        resize: vertical; min-height: 56px; transition: border-color 0.15s;
    }
    .draft-area textarea:focus { outline: none; border-color: var(--accent); background: white; }
    .draft-area textarea::placeholder { color: #bbb; font-style: italic; }
    .draft-controls { display: flex; align-items: center; gap: 9px; }
    .draft-hint { font-family: Arial, sans-serif; font-size: 0.72rem; color: var(--muted); font-style: italic; }

    /* Note content */
    .note-content { display: none; }
    .note-text { font-size: 0.91rem; line-height: 1.68; }
    .note-text p { margin-bottom: 8px; }
    .note-text p:last-child { margin-bottom: 0; }

    .importance-block {
        margin-top: 8px; padding: 9px 13px;
        background: var(--accent-lt); border-left: 3px solid var(--accent);
        border-radius: 0 4px 4px 0;
        font-family: Arial, sans-serif; font-size: 0.79rem;
        line-height: 1.55; color: var(--accent);
    }
    .importance-block strong {
        display: block; margin-bottom: 3px;
        font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.07em;
    }
    .hide-btn { align-self: flex-start; font-size: 0.72rem; color: var(--muted); padding: 3px 8px; }

    /* Diagram placeholder — placed INSIDE note, above text (cognitive load rule) */
    .diagram-box {
        border: 2px dashed var(--accent); border-radius: 6px;
        padding: 13px; background: var(--accent-lt); margin-bottom: 12px;
    }
    .diagram-box .dtitle {
        font-family: Arial, sans-serif; font-size: 0.73rem; font-weight: bold;
        text-transform: uppercase; letter-spacing: 0.07em;
        color: var(--accent); margin-bottom: 7px;
    }
    .diagram-box .ddesc {
        font-family: Arial, sans-serif; font-size: 0.79rem;
        line-height: 1.6; color: var(--text); white-space: pre-wrap;
    }
    .diagram-box .dprompt {
        margin-top: 8px; font-family: Arial, sans-serif;
        font-size: 0.7rem; color: var(--muted); font-style: italic;
    }

    /* Supporting details — native <details>/<summary> */
    details.sd { margin-top: 7px; border: 1px solid var(--border); border-radius: 4px; overflow: hidden; }
    details.sd summary {
        padding: 6px 12px; cursor: pointer;
        font-family: Arial, sans-serif; font-size: 0.77rem;
        color: var(--muted); background: var(--bg);
        user-select: none; list-style: none;
    }
    details.sd summary::-webkit-details-marker { display: none; }
    details.sd summary::before { content: "▶ "; font-size: 0.65rem; }
    details.sd[open] summary::before { content: "▼ "; }
    details.sd.exception  summary { color: var(--warn);   background: var(--warn-lt);   border-left: 3px solid var(--warn);   }
    details.sd.intersystem summary { color: var(--purple); background: var(--purple-lt); border-left: 3px solid var(--purple); }
    details.sd.clinical   summary { color: var(--green);  background: var(--green-lt);  border-left: 3px solid var(--green);  }
    .detail-body { padding: 10px 14px; background: white; border-top: 1px solid var(--border); line-height: 1.6; font-size: 0.87rem; }
    .detail-q { font-style: italic; color: var(--muted); font-family: Arial, sans-serif; font-size: 0.77rem; margin-bottom: 5px; }

    /* Summary */
    .summary-section {
        background: white; border: 1px solid var(--border); border-radius: 8px;
        padding: 18px 22px; margin-bottom: 13px; box-shadow: var(--shadow);
    }
    .summary-section h2 {
        font-family: Arial, sans-serif; font-size: 0.7rem; font-weight: normal;
        text-transform: uppercase; letter-spacing: 0.09em;
        color: var(--muted); margin-bottom: 11px;
    }
    .summary-unlocked { display: none; font-family: Arial, sans-serif; font-size: 0.72rem; color: var(--muted); font-style: italic; margin-top: 6px; }
    .summary-text {
        display: none; font-size: 0.93rem; line-height: 1.7;
        padding: 14px 16px; background: var(--accent-lt);
        border-left: 4px solid var(--accent); border-radius: 0 5px 5px 0; margin-top: 11px;
    }

    /* Terminology */
    .term-section {
        background: white; border: 1px solid var(--border); border-radius: 8px;
        padding: 18px 22px; margin-bottom: 13px; box-shadow: var(--shadow);
    }
    .term-section h2 {
        font-family: Arial, sans-serif; font-size: 0.7rem; font-weight: normal;
        text-transform: uppercase; letter-spacing: 0.09em; color: var(--green);
        padding-bottom: 8px; border-bottom: 2px solid var(--green); margin-bottom: 14px;
    }
    .term-entry { margin-bottom: 14px; padding-left: 13px; border-left: 3px solid var(--green); }
    .term-name { font-family: Arial, sans-serif; font-weight: bold; font-size: 0.9rem; color: var(--green); }
    .term-def  { font-size: 0.87rem; line-height: 1.6; margin-top: 3px; }
    .term-why  { font-family: Arial, sans-serif; font-size: 0.73rem; color: var(--muted); font-style: italic; margin-top: 3px; }

    /* Gap analysis */
    .gap-section {
        background: white; border: 1px solid var(--border); border-radius: 8px;
        padding: 18px 22px; margin-bottom: 13px; box-shadow: var(--shadow);
    }
    .gap-section h2 {
        font-family: Arial, sans-serif; font-size: 0.7rem; font-weight: normal;
        text-transform: uppercase; letter-spacing: 0.09em; color: var(--purple);
        padding-bottom: 8px; border-bottom: 2px solid var(--purple); margin-bottom: 14px;
    }
    .gap-entry {
        margin-bottom: 10px; padding: 10px 14px;
        background: var(--purple-lt); border-left: 3px solid var(--purple);
        border-radius: 0 4px 4px 0; font-size: 0.87rem; line-height: 1.6;
    }
    .gap-entry.warn-entry { background: var(--warn-lt); border-left-color: var(--warn); }
    .gap-entry.neutral    { background: var(--bg);       border-left-color: var(--border-dk); }
    .gap-lbl {
        font-family: Arial, sans-serif; font-size: 0.68rem; font-weight: bold;
        text-transform: uppercase; letter-spacing: 0.07em;
        color: var(--purple); margin-bottom: 5px;
    }
    .gap-entry.warn-entry .gap-lbl { color: var(--warn); }
    .gap-entry.neutral    .gap-lbl { color: var(--muted); }
    .rbadge {
        display: inline-block; padding: 2px 9px; border-radius: 12px; margin-right: 6px;
        font-family: Arial, sans-serif; font-size: 0.7rem; font-weight: bold;
        text-transform: uppercase; letter-spacing: 0.06em;
    }
    .r-low    { background: var(--green-lt);  color: var(--green); }
    .r-medium { background: var(--warn-lt);   color: var(--warn);  }
    .r-high   { background: #fee2e2; color: #c53030; }

    /* Reflections */
    .reflect-section {
        background: white; border: 1px solid var(--border); border-radius: 8px;
        padding: 18px 22px; margin-bottom: 32px; box-shadow: var(--shadow);
    }
    .reflect-section h2 {
        font-family: Arial, sans-serif; font-size: 0.7rem; font-weight: normal;
        text-transform: uppercase; letter-spacing: 0.09em;
        color: var(--muted); margin-bottom: 10px;
    }
    .reflect-area {
        min-height: 90px; padding: 11px 13px;
        border: 1px dashed var(--border); border-radius: 5px;
        font-family: Georgia, serif; font-size: 0.9rem;
        line-height: 1.65; color: var(--text); background: var(--bg); outline: none;
    }
    .reflect-area:focus { border-color: var(--accent); background: white; }
    .reflect-area:empty::before { content: attr(data-ph); color: #bbb; font-style: italic; pointer-events: none; }
    .print-tip { margin-top: 9px; font-family: Arial, sans-serif; font-size: 0.72rem; color: var(--muted); font-style: italic; }

    /* Draft input row: textarea + mic button side by side */
    .draft-input-row { display: flex; gap: 8px; align-items: flex-start; }
    .draft-input-row textarea { flex: 1; }
    .mic-btn {
        flex-shrink: 0; width: 38px; height: 38px; padding: 0;
        border-radius: 50%; font-size: 1.1rem;
        display: flex; align-items: center; justify-content: center;
        border: 1px solid var(--border); background: white; cursor: pointer;
        transition: background 0.15s, border-color 0.15s;
    }
    .mic-btn:hover { background: var(--accent-lt); border-color: var(--accent); }
    .mic-btn.listening {
        background: #fee2e2; border-color: #9b2226; color: #9b2226;
        animation: pulse 1s ease-in-out infinite;
    }
    .mic-hint { font-family: Arial, sans-serif; font-size: 0.7rem; color: var(--muted); font-style: italic; }

    /* Reference note (model answer, shown after reveal) */
    .ref-note-wrap { margin-top: 10px; }
    .ref-note-lbl {
        font-family: Arial, sans-serif; font-size: 0.68rem; font-weight: bold;
        text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); margin-bottom: 4px;
    }
    .ref-note {
        padding: 7px 11px; background: var(--bg);
        border: 1px dashed var(--border-dk); border-radius: 4px;
        font-family: Arial, monospace; font-size: 0.82rem;
        line-height: 1.6; color: var(--text); white-space: pre-line;
    }

    /* Grade result */
    .grade-area {
        display: none; margin-top: 8px; padding: 8px 12px;
        background: #fafaf7; border: 1px solid var(--border); border-radius: 4px;
        font-family: Arial, sans-serif; font-size: 0.85rem; line-height: 1.8;
    }
    .grade-response { margin-bottom: 5px; }
    .grade-missed { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; font-size: 0.78rem; }
    .grade-missed-lbl { font-weight: bold; color: #9b2226; }
    .grade-missed-item {
        background: #fee2e2; color: #9b2226; padding: 1px 8px;
        border-radius: 10px; font-size: 0.74rem;
    }

    /* Telegraphic note — preserve line breaks from shorthand */
    .note-text { font-size: 0.91rem; line-height: 1.68; white-space: pre-line; }

    /* Print */
    @media print {
        body { padding: 0; max-width: none; font-size: 13px; }
        .review-banner, .map-container { display: none; }
        .draft-area, .hide-btn,
        #hide-all-btn, #reveal-summary-btn, .print-tip { display: none !important; }
        .note-content { display: block !important; }
        .summary-text { display: block !important; }
        button { display: none !important; }
        .crow { page-break-inside: avoid; }
        details.sd .detail-body { display: block !important; }
    }
"""


# ─────────────────────────────────────────────────────────────────────────────
# JAVASCRIPT
# Uses __N__ as a placeholder for the total concept count.
# build_javascript() replaces it with the real number.
# We use a plain string (not f-string) so JS curly braces don't need escaping.
# ─────────────────────────────────────────────────────────────────────────────

_JS = """
const TOTAL = __N__;        // total concept rows — injected at generation time
const API_KEY = "__API_KEY__"; // Anthropic key for browser-side grading calls
let done = 0;               // how many notes have been submitted

// Enable Submit once the user has typed or spoken something.
function onInput(i) {
    var hasText = document.getElementById('d-' + i).value.trim().length > 0;
    document.getElementById('rb-' + i).disabled = !hasText;
}

// --- Speech recognition (Chrome / Safari) ---
var _recs = {};  // one recognizer instance per card

function toggleMic(i) {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Speech recognition is not available. Try Chrome.'); return; }
    // Second click stops the recognizer
    if (_recs[i]) { try { _recs[i].stop(); } catch(e){} return; }
    var rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    _recs[i] = rec;
    var mb = document.getElementById('mic-' + i);
    mb.classList.add('listening');
    mb.textContent = '\u23F9';  // ⏹ stop symbol
    rec.onresult = function(e) {
        var t = '';
        for (var j = 0; j < e.results.length; j++) t += e.results[j][0].transcript;
        document.getElementById('d-' + i).value = t;
        onInput(i);
    };
    rec.onend = function() { _recs[i] = null; mb.classList.remove('listening'); mb.textContent = '\U0001F3A4'; };
    rec.onerror = function() { _recs[i] = null; mb.classList.remove('listening'); mb.textContent = '\U0001F3A4'; };
    rec.start();
}

// --- Grading via Anthropic API ---
async function gradeAnswer(userText, refNote) {
    var prompt = 'You are a study grader. Compare the student response to the reference note.\\nReturn ONLY a valid JSON object — no preamble, no markdown fences, nothing else.\\nFormat exactly: {"user_phrases":[{"text":"...","status":"match|fuzzy|miss"}],"missed_concepts":["..."]}\\nStatus: match=correct and present, fuzzy=partially correct or different wording, miss=absent or wrong.\\nSplit the student response into meaningful phrases of ~3-8 words each.\\nReference note: ' + refNote + '\\nStudent response: ' + userText;
    var res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
            'x-api-key': API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
            'anthropic-dangerous-direct-browser-access': 'true'
        },
        body: JSON.stringify({
            model: 'claude-haiku-4-5-20251001',
            max_tokens: 512,
            messages: [{ role: 'user', content: prompt }]
        })
    });
    if (!res.ok) throw new Error('API ' + res.status);
    var data = await res.json();
    var raw = data.content[0].text.replace(/```json?\\n?|```/g, '').trim();
    return JSON.parse(raw);
}

function renderGrade(i, grade) {
    var area = document.getElementById('grade-' + i);
    if (!area) return;
    var h = '<div class="grade-response">';
    (grade.user_phrases || []).forEach(function(p) {
        var c = p.status === 'match' ? '#2d6a4f' : (p.status === 'fuzzy' ? '#b5830a' : '#9b2226');
        var w = p.status === 'match' ? '600' : '400';
        h += '<span style="color:' + c + ';font-weight:' + w + '">' + _esc(p.text) + '</span> ';
    });
    h += '</div>';
    var missed = grade.missed_concepts || [];
    if (missed.length) {
        h += '<div class="grade-missed"><span class="grade-missed-lbl">Missed:&nbsp;</span>';
        missed.forEach(function(m) { h += '<span class="grade-missed-item">' + _esc(m) + '</span>'; });
        h += '</div>';
    }
    area.innerHTML = h;
    area.style.display = 'block';
}

function _esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Submit: grade the answer, then reveal the note.
async function submit(i) {
    var userText = document.getElementById('d-' + i).value.trim();
    var refEl = document.getElementById('ref-' + i);
    var refNote = refEl ? refEl.textContent.trim() : '';
    var btn = document.getElementById('rb-' + i);
    btn.disabled = true;
    btn.textContent = 'Grading\u2026';

    // Grade only when the API key is present (grading requires internet)
    if (refNote && API_KEY && API_KEY.length > 0) {
        try {
            var grade = await gradeAnswer(userText, refNote);
            renderGrade(i, grade);
        } catch(e) {
            // Grading failed (offline, API error) — reveal without grade
        }
    }

    document.getElementById('da-' + i).style.display = 'none';
    document.getElementById('nc-' + i).style.display = 'block';
    document.getElementById('row-' + i).classList.add('revealed');
    done++;
    document.getElementById('rc').textContent = done;
    if (done >= TOTAL) {
        var sb = document.getElementById('reveal-summary-btn');
        sb.disabled = false;
        sb.classList.add('ready');
        sb.textContent = 'Reveal Summary \u2713 All concepts reviewed';
    }
}

// Re-hide for a fresh attempt.
function rehide(i) {
    if (_recs[i]) { try { _recs[i].stop(); } catch(e){} }
    document.getElementById('nc-' + i).style.display = 'none';
    var da = document.getElementById('da-' + i);
    da.style.display = 'flex';
    document.getElementById('d-' + i).value = '';
    var btn = document.getElementById('rb-' + i);
    btn.disabled = true;
    btn.textContent = 'Submit';
    var grade = document.getElementById('grade-' + i);
    if (grade) { grade.innerHTML = ''; grade.style.display = 'none'; }
    document.getElementById('row-' + i).classList.remove('revealed');
    done = Math.max(0, done - 1);
    document.getElementById('rc').textContent = done;
    if (done < TOTAL) {
        var sb = document.getElementById('reveal-summary-btn');
        sb.disabled = true;
        sb.classList.remove('ready');
        sb.textContent = 'Reveal Summary \u2014 review all cues first';
    }
}

// Reset all cards for a fresh practice run.
function hideAll() {
    for (var i = 0; i < TOTAL; i++) {
        if (document.getElementById('row-' + i).classList.contains('revealed')) rehide(i);
    }
}

// Reveal summary — only unlocked after all cards are submitted.
function showSummary() {
    document.getElementById('summary-text').style.display = 'block';
    document.getElementById('reveal-summary-btn').style.display = 'none';
    document.getElementById('summary-unlocked').style.display = 'block';
}
"""


def build_javascript(total_concepts, api_key=""):
    """Injects the concept count and API key into the JS template."""
    return _JS.replace("__N__", str(total_concepts)).replace("__API_KEY__", api_key)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def build_spaced_repetition_block(creation_date):
    """
    Returns a banner showing the four spaced-repetition review dates.
    Dates are calculated at generation time (+1, +3, +7, +14 days).
    This is a nudge, not a scheduler — it just reminds the user when to reopen the file.
    """
    schedule = [(1, "Tomorrow"), (3, "+3 days"), (7, "+7 days"), (14, "+14 days")]
    dates_html = ""
    for days, label in schedule:
        d = (creation_date + timedelta(days=days)).strftime("%b %d")
        dates_html += f'<span class="rdate"><b>{label}:</b> {d}</span>'
    return f"""<div class="review-banner">
  <b>Next reviews:</b>
  <div class="rdates">{dates_html}</div>
</div>"""


def build_concept_map_svg(critical_concepts):
    """
    Returns an SVG showing each concept as a labeled box, with dashed lines
    connecting concepts that are linked via the relates_to field.
    Placed at the top of the notes so the learner sees the knowledge structure
    before diving into details.
    """
    N = len(critical_concepts)
    if N == 0:
        return ""

    BW, BH = 165, 52      # box width / height
    GX, GY = 28, 32       # gap between boxes
    PAD    = 22           # outer padding
    COLS   = min(4, N)
    ROWS   = (N + COLS - 1) // COLS

    W = COLS * BW + (COLS - 1) * GX + 2 * PAD
    H = ROWS * BH + (ROWS - 1) * GY + 2 * PAD

    # Centre coordinates for each box
    centres = []
    for i in range(N):
        col, row = i % COLS, i // COLS
        x = PAD + col * (BW + GX)
        y = PAD + row * (BH + GY)
        centres.append((x, y, x + BW // 2, y + BH // 2))

    cue_idx = {c["cue"]: i for i, c in enumerate(critical_concepts)}

    # Lines first (drawn behind boxes)
    lines = []
    seen  = set()
    for i, concept in enumerate(critical_concepts):
        for rel in concept.get("relates_to", []):
            j = cue_idx.get(rel)
            if j is not None and i != j:
                pair = tuple(sorted([i, j]))
                if pair not in seen:
                    seen.add(pair)
                    cx1, cy1 = centres[i][2], centres[i][3]
                    cx2, cy2 = centres[j][2], centres[j][3]
                    lines.append(
                        f'<line x1="{cx1}" y1="{cy1}" x2="{cx2}" y2="{cy2}" '
                        f'stroke="#b0ad9f" stroke-width="1.5" stroke-dasharray="5,3"/>'
                    )

    # Boxes
    boxes = []
    for i, concept in enumerate(critical_concepts):
        x, y, cx, cy = centres[i]
        raw = concept.get("cue", f"Concept {i+1}")
        short = (raw[:20] + "\u2026") if len(raw) > 20 else raw
        short = _e(short)
        boxes.append(
            f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="6" '
            f'fill="#e8f0fb" stroke="#2c5f9e" stroke-width="1.5"/>'
            f'<text x="{cx}" y="{y+18}" font-family="Arial" font-size="10" '
            f'font-weight="bold" fill="#2c5f9e" text-anchor="middle">C{i+1}</text>'
            f'<text x="{cx}" y="{y+36}" font-family="Arial" font-size="9.5" '
            f'fill="#374151" text-anchor="middle">{short}</text>'
        )

    noun = "concept" if N == 1 else "concepts"
    inner = "\n  ".join(lines + boxes)
    return f"""<div class="map-container">
  <p class="section-label">Concept map &mdash; {N} {noun}</p>
  <svg width="{W}" height="{H}" style="display:block;overflow:visible;">
  {inner}
  </svg>
</div>"""


def build_supporting_detail_html(detail):
    """
    Returns an HTML <details>/<summary> block for one supporting detail.
    The CSS class varies by type: exception → amber, intersystem → purple, clinical → green.
    """
    cue_text  = _e(detail.get("cue",  ""))
    note_text = _e(detail.get("note", ""))
    dtype     = detail.get("detail_type", "supporting_detail")

    cfg = {
        "supporting_detail":   ("",            "Supporting detail"),
        "important_exception": ("exception",   "\u26a0 Important exception"),
        "clinical_application":("clinical",    "Clinical application"),
        "intersystem_link":    ("intersystem", "\u2194 Intersystem link"),
    }
    css_class, label = cfg.get(dtype, ("", "Detail"))

    return f"""<details class="sd {css_class}">
  <summary>{label}</summary>
  <div class="detail-body">
    <div class="detail-q">{cue_text}</div>
    <div>{note_text}</div>
  </div>
</details>"""


def build_concept_row(concept, index, concept_details):
    """
    Returns the HTML for one complete Cornell row: cue column on the left,
    Force Draft gate + note content on the right.
    The diagram placeholder (if any) is placed INSIDE the note, above the
    explanatory text — this is the cognitive load / split-attention fix
    from research.md Section 7 Trap 2.
    """
    cue        = _e(concept.get("cue", ""))
    comp_cue   = _e(concept.get("comparison_cue", ""))
    note_text  = _e(concept.get("note", ""))
    ref_note   = _e(concept.get("reference_note", ""))
    importance = _e(concept.get("importance", ""))
    diag_need  = concept.get("diagram_needed", False)
    diag_desc  = _e(concept.get("diagram_description", ""))

    # Diagram placeholder — only rendered when diagram_needed is true
    diag_html = ""
    if diag_need and diag_desc:
        title = _e(concept.get("cue", "")[:50])
        diag_html = f"""<div class="diagram-box">
  <div class="dtitle">Draw this: {title}</div>
  <div class="ddesc">{diag_desc}</div>
  <div class="dprompt">Draw this diagram by hand to reinforce the concept.</div>
</div>"""

    # Importance block
    imp_html = ""
    if importance:
        imp_html = f"""<div class="importance-block">
  <strong>Why this is in the 20%</strong>
  {importance}
</div>"""

    # Reference note block (shown after reveal, used as grading target)
    ref_html = ""
    if ref_note:
        ref_html = f"""<div class="ref-note-wrap">
  <div class="ref-note-lbl">Model answer</div>
  <div class="ref-note" id="ref-{index}">{ref_note}</div>
</div>"""

    # Supporting details
    details_html = "".join(build_supporting_detail_html(d) for d in concept_details)

    return f"""<div class="crow" id="row-{index}">
  <div class="cue-col">
    <div class="cue-q">{cue}</div>
    <div class="cmp-cue">{comp_cue}</div>
  </div>
  <div class="notes-col">
    <div class="draft-area" id="da-{index}" style="display:flex">
      <div class="draft-input-row">
        <textarea id="d-{index}"
          placeholder="Write or speak your answer, then click Submit&hellip;"
          oninput="onInput({index})"></textarea>
        <button class="mic-btn" id="mic-{index}" onclick="toggleMic({index})" title="Click to dictate">&#127908;</button>
      </div>
      <p class="mic-hint">Mic works best in Chrome.</p>
      <div class="draft-controls">
        <button id="rb-{index}" disabled onclick="submit({index})">Submit</button>
        <span class="draft-hint">Type or speak something first &mdash; even a guess counts</span>
      </div>
    </div>
    <div class="note-content" id="nc-{index}">
      {diag_html}
      <div class="note-text">{note_text}</div>
      {ref_html}
      <div class="grade-area" id="grade-{index}"></div>
      {imp_html}
      {details_html}
      <button class="hide-btn" onclick="rehide({index})">&larr; Hide &amp; retry</button>
    </div>
  </div>
</div>"""


def build_terminology_section(key_terms):
    """
    Returns the Key Terms section. Surfaces vocabulary that cannot be derived
    from mechanism understanding alone — the Lexicon Layer (research.md Section 1).
    """
    if not key_terms:
        return ""
    terms = ""
    for t in key_terms:
        terms += f"""<div class="term-entry">
  <div class="term-name">{_e(t.get('term',''))}</div>
  <div class="term-def">{_e(t.get('definition',''))}</div>
  <div class="term-why">Why memorize: {_e(t.get('why_memorize',''))}</div>
</div>"""
    return f"""<div class="term-section">
  <h2>Key Terms &mdash; The Lexicon Layer</h2>
  {terms}
</div>"""


def build_gap_section(gap_analysis):
    """
    Returns the 'What Was Filtered Out' section.
    Makes the 80/20 filtering transparent — the learner can see exactly what
    was omitted and judge whether to dig deeper.
    """
    if not gap_analysis:
        return ""

    filtered  = _e(gap_analysis.get("content_filtered_out", ""))
    intersys  = _e(gap_analysis.get("intersystem_links_found", ""))
    nuances   = _e(gap_analysis.get("important_nuances_omitted", ""))
    risk_raw  = gap_analysis.get("omission_risk", "low")
    risk_esc  = _e(risk_raw)

    risk_level = "low"
    for lvl in ["high", "medium", "low"]:
        if lvl in risk_raw.lower():
            risk_level = lvl
            break

    skip = {"", "none", "n/a", "none found", "none identified", "not applicable"}

    entries = ""
    if filtered:
        entries += f"""<div class="gap-entry">
  <div class="gap-lbl">What was filtered out</div>
  <div>{filtered}</div>
</div>"""

    if intersys.lower().strip() not in skip:
        entries += f"""<div class="gap-entry">
  <div class="gap-lbl">Intersystem links found</div>
  <div>{intersys}</div>
</div>"""

    if nuances.lower().strip() not in skip:
        entries += f"""<div class="gap-entry warn-entry">
  <div class="gap-lbl">&#9888; Important nuances omitted</div>
  <div>{nuances}</div>
</div>"""

    entries += f"""<div class="gap-entry neutral">
  <div class="gap-lbl">Omission risk</div>
  <div><span class="rbadge r-{risk_level}">{risk_level}</span>{risk_esc}</div>
</div>"""

    return f"""<div class="gap-section">
  <h2>What Was Filtered Out</h2>
  {entries}
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ASSEMBLER
# ─────────────────────────────────────────────────────────────────────────────

def build_html(notes_dict, api_key=""):
    """
    Assembles the complete, self-contained HTML file from the notes dictionary.

    api_key is embedded as a JS constant so the browser can make grading calls.
    It is read from .env by note_engine.py and passed in — html_builder never
    touches the filesystem directly.

    Calls every other function in this file and combines their output into
    one valid HTML document. The returned string is written directly to
    cornell.html — no other processing needed.
    """
    topic     = _e(notes_dict.get("topic", "Cornell Notes"))
    fctx      = notes_dict.get("field_context", {})
    field     = _e(fctx.get("field", ""))
    sub       = _e(fctx.get("sub_domain", ""))
    summary   = _e(notes_dict.get("summary", ""))

    concepts  = notes_dict.get("critical_concepts", [])
    details   = notes_dict.get("supporting_details", [])
    terms     = notes_dict.get("key_terms", [])
    gap       = notes_dict.get("gap_analysis", {})

    n = len(concepts)

    # Build concept rows, attaching the right supporting details to each
    rows = ""
    for i, concept in enumerate(concepts):
        parent_details = [d for d in details if d.get("parent_concept_index") == i]
        rows += build_concept_row(concept, i, parent_details)

    field_line = field + (f" &mdash; {sub}" if sub else "")

    css        = build_css()
    js         = build_javascript(n, api_key=api_key)
    review     = build_spaced_repetition_block(date.today())
    cmap       = build_concept_map_svg(concepts)
    term_sec   = build_terminology_section(terms)
    gap_sec    = build_gap_section(gap)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cornell Notes: {topic}</title>
  <style>{css}</style>
</head>
<body>

<div class="page-header">
  <div>
    <h1>{topic}</h1>
    <p class="field-label">{field_line}</p>
  </div>
  <div class="header-controls">
    <div class="progress-display">
      <span id="rc">0</span>&nbsp;/&nbsp;{n} reviewed
    </div>
    <button id="hide-all-btn" onclick="hideAll()">Hide All Notes</button>
  </div>
</div>

{review}
{cmap}

<div class="cornell-wrap">
  <div class="cornell-head">
    <div>Cue Questions</div>
    <div>Notes &mdash; attempt your answer before revealing</div>
  </div>
  {rows}
</div>

<div class="summary-section">
  <h2>Summary &mdash; The 20% of the 20%</h2>
  <button id="reveal-summary-btn" disabled onclick="showSummary()">
    Reveal Summary &mdash; review all cues first
  </button>
  <p class="summary-unlocked" id="summary-unlocked">
    &#10003; Revealed after completing all cues.
  </p>
  <div id="summary-text" class="summary-text">{summary}</div>
</div>

{term_sec}
{gap_sec}

<div class="reflect-section">
  <h2>Your Notes &amp; Reflections</h2>
  <div contenteditable="true" class="reflect-area"
       data-ph="Click here to add your own notes, connections, and &lsquo;aha&rsquo; moments&hellip;"></div>
  <p class="print-tip">
    Tip: Cmd+P (Mac) or Ctrl+P (Windows) to &ldquo;Print to PDF&rdquo; &mdash;
    your personal notes will be included.
  </p>
</div>

<script>
{js}
</script>
</body>
</html>"""
