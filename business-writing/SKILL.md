---
name: professional-docs
description: >
  Use this skill whenever the user asks to write, rewrite, or improve a resume,
  CV, cover letter, or professional portfolio content. Triggers include: "update
  my resume", "write a cover letter", "help me apply for a job", "rewrite my
  experience", "make my resume better", "tailor this for [company]", or any
  request involving professional self-presentation documents. Also triggers when
  the user shares a resume or cover letter for review. This skill encodes hard-won
  conventions around voice, structure, spice gradient, and the distinction between
  a resume and a cover letter — do not skip it for any professional document task.
---

# Professional Document Writing

## Core Philosophy

Three documents, three distinct jobs. Never conflate them.

| Document | Purpose | Voice | Technical Depth |
|---|---|---|---|
| Resume | Recyclable capability inventory | Action verbs, no pronouns | Tools in competencies only; bullets state outcomes |
| Cover letter | Narrative argument for fit | Prose story, no bullets | Insider language as texture, not structure |
| Portfolio / application fields | Evidence trail + product thinking | Varies by section | Full specificity permitted |

The **spice gradient** runs resume → cover letter → application fields.
What is too specific for the resume is exactly right for the cover letter.
What is too specific for the cover letter belongs in the application field.

---

## Resume

### Voice
- No pronouns. No "I", no "he/she/they".
- Every bullet leads with what was done, not who did it.
- No temporal or subjective adjectives: not "optimized", "enhanced", "improved" as standalone claims. Say what changed and by how much.

### Structure (top to bottom)
1. **Header** — Name with degree suffix (M.S. not MSc — US notation), location, email, portfolio URL, GitHub
2. **Summary** — 2–3 sentences. Career span, domain specialization, one differentiating trait. No fluff.
3. **Core Competencies** — This is where tool and algorithm names live. Organized by category (ML/AI, Frameworks, Data/Infra, Languages, Cloud/DevOps). Bullet-free; pipe or dot separated.
4. **Professional Experience** — Triplet bullets (see below). Reverse chronological.
5. **Projects & Accomplishments** — Same triplet format. Personal projects go here.
6. **Education** — Bottom. For 10+ years experience, education is not the hook. Front-load it only via the degree suffix in the name.

### Triplet Bullet Format

Every experience bullet follows:

```
[Enabling Capacity] → [What Was Done] → [Business/User Benefit]
```

Formatted as: **bold capacity** → action → *italic benefit*

**Rules:**
- Capacity = the skill or method that made this possible (generic enough to apply elsewhere)
- Action = what was actually built or changed (no algorithm names, no counts, no source names)
- Benefit = what the end user or business gained (not what the system does — what someone got)

**Wrong:** `UMAP + Ward clustering → clustered 1,751 songs using cosine similarity matrix → micro/meso/macro hierarchy`
**Right:** `Music discovery system → clustered songs into navigable genre and artist groupings → listener can explore by similarity or pivot intentionally across genres`

Algorithm names belong in Competencies. Counts and sources belong in the cover letter or application fields. The resume bullet should be reusable across similar roles without rewriting.

### Fact Discipline
- Verify all tenure dates. "12+ years" = total career, not tenure at current employer.
- Attribute metrics to the correct employer. A 15% latency improvement at Vennify is not a Boeing achievement.
- No fabricated industry categories. Only claim industries where there is actual professional experience.
- If a metric is real, it stays. If it is approximate or unverified, cut it.

### Education Notation
- Use M.S. (not MSc — that is British)
- Use M.D., Ph.D., M.B.A. — standard American period notation
- Place in name header as suffix when experience is the primary credential

---

## Cover Letter

### What It Is Not
A cover letter is not:
- An extended CV
- A bulleted list of accomplishments
- A section-headed document
- A recipe

### What It Is
A one-page prose argument for why this person, this company, this role. It has a narrative arc. Someone should want to keep reading it.

### Structure (prose, no headers, no bullets)

**Paragraph 1 — Hook**
Open in media res. Place the reader in a moment, an observation, a genuine point of curiosity. Do not open with "I am applying for..." Do not open with credentials. The hook should make the reader think: *this is different, I want to know more.*

**Paragraph 2 — The Problem You Think About**
Connect the hook to a technical or domain problem. Show that the thinking is real, ongoing, and self-directed — not activated by the job posting. This is where genuine personal projects earn their weight. The project should appear not as a credential but as evidence of a preoccupation.

**Paragraph 3 — Professional Proof**
Establish that the same thinking has been applied in production. Name specific results. Do not re-list the resume — synthesize it into a coherent claim. One or two employers, two or three concrete outcomes. End with a line that distinguishes what was built from what was merely used: "not just used, but stood up."

**Paragraph 4 — Why This Company**
Show domain-specific product thinking. Not "I admire your mission." An actual idea, insight, or observation about their problem space that only someone who has thought about it would have. This is the place for the venue idea, the platform insight, the architectural observation. Demonstrate that the interest predates the application.

**Paragraph 5 — Close**
One or two sentences. Express readiness, not desperation. Point to the resume and portfolio. "Would welcome the conversation." Done.

### Voice
- Minimal pronouns; third-person distance or implicit subject preferred
- Plain speech — no dramatic framing, no hyperbole
- The insider technical language goes here as texture, not as section headers or bullets
- Tone: confident, curious, direct

### Cover Letter Must-Nots
- No bullet points
- No section headers
- No "I am excited to apply"
- No restating the resume
- No flattery toward the company ("Spotify's mission resonates deeply")
- No generic closes ("I look forward to hearing from you at your earliest convenience")

---

## Portfolio / Application Fields

Full spice permitted here. Algorithm names, counts, architectural specifics, product ideas. This is the evidence trail for anyone who digs. The cover letter points here; the portfolio substantiates.

For project descriptions:
- Lead with what it does for a user, not how it works
- Technical specifics in the second sentence or as a parenthetical
- Link to the repo or live artifact

---

## Docx Output (when building files)

Use the `docx` skill for file generation. Key formatting conventions for professional documents:

- Font: Calibri, 10pt body, 11pt job titles, 14pt name
- Colors: deep navy accent (`1F4E79`), muted gray for metadata (`595959`)
- Section dividers: bottom border on heading paragraph, not a separate rule element
- Bullet indentation: left 480 DXA, hanging 240 DXA
- Margins: 1080 DXA (0.75 inch) all sides — tighter than default to fit content
- Page size: US Letter (12240 × 15840 DXA) — docx-js defaults to A4, always override
- Triplet bullet style: bold capacity, normal arrow and action, italic benefit

---

## Iteration Protocol

When the user provides feedback mid-session:

1. **Scope the change** — identify exactly which bullet, section, or paragraph is affected
2. **Update the build script** — surgical edit, not a full rewrite
3. **Rebuild and spot-check** — `extract-text` the output and grep the changed section
4. **Present** — both files if both changed, only the changed file if not

When the user pastes their own edited version of a document, diff it against the current build and apply their changes precisely. Do not silently revert their edits on the next rebuild.

Common correction patterns from this session:
- "finance" appearing in summary when the experience is actually in aerospace, media, government
- Metrics attributed to the wrong employer
- Algorithm names leaking into resume bullets instead of staying in competencies
- Cover letter formatted as a bulleted section doc instead of prose narrative
- Education placed at top for an experienced candidate
- MSc instead of M.S.
- Song/record counts drifting back to outdated values
