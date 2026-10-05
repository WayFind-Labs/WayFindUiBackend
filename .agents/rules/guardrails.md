# Guardrails & Workflow Standards for Wayfind Backend

## 1. Git Commit & Push Guardrail (Mandatory)
- **Automatic Push After Meaningful Work:** After completing any meaningful writing, coding, refactoring, database migration, API endpoint addition, or bug fix, you must stage, commit, and run `git push` to the remote repository (`origin`).
- **Descriptive & Understandable Commit Messages:** Commit messages must strictly follow Conventional Commits (e.g., `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`) with clear, understandable descriptions explaining *what* was changed and *why*.
  - Example: `feat(api): implement masked twilio bridge proxy endpoint`
  - Example: `fix(matching): adjust temporal window buffer boundary condition`

## 2. Project Context Synchronization Guardrail (Mandatory)
- **Keep Project Context in Sync:** If the work requested or performed alters, introduces, or extends the backend architecture, database schema, endpoints, matching logic, third-party integrations, or guardrails, you **must immediately update** the project context documentation (`skills/context.md`, `README.md`).
- Never leave project context files outdated or inconsistent with the active code implementation.
