# 01: Card checks read the remote state, not the working tree

**Status:** ready-for-agent

`check.py` now runs `git fetch` before a card's checks (commit `70468e3`), which updates `origin/...` refs only. Checks that read files (`grep Status .scratch/.../issues/NN.md`) still see the working tree, stale until the user pulls.

- [ ] `/checkpoint` (step "Checks") tells the session to write file-reading checks against the remote branch, e.g. `git -C <repo> show origin/develop:<path> | grep -m1 Status`, and to keep working-tree reads only for local-only state (uncommitted files, local branches).
- [ ] The example in the skill shows one remote read and one local read, with labels that say which is which.
- [ ] A test (or documented manual check) shows a card check on a ticket file reporting the remote status when the local checkout is behind.

## Comments
