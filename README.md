<div align="center">
  <img src="frontend/src/renderer/assets/logo.png" alt="Nebula Intelligence logo" width="120">
  <h1>AIris</h1>
  <p><strong>A local Windows desktop financial BI platform for source-grounded research, market analysis, and Word, Excel, and PowerPoint generation.</strong></p>
  <p>
    <a href="https://arxiv.org/abs/2603.08329"><img src="https://img.shields.io/badge/arXiv-2603.08329-b31b1b" alt="SPD-RAG paper on arXiv"></a>
    <a href="https://teknofest.org/tr/yarismalar/finansal-teknolojiler-yarismasi/"><img src="https://img.shields.io/badge/TEKNOFEST%202025-3rd%20place-0F172A" alt="TEKNOFEST 2025 Financial Technologies, third place"></a>
    <img src="https://img.shields.io/badge/platform-Windows-0078D4" alt="Platform: Windows">
    <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-1F6FEB" alt="License: PolyForm Noncommercial 1.0.0"></a>
  </p>
  <p>
    <a href="#demo">Demo</a>
    ·
    <a href="#quick-start">Quick start</a>
    ·
    <a href="ARCHITECTURE.md">Architecture</a>
    ·
    <a href="https://arxiv.org/abs/2603.08329">SPD-RAG paper</a>
    ·
    <a href="CONTRIBUTING.md">Contributing</a>
  </p>
</div>

