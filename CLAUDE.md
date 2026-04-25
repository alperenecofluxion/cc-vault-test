\# Project Operating Manual for Claude Code



\## Project identity

\- \*\*Name:\*\* my-app

\- \*\*Type:\*\* FastAPI service (fake OCR demo)

\- \*\*Purpose:\*\* A learning project to exercise the cc-best PM→Lead→Dev→QA workflow.



\## Knowledge base bridge

\*\*Vault path:\*\* `C:/Users/alper/vault`

\*\*Vault access:\*\* via the `obsidian-vault` MCP server (search\_notes, read\_note, write\_note, etc.)



The vault is the single source of truth for:

\- Architecture decisions (`Decisions/`, ADR format)

\- Cross-project learnings (`03-Resources/`)

\- Long-lived context for this project (`01-Projects/my-app/`)



\### When to read the vault

1\. \*\*Session start\*\* — Read `01-Projects/my-app/README.md` if it exists. If not, propose creating one before substantial work begins.

2\. \*\*Before architectural choices\*\* — Search `Decisions/` for relevant ADRs. Do not re-decide settled questions; cite the ADR if found.

3\. \*\*Before introducing a pattern\*\* — Search `02-Areas/` and `03-Resources/` first.

4\. \*\*When asked "why X?"\*\* — Cite vault notes by wikilink, not from memory.



\### When to write to the vault

1\. \*\*A non-trivial decision is finalized\*\* → ADR in `Decisions/YYYY-MM-DD-<slug>.md` using `Templates/adr.md`.

2\. \*\*A learned pattern or insight emerges\*\* → atomic note in `03-Resources/` using `Templates/note.md`.

3\. \*\*Project state change\*\* → update `01-Projects/my-app/README.md`.

4\. \*\*Never\*\* dump session transcripts or implementation chatter into the vault. Atomize first.



\### Vault discipline

\- Mandatory frontmatter on every new note (created, updated, last-reviewed, type, tags, status).

\- ≥2 outbound `\[\[wikilinks]]` per new note.

\- Search before write. Extend over duplicate.

\- Vault is a separate git repo — do not stage vault changes from this project.



\## Code conventions

\- \*\*Language:\*\* Python 3.11+

\- \*\*Framework:\*\* FastAPI

\- \*\*Dependency manager:\*\* `uv`

\- \*\*Test framework:\*\* pytest

\- \*\*Style:\*\* ruff (format + lint)

\- \*\*OCR engine:\*\* \*\*FAKE\*\* — no real model. A stub function that returns deterministic mock text based on the uploaded filename. This is intentional and must not change without an ADR.



\## Workflow

\- Use `/cc-best:iterate "<goal>"` for non-trivial work (full PM→Lead→Dev→QA chain).

\- Use `/cc-best:pm`, `/cc-best:lead`, `/cc-best:dev`, `/cc-best:qa` for finer-grained control.

\- All non-trivial decisions produce an ADR in the vault BEFORE implementation begins.

\- Never push directly to `main`. Open a PR.



\## Safety

\- Never read or write outside this project directory and the declared vault path.

\- Never commit secrets, `.env`, credentials, model files, or build artifacts.

\- Destructive git operations (force push, history rewrite, branch deletion) require explicit user confirmation in the same turn.

\- Destructive vault operations (delete\_note, cross-folder move\_note) require explicit user confirmation in the same turn.

