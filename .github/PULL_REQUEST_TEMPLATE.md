Fixes #

<!-- Keep the `Fixes #xx` keyword at the very top and update the issue number when this PR closes an issue. Replace this comment with a 1-2 sentence description of the change. -->

Read [CONTRIBUTING.md](../CONTRIBUTING.md) before opening a pull request.

If you paste a large, clearly unreviewed AI-generated description here, the pull request may be ignored or closed.

1. Description

  - Write 1-2 sentences that make the change easy to understand: who benefits, what problem they had, and how this solves it.
  - The `Fixes #xx` line at the top is required when the work closes an issue. Update the number and keep the keyword.
  - If there are any breaking changes, describe them.

2. Scope

  - Keep the change focused. Do not mix retrieval, UI, and provider changes unless they are one behavior.
  - Update README or ARCHITECTURE when setup, user-visible behavior, or architecture changes.
  - Do not add dependencies unless the change requires them. If it does, update `uv.lock` or `package-lock.json` in the same change and explain why.
  - Do not commit secrets, `.env` files, databases, uploads, or vector-store files.

3. How did you verify the change?

  - What you ran (commands or a manual workflow).
  - Which paid providers were involved, if any.
  - What you observed (for example source cards, charts, generated files, SPD-RAG progress).
