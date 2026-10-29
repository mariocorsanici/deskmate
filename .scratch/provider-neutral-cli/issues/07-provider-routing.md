# 07: Route Work session launch and resume

**What to build:** Start or continue work with a predictable Provider: resume with the Provider recorded by the Project card and use the Default provider only when there is no owned Work session.

**Blocked by:** 02: Detect and configure Providers; 03: Migrate to shared Project cards; 04: Put Claude behind the Provider adapter; 05: Add the Codex Provider adapter.

**Status:** ready-for-agent

- [ ] A Project card with an available recorded Provider resumes through that Provider.
- [ ] A project without a resumable Work session starts with the Default provider.
- [ ] An unavailable recorded Provider never causes a silent switch.
- [ ] When the recorded Provider is unavailable, Deskmate explains the condition and offers an explicit new Work session with an available Provider.
- [ ] Launch and resume update Project card ownership consistently.
- [ ] Human and JSON output distinguish resume, new session and refused implicit switch.
- [ ] Attempts to launch simultaneous Work sessions for one project can be detected by later switch behavior.

