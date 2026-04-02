# ATLAS Research — Phase 1: Note Engine

*Foundation document. Every design decision in Phase 1 traces back here.*
*Last expanded: integrated learning science traps and advanced prompt engineering.*

---

## Table of Contents

1. [The 80/20 Principle in Learning](#1-the-8020-principle-in-learning)
2. [Cornell Note Structure](#2-cornell-note-structure)
3. [The Gap Filler](#3-the-gap-filler)
4. [The HTML Output](#4-the-html-output)
5. [The Python Pipeline](#5-the-python-pipeline)
6. [What the AI Call Looks Like](#6-what-the-ai-call-looks-like)
7. [Learning Science Traps to Avoid](#7-learning-science-traps-to-avoid)
8. [Summary: What We're Building and Why](#summary-what-were-building-and-why)

---

## 1. The 80/20 Principle in Learning

### What It Is

The Pareto Principle, named after Italian economist Vilfredo Pareto, observes that in
most systems, roughly 80% of outcomes come from 20% of inputs. Pareto noticed this in
land ownership (20% of people owned 80% of land), and it turns out to be fractal — it
shows up in business, software bugs, wealth distribution, and critically for us: learning.

In learning, the principle means this: within any body of knowledge, roughly 20% of the
concepts are responsible for 80% of your understanding, your test performance, and your
ability to apply the material. The other 80% of content is either supporting detail,
elaboration, edge cases, or context — useful, but not the engine of understanding.

This is not just a theory. It is the organizing principle behind every high-stakes exam
prep system that works. USMLE Step 1 — the first licensing exam for US medical students
— has been reverse-engineered over decades by companies like First Aid, Sketchy, and
Boards and Beyond. Their entire business model is identifying the 20% of medical science
that appears on 80% of questions. Students who study from those resources outperform
students who read full textbooks, not because they know more, but because they know the
right things deeply.

### Why 80/20 Matters More in Medicine

Medicine is one of the most information-dense fields that exists. A first-year medical
student is expected to learn, in two years, what took physicians of a previous generation
an entire career to accumulate. The raw volume is impossible to learn exhaustively.

The students who succeed — who pass USMLE, who perform well clinically — are not the
ones who memorized the most. They are the ones who built the most accurate mental models
of how the body works, and then hung details onto those models as needed. The mental
model is the 20%. The details are the 80%.

Concretely: understanding that the kidney regulates blood pressure through the
renin-angiotensin-aldosterone system (RAAS) is a foundational model — the 20%. Knowing
that ramipril is an ACE inhibitor used in heart failure is a detail that only makes sense
if you have the model. The model lets you reason. The detail alone is just trivia.

A student who memorizes drug names without the model will forget them in a week and be
unable to reason about a drug they've never seen. A student who owns the RAAS model can
encounter any drug in that pathway, understand what it does, predict its side effects, and
reason about contraindications — without having memorized them.

**This is why 80/20 filtering is not about discarding information. It is about identifying
the structural skeleton that makes all other information hang together and make sense.**

### What Makes Something the Critical 20%?

This is the key design question for our AI prompt. We need to give Claude a principled
way to identify what belongs in the critical 20%. Here are the criteria, ranked by
importance:

**1. Foundational / Mechanistic**
Does understanding this concept explain *why* other things are true? Mechanisms are
almost always in the 20%. The action potential mechanism explains why local anesthetics
work, why hyperkalemia causes arrhythmia, why nerve conduction velocity changes in
demyelinating disease. One concept, dozens of applications. This is maximum explanatory
power per unit of learning effort.

**2. High Connectivity**
How many other concepts in the text depend on or refer back to this one? In a dense
text, certain concepts are referenced repeatedly — they are the nodes in the knowledge
graph that everything else connects to. Identify them by asking: "If I didn't understand
this, how much else in this text would I fail to understand?"

**3. Generative Power (The Utility-First Constraint)**
This is the single most important criterion for prompt design. A concept has high
Generative Power if knowing it deeply allows you to *predict* at least five other facts
without being told them. The RAAS cascade, once understood, lets you predict: why ACE
inhibitors cause a dry cough (bradykinin accumulation), why ARBs don't (they act
downstream), why spironolactone causes hyperkalemia (blocks aldosterone), why loop
diuretics are used in heart failure (override RAAS-driven sodium retention), and why
renal artery stenosis causes hypertension (falsely activates RAAS). One mechanism.
Five predictions. That is Generative Power. This criterion must be explicit in the
AI prompt — see Section 6.

**4. Principle Over Instance**
General principles are higher yield than specific examples. "Competitive inhibition
reduces apparent Km without affecting Vmax" is a principle. "Methotrexate competitively
inhibits DHFR" is an instance. The principle lets you understand any competitive
inhibitor. The instance only tells you about one drug.

**5. Clinical/Practical Relevance (in medicine)**
In medical contexts, concepts that directly explain patient presentations, diagnoses,
treatment decisions, or clinical reasoning are elevated in priority. Pathophysiology
(how does this disease process work?) is almost always higher yield than pure biochemistry
(what is the exact enzyme pathway?).

**6. Exam/Assessment Frequency**
This is pragmatic but important: some concepts are tested far more often than others.
In MCAT and USMLE, certain topics are reliably high-frequency. Our AI analysis should
weight these appropriately.

**The logic in plain English:**
> A concept belongs in the critical 20% if understanding it deeply allows a thoughtful
> person to reason their way to understanding many of the other concepts in the text,
> AND to predict real-world outcomes they haven't been explicitly taught.

### The Content Length Trap: 80/20 Is a Ratio, Not a Number

A critical mistake — even for experienced educators — is asking for a "top 5" or
"top 10" list of concepts. 80/20 is a ratio, not a fixed count.

- For a 5-minute YouTube video on a narrow topic, the 20% might be **one single mental
  model**. Forcing ten concepts would pad with noise.
- For a dense textbook chapter on cardiac physiology, the 20% might be **twelve to
  fifteen concepts**. Capping at five would leave dangerous gaps.

**The fix in our prompt:** Instead of specifying a number, give the AI a "mental budget"
instruction:

> "You have a mental budget. Every concept you include costs points proportional to its
> complexity. Only include a concept if its Generative Power — the number of other facts
> it lets you predict — justifies its cost. There is no fixed list length."

This forces the AI to make a genuine cost-benefit judgment rather than defaulting to an
arbitrary count. The number of critical_concepts in the JSON output will naturally scale
with the density of the source material. See the updated prompt in Section 6.

### Generalizable 80/20 Heuristics Across Domains

One of the most important insights for making ATLAS work beyond medicine is that "high
yield" means something different depending on the type of knowledge being filtered. AI
models often pick the most *complex* or most *central to the text* concept as the 20%,
which is wrong — complexity and yield are not the same thing.

The fix is to give the AI domain-specific heuristics. The following table defines what
"the 20%" looks like in each major knowledge domain:

| Domain Type | What the "20%" Looks Like | Examples |
|-------------|--------------------------|----------|
| **System-Based** (Medicine, Economics, Biology) | Feedback loops and regulators. The single variable that, when changed, shifts the whole system. | RAAS (Medicine), Interest Rates and inflation (Economics), Homeostasis and negative feedback (Biology) |
| **Skill-Based** (Coding, Cooking, 3D Printing) | The "Fail-Safe" principles. Things that, if ignored, cause the entire project to fail — not just produce suboptimal results, but produce nothing usable. | State management and data flow (Coding), Bed leveling and first-layer adhesion (3D Printing), Temperature control and the Maillard reaction (Cooking) |
| **Argument-Based** (History, Philosophy, Law) | The "load-bearing premise." The one idea that, if proven wrong or removed, causes the entire argument to collapse. | The Social Contract as a prerequisite for legitimate government (Philosophy), Precedent and stare decisis (Law), Counterfactual cause-and-effect (History) |
| **Procedural** (Mathematics, Engineering, Chemistry) | The principle that determines when to use which tool. Not "how to do X" but "how to know when X is needed." | When to use integration by parts vs. substitution (Math), When a reaction requires a catalyst vs. will proceed spontaneously (Chemistry) |

These heuristics must be injected into the AI prompt dynamically, based on the domain
detected during the pre-flight step (see Section 5 and Section 6). This prevents the AI
from applying medical-style mechanism-hunting to a philosophy text where what matters
is identifying the load-bearing premise.

### Shadow Exams for Non-Academic Content

Every piece of content — even a YouTube video about a hobby — has what we call a
**Shadow Exam**: the implicit test of whether you have truly understood and can apply
the material to a novel situation you haven't seen before.

Examples:
- **Economics video**: The shadow exam is being able to predict, in real time, how a
  market will react to a news event. Not recall a textbook answer — *predict*.
- **3D Printing tutorial**: The shadow exam is successfully printing a complex geometry
  with overhangs on your specific machine without a failure, adapting the settings when
  something goes wrong.
- **History lecture**: The shadow exam is being able to argue a historical counterfactual
  — "what if the assassination had failed?" — using the causal mechanisms you learned.
- **Philosophy text**: The shadow exam is being able to defend or attack the central
  thesis using premises from the text, against a skeptical opponent.

The shadow exam matters for 80/20 filtering because it defines what "applying the
knowledge" actually means in each domain. It is the filter that separates conceptual
fluff from actionable understanding.

**This principle gets injected into the prompt:** "Assume the user will be tested on
their ability to apply this knowledge to a novel, real-world problem they have never
seen. The shadow exam for this content is: [detected from pre-flight step]. Filter
for the concepts required to perform well on that application." See Section 6.

### The Mechanism-Terminology Split

There is an important trap in medicine (and many technical fields) that pure 80/20
filtering misses: understanding the mechanism does not automatically mean you can
communicate it.

You can own the complete RAAS model — understand every step of the cascade, every drug
interaction, every pathological consequence — and still be unable to answer the question
"what is furosemide?" if you have never encountered the word. The name is not derivable
from the mechanism.

This is not a failure of the 80/20 principle. It is a recognition that there are **two
distinct types of 20%**:

1. **The Mechanism Layer**: The 20% that builds understanding and enables reasoning.
   This is what the standard 80/20 filter produces.

2. **The Lexicon Layer**: The key terms, drug names, anatomical structures, and proper
   nouns that allow you to communicate that understanding in the domain's language.

ATLAS must surface both. In the JSON schema, this means adding a `key_terms` field
alongside `critical_concepts`. In the HTML, it means including a Terminology section
that lists key vocabulary with brief, mechanism-anchored definitions.

*Cross-reference: the `key_terms` field is added to the output schema in Section 6.*

### Holistic Understanding vs. Rote Memorization

The goal of 80/20 filtering is not to produce a shorter list to memorize. It is to
identify the conceptual scaffold that allows the remaining 80% to be *understood* rather
than memorized.

When you understand the critical 20% deeply, the 80% becomes predictable. You can derive
it, recall it in context, or quickly relearn it when needed. This is the difference
between a student who freezes on a novel MCAT question and one who reasons through it
step by step.

ATLAS must never produce notes that are just a shorter memorization list. The notes must
surface *why* each critical concept matters and *what it explains*, so the learner builds
a model, not a list.

---

## 2. Cornell Note Structure

### Origin and Purpose

The Cornell method was developed by Walter Pauk at Cornell University in the 1950s and
published in "How to Study in College" — one of the most evidence-based study skill
resources ever written. It remains widely used in medical education because it encodes
the learning science of spaced retrieval practice directly into the physical layout of
the page.

The key insight: most note-taking is passive. You write things down and never look at
them again in a way that forces recall. Cornell notes force retrieval by design — the
layout makes it physically easy to cover one section and quiz yourself from another.

### The Three Sections

**Main Notes Column (right side, ~65% of page width)**

This is where detailed information lives. In traditional use, you write here during a
lecture. In ATLAS, this is where the full explanation of each concept goes — the "what
and why" in enough detail to actually understand the topic.

Good main notes for ATLAS should:
- Explain the concept in clear, complete sentences (not just bullet fragments)
- Include the mechanism or reasoning, not just the conclusion
- Connect the concept to its neighbors where relevant (see: Concept Connections below)
- Be detailed enough to understand without the original text

**Cue Column (left side, ~35% of page width)**

This is the column that makes Cornell notes a study tool rather than just organized
notes. The cue column contains questions that, when covered, force you to recall the
content of the main notes column. It is written *after* the main notes.

In ATLAS, the cue column serves a dual purpose:
1. It surfaces the question that each note is "answering" — making the structure of
   knowledge explicit
2. It is the primary study interface: cover the right column, read the left, try to
   recall

Good cue questions for ATLAS should:
- Be answerable by the content of the corresponding main note
- Be phrased as questions, not keywords (questions drive active recall more effectively)
- Include at least one **Comparison Cue** per concept — a question of the form "How does
  X differ from Y?" or "Under what conditions would X fail?" These are more cognitively
  demanding than simple recall questions and produce stronger long-term retention
- Be clear enough to make sense days later without context

*Cross-reference: The AI prompt instructions for generating Comparison Cues are in
Section 6.*

**Summary Section (bottom, ~20% of page height)**

This is the 20% of the 20% — a 2-4 sentence synthesis of the most important takeaways
from the entire page. Not a list. A coherent paragraph in the learner's conceptual terms.

The summary serves two purposes:
1. It forces synthesis — you can't write a good summary without actually understanding
   the material
2. It is the fastest possible review — when you return to these notes a week later, the
   summary tells you instantly what's most important

**Critical design decision — Scaffolding and Fading:** The summary must be hidden by
default in the HTML output. If a student reads the summary first, they skip the mental
work of synthesis and receive the conclusion without earning it. The cognitive science
term for this is *scaffolding and fading*: provide support (the summary exists), but
only after the student has done the generative work. In the HTML, the summary section
is blurred or hidden behind a "Reveal Summary" button labeled: *"Only reveal after you
have reviewed all cues."*

*Cross-reference: HTML implementation of the hidden summary is in Section 4.*

### How 80/20 Maps to Cornell Structure

The mapping is direct:

| Cornell Section | 80/20 Role |
|-----------------|------------|
| Cue Column | The critical 20%: questions that unlock understanding |
| Main Notes | The full explanation: foundational 20% + supporting 80% |
| Terminology Section | The Lexicon Layer: key terms the mechanism doesn't generate |
| Summary | The 20% of the 20%: the irreducible core (hidden until earned) |

In practice for ATLAS:
- The **critical concepts** from the 80/20 filter become cue/note pairs in the main body
- The **supporting details** are grouped under their parent concept, collapsed by default
- The **summary** is generated separately as the synthesis of critical concepts only,
  hidden until the student has reviewed all cues
- The **gap analysis** surfaces what was filtered out, with a risk assessment
- The **terminology section** surfaces key vocabulary that can't be derived from the
  mechanism alone

This layout means a learner can study at three levels of depth:
1. Summary only (2 minutes: highest-level review — only after first pass)
2. Cue column + collapsed notes (10 minutes: active recall practice)
3. Full expanded notes with supporting details (30+ minutes: deep study)

### The Problem of Atomization: Chunking and Concept Connections

Beginners see 10 separate facts. Experts see 1 system. This difference — called
**chunking** in cognitive science — is one of the most important aspects of expertise.
When a cardiologist looks at an EKG, they don't see 12 individual waveform measurements;
they see a pattern that tells a story about what the heart is doing. The 12 measurements
are still there, but they are stored and recalled as one coherent unit.

The danger of well-formatted notes is that they can produce the opposite of chunking:
**atomization**. Each concept becomes a discrete, isolated card. The learner memorizes
all of them individually but never builds the interconnected model that experts use.

The fix: every critical concept in the JSON output must include a `relates_to` field
listing the other concepts it connects to. In the HTML, these connections are visualized
with SVG lines or arrows linking concept cards. The learner can see at a glance that
RAAS connects to hypertension, which connects to left ventricular hypertrophy, which
connects to heart failure — a chain of causation, not a collection of facts.

*Cross-reference: `relates_to` is added to the JSON schema in Section 6. SVG connection
visualization is described in Section 4.*

---

## 3. The Gap Filler

### The Problem

The 80/20 filter is aggressive by design. That means meaningful content gets filtered
out. Some of that content truly is filler — elaboration, anecdote, redundancy. But some
of it is:

- **Supporting details** that are necessary to understand a critical concept properly
- **Important exceptions** that the critical concept alone would cause you to get wrong
  (in medicine: "always true except in X condition")
- **Niche but high-stakes content**: rare presentations that are life-threatening if
  missed
- **Context** that doesn't fit the 80/20 hierarchy but matters for application
- **Intersystem links**: connections between topics that the text treats as separate
  but that are causally linked

The gap filler addresses this by asking: after filtering, what important content was
left behind?

### Categories of Omitted Content

**Category 1: Necessary Supporting Detail**
The critical concept is correct but incomplete without this. Example: "the action
potential requires sodium influx" is the critical concept. "The threshold for sodium
channel activation is approximately -55mV" is a supporting detail that becomes necessary
when you're asked why subthreshold stimuli don't produce action potentials.

*ATLAS treatment*: Include as a collapsed section under the parent concept. Visible on
click.

**Category 2: Important Exception or Nuance**
The critical concept states a rule; the omitted content is an important exception.
Example: "beta blockers reduce heart rate" is the rule. "Beta blockers are contraindicated
in acute decompensated heart failure" is a critical exception that pure mechanism
understanding doesn't surface.

*ATLAS treatment*: Flag explicitly with a "Watch Out" label and amber styling. These are
the highest priority gap items because missing them in a clinical context is dangerous.

**Category 3: Truly Low-Yield**
Redundant elaboration, historical context, specific numbers you'd look up anyway,
trivia. This content genuinely was not useful to filter in.

*ATLAS treatment*: Omit entirely. Note its category in the gap analysis so the learner
knows it was assessed and consciously excluded — not overlooked.

### Handling Non-Linear Content: Intersystem Links

Medical texts — and many scientific texts — do not follow a clean linear flow. A chapter
on renal physiology will jump between tubular anatomy, the RAAS cascade, diuretic
pharmacology, and the clinical presentation of hypertension. Each section is internally
coherent, but the *connections between sections* are where the deepest understanding
lives.

These connections are called **Intersystem Links**: concepts from one system that
causally affect another system. They are almost never made explicit in the text — they
are assumed knowledge. But for a learner, they are invisible and critical.

Examples of intersystem links that would be missed by naive 80/20 filtering:
- How RAAS-driven sodium retention causes pulmonary edema (kidney → lung)
- How chronic hypoxia causes polycythemia (lung → bone marrow)
- How hyperglycemia causes osmotic diuresis (endocrine → kidney)

The gap analysis prompt must explicitly instruct the AI to look for these links:
"Identify any 'Intersystem Links' — places where a concept in one body system or domain
causally affects a concept in another. These connections are rarely made explicit in
source texts but are high-yield for clinical reasoning."

*Cross-reference: The gap_analysis prompt instruction is updated in Section 6.*

### How the Gap Analysis Works in Practice

After the AI produces the structured 80/20 analysis, the gap analysis component does
this:

1. The AI identifies what was filtered out and categorizes it
2. For each omitted item, it assesses: supporting detail, important nuance,
   intersystem link, or truly low-yield?
3. Supporting details get attached to their parent critical concept as hidden expandable
   sections in the HTML
4. Important nuances and intersystem links get flagged in a "Watch Out" section with
   amber styling
5. Truly low-yield content is documented with a brief note explaining why it was cut
6. The learner sees a transparent summary of what was removed and can decide whether
   to dig in

The gap analysis is how ATLAS ensures that aggressive 80/20 filtering doesn't produce
dangerously incomplete notes. It makes the filtering *auditable* — the learner knows
what was removed and why.

---

## 4. The HTML Output

### What Makes It Interactive

The interactivity in our Cornell notes output serves one pedagogical purpose: enabling
active recall practice and *desirable difficulty* without needing a separate tool. The
learner opens the file, tests themselves from the cue column, and the file resists
giving them the answer too easily — because that difficulty is what drives learning.

There are five interactive behaviors we need:

**1. Hide/Reveal Main Notes (Core Study Mechanism)**

A click event on the notes section toggles its visibility. This is the digital
equivalent of covering the right side of a Cornell notes page with your hand.

How it works in code:
- Each main note section is wrapped in a `<div>` with a specific CSS class
- A JavaScript function toggles a CSS class that sets `display: none` / `display: block`
- A "Hide All Notes" button at the top collapses all notes for a full practice run
- Individual notes can also be clicked to reveal one at a time

**2. Force Draft Mode (Combating the Fluency Illusion)**

This is a more advanced interactive layer that addresses one of the biggest learning
traps: the Fluency Illusion. When notes are beautifully formatted and easy to read, the
brain generates a false feeling of mastery — "I understand this because I can read it
clearly." This is not learning. This is recognition, which is cognitively cheap and
forgettable.

The fix: before the main note is allowed to be revealed, a small text input appears
below the cue question with the label: *"Write your answer in one sentence before
revealing."* The user types anything (there is no grading at this stage — that comes
in Phase 3's Feynman scoring) and then clicks "Reveal." The act of attempting to
generate an answer before seeing it is called *retrieval practice* and is one of the
most robustly supported learning interventions in cognitive science.

How it works in code:
- A `<textarea>` element sits hidden below each cue question
- Clicking "Attempt Answer" reveals the textarea and hides the "Reveal" button
- Only after the textarea has at least one character does the "Reveal" button reappear
- This creates a soft gate — the learner *can* skip it (just type a space), but the
  friction of the gate is enough to change behavior

*Cross-reference: This directly counters the Fluency Illusion described in Section 7.*

**3. Expand/Collapse Supporting Details**

Supporting details (the "gap filler" content attached to parent concepts) are hidden by
default to keep the view clean. A "Show Details" button per concept expands them.

How it works in code:
- HTML `<details>` and `<summary>` elements handle this natively in browsers with zero
  JavaScript needed
- `<details>` is a browser-native collapsible container; `<summary>` is the always-
  visible label you click
- This is simpler and more accessible than writing custom JS toggle logic

**4. Progress Tracking**

As the learner goes through concepts and reveals them, a counter shows "X of Y reviewed."
This makes studying feel like progress with a visible endpoint.

How it works in code:
- A JavaScript counter increments each time a note is revealed
- Updates a `<span>` element at the top of the page
- When all notes are revealed, the "Reveal Summary" button becomes active

**5. Scaffolded Summary Reveal**

The summary is blurred or hidden behind a "Reveal Summary" button that only becomes
active after all notes have been reviewed. The button label reads: *"Reveal Summary
(review all cues first)."* This prevents the student from reading the conclusion before
doing the synthesis work. See Section 2 for the pedagogical rationale.

### Cognitive Load and Diagram Placement

Cognitive Load Theory, developed by John Sweller, describes the limits of working
memory. A critical sub-finding — the **Split-Attention Effect** — is directly relevant
to our diagram design.

The Split-Attention Effect: when a learner has to look at a diagram and then scroll
or navigate to find the text explaining it, their working memory must hold the diagram
in mind while reading the text. The cognitive cost of this mental bridging reduces the
resources available for actually understanding the content. Studies show this
significantly degrades learning compared to *integrated instructions*, where diagram
and explanation occupy the same visual space.

**The fix:** in our HTML, diagram placeholders are never placed in a separate section.
They are generated *inside* the main note for the concept they illustrate, immediately
adjacent to or wrapping the explanatory text. The eye should not have to travel. The
reader should be able to look at the diagram and read the explanation without any
spatial separation.

Concretely, the HTML structure for a concept with a diagram looks like this:

```
[Cue Column]          [Main Note Column]
                      ┌──────────────────────────────┐
How does RAAS         │ DIAGRAM: RAAS Cascade        │
regulate blood        │ Draw: Low BP → Renin →       │
pressure?             │ Angiotensin I → ACE →        │
                      │ Angiotensin II → Aldosterone  │
                      │ → Na+ retention → BP rises   │
                      └──────────────────────────────┘
                      The kidney detects low blood
                      pressure via reduced stretch in
                      the juxtaglomerular cells, which
                      release renin into the bloodstream.
                      Renin cleaves angiotensinogen...
```

The diagram and the explanation are adjacent — not separated by a scroll.

*Cross-reference: The Cognitive Load trap is summarized in Section 7.*

### Concept Connection Map

To counter atomization (Section 2), the HTML includes a visual concept map at the top
of the notes page. This is a small SVG diagram that shows each critical concept as a
labeled node, with lines connecting nodes that are linked via the `relates_to` field in
the JSON.

It is intentionally minimal — not a complex force-directed graph, just a static
arrangement of boxes and lines drawn with SVG tags that are embedded directly in the
HTML. The learner can see at a glance which concepts are isolated facts vs. which are
densely connected hubs in the knowledge graph. The hubs are the most important to
understand deeply.

### Spaced Repetition: Next Review Date

Forgetting is not a failure. It is the default state of human memory. The forgetting
curve, described by Hermann Ebbinghaus in 1885, shows that memory of new information
drops to ~40% within 24 hours if not reviewed, and continues declining exponentially
without spaced repetition.

Our HTML notes are self-contained files, which is great for durability but creates a
"dead artifact" problem: once created and studied, the file sits in a folder and is
never revisited. The learner loses most of what they studied within a week.

**The fix:** a small JavaScript block at the top of each HTML file reads the file's
creation metadata (or a date embedded in the HTML during generation) and displays a
"Next Review" prompt:

```
Created: 2025-08-14
Next review: 2025-08-15 (Tomorrow — first consolidation)
After that:  2025-08-18 (3 days — second consolidation)
Then:        2025-08-25 (7 days — long-term retention check)
```

This is not a scheduling system. It is a nudge — a visible reminder at the top of the
file that tells the learner exactly when they should reopen it to retain what they
studied. The dates are calculated using the Leitner-style spaced repetition intervals
(+1, +3, +7, +14 days) and embedded as plain text in the HTML at generation time.

*Cross-reference: The Forgetting Curve trap is detailed in Section 7.*

### The "Durable File" vs. "Dead File" Problem: User Reflections

A self-contained HTML file has a hidden flaw: it cannot be updated after it is generated.
The learner has insights, makes connections, and has "Aha!" moments while studying — and
has no way to capture them in the same artifact they are studying from.

**The fix:** a `contenteditable` `<div>` at the bottom of the HTML file, labeled
*"Your Notes & Reflections."* This is a browser-native feature that allows any `<div>`
to be typed into directly in the browser without any JavaScript or server needed. The
learner can type their own insights, connections, and corrections directly into the
rendered HTML.

Because it doesn't persist automatically (the browser doesn't save edits to files on
disk), we add a clear note: *"Use Ctrl+P / Cmd+P to 'Print to PDF' to save your
combined AI + personal notes as a single document."* This transforms the HTML from a
read-only artifact into a canvas that the learner can mark up and save as a PDF.

*Cross-reference: This addresses the Durable vs. Dead File trap in Section 7.*

### Diagram Placeholders

Our Python pipeline cannot generate actual diagrams. But diagrams are critical for
certain concepts (anatomy, pathways, mechanisms, graphs). Rather than omitting them, we
create structured placeholder boxes placed *inside* the relevant note — not in a
separate section (see Cognitive Load above).

A diagram placeholder is a styled `<div>` that:
- Is visually distinct from note content (dashed border, light background)
- Contains: a title, a description of what the diagram should show, and a prompt to
  draw it by hand
- Is placed immediately above the explanatory text for that concept
- Optionally includes a text-based approximation (ASCII art or a simple flow) for
  concepts that can be partially represented in text

Example placeholder for RAAS:
```
┌─────────────────────────────────────────────────────────┐
│  DIAGRAM: RAAS Cascade                                  │
│  Draw this: A vertical flow chart showing:             │
│  Low BP → Renin (kidney) → Angiotensinogen →           │
│  Angiotensin I → ACE (lung) → Angiotensin II →         │
│  Aldosterone (adrenal) → Na+ retention → BP rises      │
│  Include: where ACE inhibitors and ARBs block the path │
└─────────────────────────────────────────────────────────┘
```

The AI flags which concepts need diagrams and provides the illustrator-brief description.

### Single Self-Contained File

This is a hard constraint from the architecture: every HTML output must work offline,
on any computer, forever, with no dependencies.

**What this means technically:**
- All CSS lives in `<style>` tags inside the `<head>` section
- All JavaScript lives in `<script>` tags at the bottom of `<body>`
- No `<link rel="stylesheet">` tags pointing to external files
- No `<script src="...">` tags loading from CDNs
- No Google Fonts, no Bootstrap, no jQuery
- Font stack uses only system fonts: Georgia, Arial, system-ui, monospace

**Why this matters:**
- The file can be emailed, stored on a USB drive, or opened 10 years from now
- It works in airplane mode
- Nothing phones home (privacy)
- Open it in a text editor and you can read every line that makes it work

**What the file structure looks like:**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Cornell Notes: [Topic]</title>
  <style>
    /* All CSS here — layout, colors, typography, interactive states */
  </style>
</head>
<body>
  <!-- Concept map SVG -->
  <!-- Spaced repetition dates -->
  <!-- Cornell layout: cue + notes columns -->
  <!-- Terminology section -->
  <!-- Gap analysis section -->
  <!-- User reflections contenteditable div -->

  <script>
    // All JavaScript here — toggle, Force Draft gate, progress counter
  </script>
</body>
</html>
```

### Visual Design Principles

- **Two-column layout**: CSS Grid, ~35% left (cue) and ~65% right (notes)
- **Visual hierarchy**: topic title → concept map → section headers → individual concepts
- **Color coding**: critical concepts in blue, supporting details in gray,
  Watch Out exceptions in amber, key terms in green
- **Print-ready**: `@media print` CSS block so notes can be printed or PDF'd
- **Typography**: Georgia serif for readability in long-form notes, monospace for terms
- **Diagram placement**: always integrated within the note, never in a separate section

---

## 5. The Python Pipeline

### Core Principle

Each function does exactly one thing. A function that reads a file does not also call
an API. A function that calls an API does not also parse the response. A function that
parses a response does not also write a file. This makes each function testable,
readable, and debuggable in isolation.

### The Sequence

The pipeline now has a two-step AI call: a lightweight **pre-flight** call to detect the
domain, and the main **analysis** call that uses that domain context.

```
input.txt
    │
    ▼
load_text(file_path)
    │  reads the .txt file, returns a string
    ▼
detect_field(raw_text)
    │  pre-flight: asks Claude to identify the domain, sub-domain,
    │  shadow exam, and appropriate 80/20 heuristic type
    │  returns a small dict: {field, sub_domain, shadow_exam, heuristic_type}
    ▼
build_prompt(raw_text, field_context)
    │  wraps the text in the full analysis prompt,
    │  injecting the field_context from pre-flight
    ▼
call_claude(prompt)
    │  sends the prompt to Claude API, returns the raw response string
    ▼
parse_response(response_string)
    │  extracts and validates the JSON, returns a Python dict
    ▼
save_session_json(notes_dict, session_dir)
    │  saves the structured data as cornell.json
    ▼
build_html(notes_dict)
    │  assembles the complete HTML: CSS, concept map SVG, Cornell layout,
    │  terminology section, gap analysis, spaced repetition dates,
    │  reflections div, and JavaScript
    ▼
save_html(html_string, session_dir)
    │  writes cornell.html to disk
    ▼
main(input_path)
    orchestrates all of the above in order
```

### What Each Function Does

**`load_text(file_path)`**
Opens the file at `file_path`, reads its contents, returns it as a single Python string.
Tells the user in plain English if the file doesn't exist, rather than crashing.

**`detect_field(raw_text)`**
The pre-flight step. Sends a short, cheap prompt to Claude asking it to identify:
- The academic or professional field (e.g., "Cardiovascular Physiology")
- The specific sub-domain (e.g., "Renin-Angiotensin System")
- The shadow exam (e.g., "Apply RAAS knowledge to explain a patient's hypertension and
  choose the correct antihypertensive class")
- The heuristic type from our domain table (e.g., "System-Based: Feedback Loops")

This takes one short API call and returns a small JSON object. The result is injected
into `build_prompt()` so the main analysis uses a calibrated, domain-specific lens.

*Why not just do this in one call?* Because a single long prompt with all the domain
logic baked in would force Claude to figure out the domain mid-analysis, and the domain
detection quality drops when it's competing with the extraction task. Separating them
produces better results.

**`build_prompt(raw_text, field_context)`**
Takes the raw text and the field_context dict from `detect_field()`. Assembles the full
analysis prompt by injecting the domain, sub-domain, shadow exam, and appropriate
80/20 heuristic type into the prompt template. Returns the complete prompt string.

**`call_claude(prompt)`**
Makes the API request. Sends the prompt, receives the response text. Has *only* this
responsibility — no parsing, no validation.

**`parse_response(response_string)`**
Extracts the JSON from Claude's response (strips markdown fences if present), calls
`json.loads()`, validates required fields exist. Explains any errors in plain English.

**`save_session_json(notes_dict, session_dir)`**
Writes the Python dict to `cornell.json` using `json.dumps(indent=2)` for readability.

**`build_html(notes_dict)`**
The most complex function. Assembles the complete HTML string from the notes dict:
1. CSS block (layout, colors, responsive, print styles)
2. Concept map SVG (nodes and connections from `relates_to` fields)
3. Spaced repetition date display
4. Cornell two-column layout (iterating over critical_concepts and supporting_details)
5. Diagram placeholders (placed inside notes, not separately)
6. Terminology / key terms section
7. Gap analysis section (Watch Out items flagged)
8. User reflections `contenteditable` div
9. JavaScript block (hide/reveal, Force Draft gate, progress counter, summary gate)

**`save_html(html_string, session_dir)`**
Writes the HTML string to `cornell.html`. Nothing more.

**`main(input_path)`**
The entry point. Creates the session folder, calls each function in sequence, prints
a success message with the path to the output file.

### Folder Creation Logic

Every run creates a new session folder named `[topic]-[date]` inside `/data/sessions/`.
The topic name comes from the AI analysis. The date is in YYYY-MM-DD format. If a
folder with that name already exists, append `-2`, `-3`, etc. rather than overwriting.

---

## 6. What the AI Call Looks Like

### Why Claude for This Task

The 80/20 analysis requires semantic understanding — grasping what is foundational vs.
elaborative, what mechanisms explain what, and what is high-yield in a given domain.
Rule-based algorithms cannot do this. Claude is well-suited specifically because:
- Deep training on medical, scientific, educational, and technical content
- Can assess "Generative Power" — how much does understanding this unlock?
- Produces well-structured JSON reliably when explicitly instructed
- Makes pedagogical judgments (diagram needed, dangerous exception, intersystem link)

### The Expert Blindness Problem

Without a domain and expertise anchor, AI models make a systematic error: they confuse
*complexity* with *importance*. The most complex concept in a text is not the 20% — it
is often obscure detail. The 20% is frequently the most *foundational* concept, which
may be stated simply and early in the text, and then built upon throughout.

This is **Expert Blindness**: the AI has read so much about every topic that it no
longer perceives what a learner at a specific level actually needs. It thinks everything
is important. Or it picks the most impressive-sounding concepts.

The fix is a **Persona Constraint**: anchor the AI to a specific role, level of
expertise, and goal. But a static persona like "medical student" fails for non-medical
content. We need a dynamic approach.

### The Recursive Expert Prompting Technique

Instead of choosing the persona manually, the pipeline asks the AI to identify the
optimal persona first. This is the job of the `detect_field()` function.

**Pre-flight prompt:**
```
Analyze the following text and return ONLY valid JSON with these fields:

{
  "field": "the academic or professional field (e.g., Cardiovascular Physiology)",
  "sub_domain": "the specific sub-topic (e.g., Renin-Angiotensin-Aldosterone System)",
  "shadow_exam": "one sentence describing the real-world or exam application that would
                  test whether someone has truly understood this content",
  "heuristic_type": "one of: System-Based, Skill-Based, Argument-Based, Procedural",
  "optimal_persona": "complete this template: 'An expert in [field] who specializes in
                      [sub_domain], mentoring a student who needs to master the 20% of
                      concepts required to [shadow_exam goal]'"
}

TEXT:
[raw text]
```

This output is then injected into the main prompt. The AI calibrates itself before
analyzing. The quality of 80/20 selection improves substantially because the filter is
anchored to a specific level, domain, and goal.

### The Bridge-the-Gap Persona Template

The persona in the main prompt uses a template that defines expertise by the
*relationship to the learner*, not just a job title. This works for any domain:

```
"You are a [Field] expert who specializes in [Specific Sub-domain].
Your goal is to mentor a student who understands the basics but needs to master the 20%
of concepts that will allow them to [Goal: the shadow exam application].
Filter ruthlessly: only include a concept if a student who lacks it would fail the
shadow exam."
```

Examples of this template in action:
- Medicine: *"...mentor a student...to correctly diagnose and manage a hypertensive
  patient presenting with acute kidney injury."*
- Economics: *"...mentor a student...to predict, in real time, how a bond market reacts
  to an unexpected Federal Reserve rate announcement."*
- 3D Printing: *"...mentor a student...to successfully print a complex overhang geometry
  on an Elegoo Saturn 4 Ultra without adhesion failure or layer separation."*

The template is domain-agnostic. It is built automatically from the pre-flight output.

### The Complete Two-Step Prompt Strategy

**Step 1 — Pre-flight (cheap, fast):**
Small prompt. Returns domain context JSON. Used to calibrate Step 2.

**Step 2 — Main Analysis (full, structured):**
```
[PERSONA BLOCK — generated from pre-flight]
You are a [optimal_persona from pre-flight].

[TASK]
Analyze the text below and extract structured Cornell notes applying strict 80/20
filtering.

[CRITICAL RULES]
- Return ONLY valid JSON. No commentary, no markdown code fences, no explanation.
- The JSON must exactly match the schema below.
- 80/20 IS A RATIO, NOT A NUMBER. Do not target a fixed count of concepts. Use your
  mental budget: only include a concept if its Generative Power (ability to let the
  student predict 5+ other facts) justifies its inclusion.
- A concept has "Generative Power" only if knowing it deeply lets the student predict
  five or more related facts without being told them explicitly.
- Prioritize [domain heuristic from pre-flight]:
    - System-Based: Feedback loops and regulators that shift the whole system
    - Skill-Based: Fail-safe principles where ignorance causes total project failure
    - Argument-Based: Load-bearing premises that, if removed, collapse the argument
    - Procedural: Meta-principles about when to apply which technique
- The shadow exam for this content is: [shadow_exam from pre-flight]. Filter for the
  concepts required to perform well on that application.
- For every critical concept, include at least one Comparison Cue — a question of the
  form 'How does X differ from Y?' or 'Under what conditions would X fail?'
- Explicitly look for Intersystem Links: places where a concept in one system or domain
  causally affects another system.
- Flag clinically or practically dangerous exceptions.
- "importance" fields must explain WHY — what Generative Power does this concept have?

[OUTPUT SCHEMA]
{
  "topic": "main subject, 5 words or fewer",
  "field_context": {
    "field": "[from pre-flight]",
    "sub_domain": "[from pre-flight]",
    "shadow_exam": "[from pre-flight]"
  },
  "summary": "2-3 sentence synthesis. Coherent paragraph, not a list.",
  "critical_concepts": [
    {
      "cue": "primary recall question for this concept",
      "comparison_cue": "How does this differ from X? OR Under what conditions would this fail?",
      "note": "full explanation — mechanism, not just conclusion",
      "importance": "Generative Power: list the 5+ facts this concept lets you predict",
      "relates_to": [list of other concept cues this connects to],
      "diagram_needed": true or false,
      "diagram_description": "if true: brief an illustrator — what to draw and label"
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
      "definition": "brief definition anchored to the mechanism (not a dictionary definition)",
      "why_memorize": "this cannot be derived from the mechanism alone — it must be explicitly learned"
    }
  ],
  "gap_analysis": {
    "content_filtered_out": "plain English description of what didn't make the cut",
    "intersystem_links_found": "any cross-system causal connections identified",
    "important_nuances_omitted": "exceptions or edge cases that carry clinical/practical risk",
    "omission_risk": "low, medium, or high — with one sentence of justification"
  }
}

TEXT TO ANALYZE:
[the raw input text]
```

### Why Each Part of the Prompt Matters

**"Return ONLY valid JSON"**
Without this, Claude wraps the JSON in markdown fences (```json ... ```) or adds a
preamble. Both break `json.loads()` in Python.

**"80/20 IS A RATIO, NOT A NUMBER"**
Without this, the AI defaults to a "top 10" list regardless of source material density.

**"Generative Power — the 5+ fact test"**
Forces the AI to make a genuine cost-benefit judgment rather than including everything
that sounds important. If it can't list five facts that flow from a concept, the concept
shouldn't be in the 20%.

**"comparison_cue" field**
Recall questions ("What is X?") test recognition. Comparison questions ("How does X
differ from Y?") test understanding. Comparison questions produce stronger long-term
retention because they force the learner to build a discriminative mental model.

**"relates_to" field**
Feeds the concept map visualization. Without this, the HTML is an atomized list. With
it, the HTML shows the knowledge graph that experts use.

**"key_terms" field**
Addresses the Mechanism-Terminology Split (Section 1). Surfaces the lexicon that
mechanism understanding alone doesn't generate.

**"intersystem_links_found" in gap_analysis**
Explicitly hunts for the cross-domain connections that are invisible in linear text but
high-yield for application.

**`parent_concept_index`**
Links supporting details to their parent for correct HTML grouping.

**`detail_type`**
Drives visual treatment in HTML: `supporting_detail` collapses quietly, `important_exception`
gets amber "Watch Out" styling, `intersystem_link` gets a distinct visual flag.

### Handling Bad Responses

**1. JSON with markdown fences**
Strip ```json and ``` with string operations before calling `json.loads()`.

**2. Missing required fields**
Check for `topic`, `summary`, `critical_concepts`, `key_terms`, `gap_analysis`. If any
are missing, tell the user in plain English and suggest adding more input text.

**3. `critical_concepts` is empty**
Flag clearly. Suggest pasting more content.

**4. API error (rate limit, network, invalid key)**
Catch the exception, tell the user what type it was and what to do next.

**5. Malformed JSON**
Save the raw response to a debug file so no information is lost. Tell the user exactly
what went wrong.

---

## 7. Learning Science Traps to Avoid

This section is a reference guide for the cognitive science pitfalls that directly
shaped our design decisions. Each trap is described, cross-referenced to the section
where it is addressed, and marked with its resolution status in ATLAS.

---

### Trap 1: The Fluency Illusion
**What it is:** When notes are beautifully formatted and easy to read, the brain tricks
itself into thinking it has "learned" the material. This is recognition masquerading as
recall. The learner can read the answer fluently but cannot produce it independently.

**Why it matters:** Every clean note-taking system is vulnerable to this. The cleaner
the notes, the worse the Fluency Illusion effect.

**ATLAS resolution:** Force Draft mode in the HTML output creates a soft retrieval gate
before each note is revealed, forcing the learner to attempt generation before recognition.
This exploits the *Testing Effect* (also called the Retrieval Practice Effect): the act
of attempting to recall — even unsuccessfully — produces stronger memory consolidation
than re-reading.

*See: Section 4 — "Force Draft Mode"*

---

### Trap 2: Cognitive Load / The Split-Attention Effect
**What it is:** Human working memory has limited capacity. When a diagram and its
explanation are placed in different locations (separate section, below the fold, in an
appendix), the learner must split attention between them, consuming working memory on
navigation rather than understanding. Learning degrades significantly.

**Why it matters:** Most note-taking tools put diagrams in a separate "media" section.
This is cognitively expensive.

**ATLAS resolution:** All diagram placeholders are placed *inside* the main note,
immediately adjacent to the explanatory text. The eye never has to travel.

*See: Section 4 — "Cognitive Load and Diagram Placement"*

---

### Trap 3: Expert Blindness in AI
**What it is:** AI models have read so much content that they lose the ability to see
what a learner at a specific level actually needs. Without an expertise anchor, they
pick complex concepts rather than foundational ones, or produce a list where everything
seems equally important.

**Why it matters:** The quality of the entire 80/20 filter depends on the AI's ability
to calibrate to the right level and purpose.

**ATLAS resolution:** Two-step Recursive Expert prompting. The pre-flight call detects
the domain and builds a Bridge-the-Gap persona. The main analysis call uses that persona
to anchor the filter to a specific level, domain, and shadow exam application.

*See: Section 6 — "The Expert Blindness Problem" and "The Recursive Expert Technique"*

---

### Trap 4: The Forgetting Curve
**What it is:** Without review, memory of new information drops to ~40% within 24 hours
and continues declining. A note studied once and never revisited might as well not have
been studied.

**Why it matters:** A self-contained HTML file that is never reopened is a perfectly
durable artifact that does absolutely nothing for long-term retention.

**ATLAS resolution:** Spaced repetition review dates are calculated at generation time
(+1, +3, +7, +14 days) and displayed at the top of every HTML file as a visible nudge.

*See: Section 4 — "Spaced Repetition: Next Review Date"*

---

### Trap 5: Over-Reliance on Mechanisms / The Mechanism-Terminology Split
**What it is:** Understanding a mechanism deeply does not guarantee you can name the
things in that mechanism. You can understand the entire RAAS cascade and still not know
the word "furosemide."

**Why it matters:** In medicine and other technical fields, communication requires
vocabulary. You cannot function clinically if you can only describe what a drug does
without knowing what it's called.

**ATLAS resolution:** `key_terms` field added to the JSON schema. A dedicated Terminology
section in the HTML notes. Each term definition is anchored to the mechanism rather than
being a dictionary definition.

*See: Section 1 — "The Mechanism-Terminology Split" and Section 6 — JSON schema*

---

### Trap 6: Atomization
**What it is:** Breaking notes into isolated facts destroys the chunked, interconnected
mental model that experts use. The learner memorizes 10 facts but never sees the 1 system
those facts describe.

**Why it matters:** Expert performance in medicine, engineering, and other fields depends
on chunked knowledge retrieval — seeing a pattern as a single unit, not a list of parts.

**ATLAS resolution:** `relates_to` field in the JSON schema. Concept connection map SVG
at the top of each HTML file. The visual graph shows which concepts are isolated vs.
densely connected — and the densely connected ones are where the learner should focus.

*See: Section 2 — "The Problem of Atomization" and Section 4 — "Concept Connection Map"*

---

### Trap 7: Scaffolding Without Fading (The Pre-Read Summary Trap)
**What it is:** Providing the summary before the student has reviewed the notes removes
the cognitive effort of synthesis. The student reads the conclusion, feels oriented, and
stops engaging. They skip the mental work that produces retention.

**Why it matters:** The summary is only valuable if the student *earns* it through prior
retrieval effort. Read first, it becomes a spoiler.

**ATLAS resolution:** Summary section is hidden (blurred) by default. The "Reveal
Summary" button only becomes active after all cue questions have been attempted. Labeled:
*"Review all cues before revealing."*

*See: Section 2 — "Scaffolding and Fading" and Section 4 — "Scaffolded Summary Reveal"*

---

### Trap 8: Non-Linear Content / Missing Intersystem Links
**What it is:** Medical and scientific texts jump between systems without explicitly
stating the connections. A chapter on kidneys mentions blood pressure. A chapter on
the heart mentions fluid balance. The causal link (kidney dysfunction causes heart
failure) is implicit and often missed entirely by linear note-taking.

**Why it matters:** Clinical reasoning is almost entirely about intersystem causation.
A learner who only understands each system in isolation cannot reason about a patient
whose problems cross multiple systems — which is almost every real patient.

**ATLAS resolution:** Explicit `intersystem_links_found` field in gap_analysis prompt.
Supporting details with `detail_type: intersystem_link` get distinct visual treatment.
The pre-flight prompt detects the domain to determine which intersystems are relevant.

*See: Section 3 — "Handling Non-Linear Content"*

---

### Trap 9: Weak Cue Questions / Lack of Metacognitive Prompts
**What it is:** Simple recall cues ("What is X?") produce shallow retrieval. They test
whether the learner has memorized the answer, not whether they understand it well enough
to apply or discriminate it.

**Why it matters:** MCAT and USMLE questions almost never ask "What is X?" They ask
"How does X differ from Y in the context of Z?" or "Why would treatment A fail in this
patient?" Simple recall cues do not prepare students for this.

**ATLAS resolution:** Every critical concept in the JSON schema requires a `comparison_cue`
field alongside the primary cue. Comparison cues follow templates: "How does X differ
from Y?" or "Under what conditions would X fail?" These force discriminative reasoning,
not recognition.

*See: Section 2 — "The Three Sections (Cue Column)" and Section 6 — JSON schema*

---

### Trap 10: The Durable File vs. Dead File Problem
**What it is:** A perfectly formatted, self-contained HTML file is a read-only artifact.
As a student studies it, they have insights, make connections, and notice gaps — but
have no way to capture those thoughts in the same document. The human layer of
understanding never gets recorded.

**Why it matters:** The most valuable notes are a combination of AI-generated structure
and human-generated insight. Without a way to add the human layer, the file remains
a template, not a personal artifact.

**ATLAS resolution:** `contenteditable` `<div>` at the bottom of every HTML file.
No JavaScript needed — it's a browser-native feature. Combined with a "Print to PDF"
prompt so the combined AI + human notes can be saved as a single durable document.

*See: Section 4 — "The Durable File vs. Dead File Problem"*

---

## Summary: What We're Building and Why

Phase 1 of ATLAS is a pipeline that takes any text and produces a single HTML file
containing Cornell notes structured by 80/20 filtering. The output is not a shorter
version of the input. It is a *restructured* version designed to build understanding,
force retrieval, and remain useful over multiple review sessions.

The complete set of design decisions, all traceable to this document:

1. **80/20 filtering is semantic and domain-calibrated**: it requires AI anchored to
   a specific level and shadow exam, not generic "expert" reasoning.

2. **The pre-flight step eliminates Expert Blindness**: domain and persona are detected
   first; the analysis uses that calibration.

3. **80/20 is a ratio, not a number**: the mental budget instruction scales concept
   count to source density.

4. **Generative Power is the selection criterion**: concepts are included based on how
   many facts they predict, not how important they sound.

5. **Cornell structure encodes active recall**: the cue/note layout is functional, not
   aesthetic. Force Draft mode deepens the retrieval requirement.

6. **Scaffolding and fading apply to the summary**: it is earned, not given upfront.

7. **Diagram placement follows Cognitive Load theory**: always integrated, never separate.

8. **Concept connections counter atomization**: `relates_to` field + SVG map build the
   expert's chunked mental model.

9. **The Lexicon Layer is separate from the Mechanism Layer**: `key_terms` captures
   what mechanism understanding can't generate.

10. **Gap analysis is non-optional and transparent**: filtering without transparency
    creates dangerous gaps. The learner sees what was removed and why.

11. **Intersystem links are explicitly hunted**: cross-system causal connections are
    the foundation of clinical reasoning and are invisible to linear filtering.

12. **Single self-contained HTML**: durable, offline, shareable, no dependencies.

13. **Spaced repetition is prompted, not automated**: review dates are embedded at
    generation time as a visible nudge.

14. **The file is a canvas, not a read-only artifact**: `contenteditable` + Print to
    PDF makes it a living document.

15. **Pipeline functions are small and single-purpose**: teachable, debuggable,
    and ready for Phases 2-4.
