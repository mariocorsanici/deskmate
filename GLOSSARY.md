# Deskmate

Deskmate preserves the state and rhythm of a working day across agent sessions and projects.

## Language

**Work session**:
A focused Claude Code or Codex CLI conversation attached to one project folder.
_Avoid_: Chat, thread

**Checkpoint**:
The durable end-of-session record of where a piece of work stands and how to continue it.
_Avoid_: Recap, summary

**Project card**:
The provider-neutral record that holds the latest checkpoint and live-state checks for one project.
_Avoid_: Memory file, session note

**Handoff**:
The end-of-day view of open and completed work, assembled from project cards and verified current state.
_Avoid_: Daily summary, transcript summary

**Daily loop**:
The complete Deskmate rhythm from morning planning through checkpoints and retrospective to the evening handoff.
_Avoid_: Workflow, routine

**Session delta**:
The bounded portion of a Work session that occurred after its latest Checkpoint and may contain unrecorded progress.
_Avoid_: Full transcript, conversation dump

**Provider**:
The local agent runtime, Claude Code or Codex CLI, that owns a Work session and its transcript.
_Avoid_: Model, platform

**Default provider**:
The Provider used to start work when a Project card does not identify a Work session to resume.
_Avoid_: Preferred model, primary agent

**Provider switch**:
The continuation of a Project in a new Work session owned by the other Provider, using the shared Project card and a bounded Session delta from the previous Work session.
_Avoid_: Cross-provider resume, session transfer
