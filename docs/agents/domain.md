# Domain docs

Use this guidance when exploring the codebase or producing specs, tickets, tests, reviews, and implementation plans.

## Read on demand

- Read root `GLOSSARY.md` when the task involves domain concepts or terminology.
- Read relevant ADRs under `docs/adr/` when the task touches a recorded decision.
- If either location does not exist, proceed without creating it pre-emptively. `domain-modeling` creates these files lazily when a term or decision is resolved.

## Layout

Deskmate is a single-context repository:

```text
/
├── GLOSSARY.md
├── docs/
│   └── adr/
├── skills/
└── tools/
```

## Vocabulary

Use canonical terms from `GLOSSARY.md` in issue titles, specifications, hypotheses, test names, and user-facing explanations. When a necessary concept is absent or ambiguous, invoke `domain-modeling` before inventing another term.

## Decisions

Surface conflicts with an existing ADR explicitly. Reference the ADR and explain why reopening the decision may be justified instead of silently overriding it.
