# ATLAS — Decisions Log

*Record every significant design or technical decision here, with the reason why.*

---

## Phase 1 Planning Decisions

| Decision | Reason |
|----------|--------|
| Split into 3 source files (api_client, note_engine, html_builder) | Single responsibility — each file has one job. HTML changes don't touch pipeline logic. |
| Two-step AI call (pre-flight + main analysis) | Pre-flight detects domain and builds persona, eliminating Expert Blindness in the 80/20 filter. |
| Build pipeline before HTML builder | Verify data quality (cornell.json) before building presentation layer. |
| Word count check before API call | Prevent wasted API spend on inputs too short for meaningful filtering. |
| Save raw Claude response on JSON parse failure | Never silently discard AI output — even broken responses may be recoverable. |
| Session folders named [topic]-[date] | Human-readable, date-sortable, one folder = one complete self-contained study session. |
| Prompt template as a top-level constant, not buried in build_main_prompt() | Easy to read, adjust, and improve without touching pipeline logic. |
