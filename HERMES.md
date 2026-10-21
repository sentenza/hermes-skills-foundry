# HERMES.md — Running this repository as a Hermes agent

The full picture — the behavioral rules and the repository rules — is in [AGENTS.md](AGENTS.md). Read it first. This file only adds what is different when the agent is a Hermes agent.

## What is different here

- **Your working directory is the user's workspace, not a skill's directory.** A skill's scripts have to be run from the directory the skill was installed in, not from a path relative to the workspace.
- **Credentials are injected by the host.** A skill that needs an API key gets it from the environment, where the host put it. If it is missing, report that — do not work around it by creating a file to hold it.
