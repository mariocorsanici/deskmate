# Development workflow

## Branch roles

- `main` is the released, stable line. Promote a release to `main` only after
  stabilization, then tag the release on `main`.
- `develop` is the integration and stabilization line. Completed feature work
  lands here before it is promoted to `main`.
- `feature/<effort>` branches contain one coherent development effort. Keep
  dependent tickets for the same clean-cut change on one feature branch when
  intermediate states are not independently releasable.

## Working on a multi-ticket feature

Use one or more focused commits per ticket. At every ticket boundary:

1. run the complete relevant test suite;
2. review the ticket's commit range against its acceptance criteria;
3. update the local ticket;
4. push the feature branch as a remote checkpoint when remote access is part
   of the current task.

Do not treat a completed ticket as a completed feature branch. Merge the
feature branch into `develop` only when the whole effort has reached its
integration boundary.

For `feature/codex-cli-support`, implement all provider-neutral CLI tickets on
the same branch. The integration boundary is the complete Daily loop
validation, not an individual ticket.

## Release flow

1. Merge the complete feature into `develop`.
2. Stabilize and validate the integrated result on `develop`.
3. Promote the validated release from `develop` to `main`.
4. Tag the release commit on `main` using the repository's chosen versioning
   convention.

Branch protection, required pull requests and mandatory CI checks are planned
guardrails, not current repository policy. See `ROADMAP.md`.
