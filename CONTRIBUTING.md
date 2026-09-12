# Contributing to AIris

Thanks for your interest in AIris. Read [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md) first; they describe the system and the external providers it depends on.

## Environment

Work on Windows with Python 3.11 or newer, Node.js 20.18.1 or newer, and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```powershell
uv sync --locked
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
Set-Location frontend
npm ci
Set-Location ..
```

Fill in the keys listed under [Backend startup configuration](README.md#backend-startup-configuration) in the README, plus any feature-specific credentials for the path you are changing. Do not commit `.env`, databases, uploads, or vector-store files.

## Running locally

Use two terminals after activating the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
python backend_runner.py
```

```powershell
.\.venv\Scripts\Activate.ps1
python frontend_runner.py
```

Confirm `GET http://127.0.0.1:8001/health` before sending queries. The backend binds to loopback only.

## Pull requests

1. Create a branch from the default branch.
2. Keep the change focused. Do not mix retrieval, UI, and provider changes unless they are one behavior.
3. Match existing module layout: agents and tools in `backend/core/`, HTTP in `backend/app/`, retrieval in `backend/retrieval/`, Electron UI in `frontend/src/`.
4. Keep imports at the top of the file.
5. Do not add dependencies unless the change requires them; explain the need in the pull request and update `uv.lock` or `package-lock.json` in the same change.
6. Update [README.md](README.md) or [ARCHITECTURE.md](ARCHITECTURE.md) when user-visible behavior, setup, or architecture changes.

## Verifying changes

Automated unit tests are not yet part of the project; contributions that add them are welcome.

The frontend's `npm test` script is a placeholder rather than a working test suite.

For changes to the coordinator or its tools, run the trajectory evaluation. It calls live providers, scores each agent trajectory with an LLM judge, and writes `metrics.txt`:

```powershell
.\.venv\Scripts\Activate.ps1
python tests/test_trajectory/test.py
```

The other scripts under `tests/` are integration helpers for retrieval, TCMB, and charting, and most of them also call live provider APIs.

Exercise the affected workflow manually as well and describe in the pull request what you ran, which provider-backed paths were involved, and what you observed (source cards, charts, generated files, SPD-RAG progress).

## Secrets

- Never commit keys, tokens, session databases, or uploaded documents.
- Do not log full prompts, document contents, or secrets.

## Security reports

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).

## License

AIris is distributed under the [PolyForm Noncommercial License 1.0.0](LICENSE). Copyright is held by the Nebula Intelligence team. By submitting a contribution you agree that it is provided under the same license and that Nebula Intelligence may include it in the project. Commercial licensing: [nebulaicompany@gmail.com](mailto:nebulaicompany@gmail.com).
