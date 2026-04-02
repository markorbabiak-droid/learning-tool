# ATLAS — Lessons Learned

*Record anything that broke, surprised us, or taught us something useful.*

---

## Phase 1 Build — Note Engine

**The .env format matters.** When the user pasted the API key, they pasted just the key
with no prefix. The file needs `ANTHROPIC_API_KEY=sk-ant-...` not just the raw key.
Fix: the `get_client()` function now explicitly checks for the placeholder value and
prints a clear error with instructions.

**Claude fills gaps the source text didn't cover.** On a 39-word input about mitochondria,
Claude correctly identified that oxidative phosphorylation was missing from the source
and included it in the notes — flagging the source as incomplete (omission_risk: high).
This is the right behavior for a learning tool. It means ATLAS teaches completeness,
not just summarization.

**`pip` vs `pip3` on Mac.** The `pip` command may not be on PATH on some Mac setups.
Use `pip3` instead. No code change needed — just use `pip3 install -r requirements.txt`.

**Use plain string + `.replace()` for JS templates, not f-strings.** JavaScript has
many curly braces. Using f-strings for JS would require escaping every `{` and `}` as
`{{` and `}}` — messy and error-prone. Storing JS as a plain string constant and using
`.replace("__PLACEHOLDER__", value)` for the one injected value is cleaner.

**Short text produces thin but valid output.** 39 words → 1-2 concepts, 3 key terms.
The mental budget instruction in the prompt correctly scaled down. The system doesn't
crash or produce garbage on short input — it produces proportionally smaller notes and
flags the limitation clearly. Good enough for demos; better with real content.

**The pipeline background-runs on slow networks.** The Anthropic API call takes
15-40 seconds. This is normal. The "this usually takes 15-30 seconds" message in the
terminal prevents the user from thinking it's frozen.

**`html.escape()` is essential.** Claude's output can contain `<`, `>`, `&`, and `"`
characters. If these aren't escaped before embedding in HTML, the page breaks silently.
The `_e()` helper in html_builder.py wraps every piece of AI content.