> [!IMPORTANT]
> AIris is a research prototype that runs locally and calls third-party APIs configured by the user. Some workflows send document content, prompts, or generated artifacts to paid external services. See [External services](#external-services).
>
> The source is available under the [PolyForm Noncommercial License 1.0.0](LICENSE.md): noncommercial use is permitted, commercial use is not. See [License](#license).

## Demo

[![Watch the AIris demonstration: document research, market analysis, and report generation](https://img.youtube.com/vi/bpOPxwwpNus/hqdefault.jpg)](https://www.youtube.com/watch?v=bpOPxwwpNus)

**Full demo** on YouTube (Turkish audio). The [example workflow](#example-workflow) below is an English written walkthrough of the same capabilities.

## What AIris does

AIris is a financial BI platform for teams whose evidence is scattered across reports, contracts, filings, and market data. A user uploads those documents, asks questions in English or Turkish, and receives streamed answers with source cards, the retrieved tables and figures, charts, and finished Office files.

A coordinator agent owns each conversation and calls specialist agents as tools. Answers are grounded in retrieved evidence from the user's documents and from market, macroeconomic, and web sources. For questions that must cover every selected document, AIris switches to SPD-RAG, a per-document retrieval method published in [arXiv:2603.08329](https://arxiv.org/abs/2603.08329) and implemented in this repository.

## Key capabilities

- **Grounded document Q&A.** Hybrid vector and BM25 retrieval with Cohere reranking; answers carry source cards and the supporting table or figure images.
- **Exhaustive cross-document research.** SPD-RAG assigns one retrieval agent per document, then merges findings through token-bounded recursive synthesis.
- **Market and macro data.** Marketstack end-of-day data and Turkish Central Bank EVDS series, discovered semantically and retrieved by date range.
- **Charts and Office deliverables.** Interactive Plotly charts and Word, Excel, or PowerPoint files generated from sandboxed code and returned as attachments.
- **Financial news workspace.** RSS stories clustered and summarized by an LLM, with a dedicated agent for questions about a story.
- **Live progress.** Every tool call, specialist step, and SPD-RAG document is streamed to the desktop client over Server-Sent Events.

## Project status

AIris is a research and competition project intended for local evaluation and extension. It has not been audited for production trading, regulated financial workflows, multi-user deployment, or unattended operation. Generated analysis may omit context or draw unsupported inferences and should be verified against the displayed sources. Outputs are framed as analysis, not investment advice.

## Quick start

### Prerequisites

- Windows with PowerShell
- Python 3.11
- Node.js 20.18.1 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- API keys for the providers listed under [Minimum configuration](#minimum-configuration)

### Install

```powershell
git clone https://github.com/NebulAICompany/AIris.git
Set-Location AIris

uv sync --locked
.\.venv\Scripts\Activate.ps1

Copy-Item .env.example .env
# Edit .env and add your keys.

Set-Location frontend
npm ci
Set-Location ..
```

### Minimum configuration

The backend creates its provider clients at startup, so these values must be present in `.env` before it will start:

| Variable | Used for |
| --- | --- |
| `ANTHROPIC_API_KEY` | Coordinator and specialist agents |
| `OPENAI_API_KEY` | Moderation, SPD-RAG, summarization, news, vision |
| `COHERE_API_KEY` | Embeddings and reranking |
| `TAVILY_API_KEY` | Web search |
| `QWEN_API_KEY` | Alternative model client |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Document parsing service endpoint |

Feature-specific keys are listed under [External services](#external-services). `.env` is ignored by git; never commit it.

### TCMB macroeconomic data setup (optional)

If you plan to use the TCMB macroeconomic data agent to query Turkish Central Bank EVDS indicators, initialize the local Qdrant collections (`datagroups` and `series`):

```powershell
.\.venv\Scripts\Activate.ps1
# Requires TCMB_API_KEY and COHERE_API_KEY in .env
python backend/utils/tcmb_rag.py
```

- **Extraction & Caching:** Queries the EVDS API for all datagroups and series, caching the structured result into `clean_datagroups_with_series.json`. If the file already exists, it skips EVDS calls and proceeds directly to vector indexing.
- **Indexing:** Embeds datagroups and series using Cohere `embed-v4.0` and upserts them into the local Qdrant vector store (`backend/database/vectorstore`).
- **CLI Options:**
  - `--skip-embed`: Only extract and update `clean_datagroups_with_series.json` without embedding to Qdrant.
  - `--force-extract`: Force re-downloading from the EVDS API even if the JSON exists.
  - `--batch-size 32`: Adjust Cohere embedding batch size.

### Run

Start the backend, then start the desktop client in a second terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python backend_runner.py
```

```powershell
.\.venv\Scripts\Activate.ps1
python frontend_runner.py
```

Success state: `GET http://127.0.0.1:8001/health` returns JSON and the Electron window opens. The first start takes longer while local stores initialize.

## Example workflow

1. Upload a central bank inflation report (PDF). Azure Document Intelligence extracts page-aware Markdown, tables, and figures; chunks are embedded with Cohere and indexed in Qdrant and BM25.
2. Ask: "How did the inflation forecast change, and which factors were positive?" The coordinator runs hybrid retrieval over the selected report and returns an answer with source cards plus the relevant table and chart images. It can call the TCMB agent to ground the answer in official series.
3. Ask: "Compare these two stocks over the last quarter and give me a report." The coordinator calls the finance agent for end-of-day prices, the plotting agent for an interactive chart, and the file agent, which generates a Word document in an E2B sandbox. The chart and the document are returned as attachments.
4. Select several contracts and enable SPD-RAG. Ask: "Across all of these contracts, which ones...". One agent researches each document in parallel; the findings are clustered and synthesized into a single sourced answer while the client shows per-document progress.

## Architecture

The Electron client talks to a local FastAPI process on `127.0.0.1:8001` over HTTP and Server-Sent Events. A coordinator agent owns the conversation and calls specialists as tools; specialists do not call each other. Documents and indexes are stored on the machine. Parsing, embedding, model inference, and generated-code execution use external providers, and all model-generated code runs in remote E2B sandboxes rather than on the host.

![AIris system architecture: Electron desktop client, local FastAPI runtime, coordinator and specialist agents, local Qdrant and BM25 indexes, and external providers](docs/assets/architecture/system-overview.svg)

Component responsibilities, request flow, ingestion pipeline, and design rationale are in [ARCHITECTURE.md](ARCHITECTURE.md).

## SPD-RAG research

Standard RAG shares one top-k budget across the whole corpus, so evidence from lower-ranked documents is dropped on questions like "compare X across all reports". SPD-RAG (Sub-Agent Per Document RAG) decomposes retrieval along the document axis: a reasoning model writes a shared task list, one bounded agent researches each document in parallel, and findings are clustered and summarized in token-bounded batches until one answer remains.

![SPD-RAG: shared task list, one retrieval agent per document, then clustered recursive synthesis](docs/assets/architecture/spd-rag.svg)

- **Paper:** [arXiv:2603.08329](https://arxiv.org/abs/2603.08329)
- **Implementation in this repository:** [`backend/core/spdrag/`](backend/core/spdrag/)
- **Benchmark code and data:** [NebulAICompany/SPD-RAG](https://github.com/NebulAICompany/SPD-RAG)
- **Citation:** [`CITATION.cff`](CITATION.cff)

Results reported in the paper on the Loong benchmark (English, 200k-250k token instances, 102 cases, GPT-5 as judge; higher score is better):

| System | Average score | Cost per query (USD) |
| --- | ---: | ---: |
| Full context (oracle) | 68.0 | 0.273 |
| Normal RAG | 33.0 | 0.080 |
| Agentic RAG | 32.8 | 0.098 |
| SPD-RAG | 58.1 | 0.103 |

In that evaluation SPD-RAG reached 85.4% of full-context quality at 37.9% of its API cost. The paper used Gemini 2.5 Pro and Flash; this repository uses GPT-5 and GPT-5-mini in the same roles. The table reproduces the paper's numbers and is not a benchmark run from this repository.

## Evaluation

Agent behavior is evaluated with trajectory scoring: [`tests/test_trajectory/test.py`](tests/test_trajectory/test.py) runs the coordinator on sampled queries, scores each full trajectory with an LLM judge ([agentevals](https://github.com/langchain-ai/agentevals)), and applies heuristics for redundant or looping tool calls. It calls live providers and writes a `metrics.txt` report.

```powershell
.\.venv\Scripts\Activate.ps1
python tests/test_trajectory/test.py
```

Benchmark results for SPD-RAG come from the paper and its [evaluation repository](https://github.com/NebulAICompany/SPD-RAG).

## External services

AIris uses bring-your-own credentials. Each provider may charge for requests.

| Provider | Feature | Data sent | Key |
| --- | --- | --- | --- |
| Anthropic | Coordinator and specialist agents | Prompts and retrieved context | `ANTHROPIC_API_KEY` (startup) |
| OpenAI | Moderation, SPD-RAG, summarization, news, vision | Prompts, retrieved context, figure images | `OPENAI_API_KEY` (startup) |
| Cohere | Embeddings and reranking | Document chunks, figures, and queries | `COHERE_API_KEY` (startup) |
| Tavily | Web search | Search queries | `TAVILY_API_KEY` (startup) |
| Qwen | Alternative model client | None unless selected in code | `QWEN_API_KEY` (startup) |
| Azure Document Intelligence | PDF and Word parsing | Uploaded document content | `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` (startup), `AZURE_DOCUMENT_INTELLIGENCE_KEY` |
| E2B | Sandboxed chart and Office generation | Generated code and referenced files | `E2B_API_KEY` |
| Marketstack | Market data and dashboard | Symbol and date requests | `MARKETSTACK_API_KEY` |
| TCMB EVDS | Turkish Central Bank series | Series codes and date ranges | `TCMB_API_KEY` |
| Wolfram Alpha | Computation | Query text | `WOLFRAM_APP_ID` |
| GoldAPI or MetalpriceAPI | Live gold prices in the desktop widget | Price requests | `GOLDAPI_KEY` or `METALPRICEAPI_KEY` |

Optional: `DEEPSEEK_API_KEY`, LangSmith tracing variables, and the GLM/vLLM helper under `backend/external/glm/`. Full variable list: [`.env.example`](.env.example).

## Privacy and data flow

- The Electron client and FastAPI backend run on the local machine. Chat history, uploads, and indexes are stored under directories ignored by git (`backend/database/`, `qdrant_storage/`).
- Document content leaves the machine when it is parsed (Azure), embedded or reranked (Cohere), included in a prompt (model providers), or staged for generation (E2B), as listed above.
- Main-chat web search is off unless the user enables it for a query; news-story chat includes web search.
- The API binds to loopback and has no authentication layer. Run it on a trusted machine and do not expose port `8001`.

## Supported files

| Kind | Extensions |
| --- | --- |
| Documents | `.pdf`, `.docx`, `.txt` |
| Spreadsheets | `.xlsx`, `.xls` |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp` |

## Limitations

- Single-user desktop application; no multi-tenant or hosted deployment.
- Model outputs are non-deterministic and depend on the configured providers; provider outages affect the corresponding features.
- The default coordinator model is Claude Sonnet 4.6; switching models is a code change.
- Benchmark results above come from the paper, not from a committed evaluation run in this repository.
- There is no automated unit test suite yet; evaluation relies on the trajectory scoring above and manual verification of workflows.

## Documentation

| Document | Content |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, request flow, ingestion, SPD-RAG internals, design decisions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Environment setup, pull-request expectations, verifying changes |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting and scope |
| [CITATION.cff](CITATION.cff) | Machine-readable citation metadata |
| [LICENSE.md](LICENSE.md) | PolyForm Noncommercial License 1.0.0 |
| [`.env.example`](.env.example) | Environment variable reference |

## Repository layout

```text
AIris/
  backend/                 FastAPI app, agents, retrieval, ingestion
    app/                   HTTP routes and SSE
    core/                  Coordinator, specialists, SPD-RAG
    pipeline/              Query and upload pipelines
    retrieval/             Qdrant, BM25, rerank, contextual headers
    security/              Input moderation
  frontend/                Electron desktop client
  tests/                   Evaluation and integration scripts
  docs/assets/             Architecture diagrams
  backend_runner.py        Start the API on 127.0.0.1:8001
  frontend_runner.py       Start the Electron client
```

## Recognition

AIris placed joint third in the [TEKNOFEST 2025 Financial Technologies competition](https://teknofest.org/tr/yarismalar/finansal-teknolojiler-yarismasi/) as team NebulAI.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, pull-request expectations, and how to verify changes that depend on external providers. Contributions are accepted under the project [license](#license).

## Security

Do not open public issues for vulnerabilities. Follow the process in [SECURITY.md](SECURITY.md).

## Citation

If you use SPD-RAG or this implementation in academic work, cite the paper:

```bibtex
@misc{akay2026spdrag,
  title         = {SPD-RAG: Sub-Agent Per Document Retrieval-Augmented Generation},
  author        = {Yagiz Can Akay and Muhammed Yusuf Kartal and Esra Alparslan and Faruk Ortakoyluoglu and Arda Akpinar},
  year          = {2026},
  eprint        = {2603.08329},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  doi           = {10.48550/arXiv.2603.08329},
  url           = {https://arxiv.org/abs/2603.08329}
}
```

GitHub also exposes [CITATION.cff](CITATION.cff) via **Cite this repository**.

## License

AIris is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE.md). You may use, modify, and share the software for noncommercial purposes, including personal study, research, and use by educational and other noncommercial organizations, under the terms in `LICENSE.md`. Commercial use requires a separate agreement — contact [nebulaicompany@gmail.com](mailto:nebulaicompany@gmail.com).

Required Notice: Copyright 2025-2026 Nebula Intelligence

This is a source-available license, not an OSI-approved open-source license, so GitHub may not detect it automatically. The license does not require attribution in publications, but if you build on SPD-RAG or this implementation in academic work, we ask that you cite the paper as shown in [Citation](#citation).
