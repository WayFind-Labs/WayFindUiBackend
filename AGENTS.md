# Agent Instructions & Operating Guardrails

## Core Guardrails

### 1. Mandatory Git Commit & Push Discipline
- **After Meaningful Coding / Writing Work:** Always stage, commit, and `git push` all changes to the remote repository (`origin`).
- **Clear Commit Messages:** Write descriptive, understandable commit messages using Conventional Commits format (e.g., `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`). Never use vague messages like "update files" or "fix backend".

### 2. Mandatory Project Context Maintenance
- **Keep Context Synced:** Whenever database schemas, API routes, matching logic, background jobs, or architectural components are created or modified, immediately update the project context files:
  - [`skills/context.md`](file:///e:/React/Shelter/ShelterAppUiBackend/skills/context.md)
  - [`README.md`](file:///e:/React/Shelter/ShelterAppUiBackend/README.md)
- Context documentation must remain an accurate reflection of the current codebase state.
