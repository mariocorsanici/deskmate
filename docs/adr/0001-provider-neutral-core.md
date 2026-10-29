# Provider-neutral core with Claude and Codex adapters

Deskmate uses one set of skills, one shared state, and one stable command interface for its Daily loop. Claude Code and Codex CLI differences stay behind Provider adapters for installation, hooks, session discovery, Session delta extraction, usage metrics, and session launch or resume; this avoids duplicated workflows and lets a Project card move between Providers without becoming two sources of truth.

## Consequences

- A Project has one shared Project card regardless of which Provider updates it.
- Native skill invocation remains Provider-specific: `/skill` in Claude Code and `$skill` in Codex CLI.
- Provider-specific raw analytics remain distinct even when future normalized comparisons combine their views.
- Failure of a transcript adapter degrades Session delta analysis but does not stop the Daily loop.
- A Provider switch starts a new Work session from the shared Project card, current Checks, and a bounded Session delta; it is not treated as a cross-provider resume.
