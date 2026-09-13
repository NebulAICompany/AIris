# Security policy

AIris is a single-user local desktop application. The FastAPI process binds to loopback and has no application-level authentication. CORS allows the Electron `file://` origin (`null`) and pages served by the same process on `http://127.0.0.1:8001` and `http://localhost:8001`. Loopback and CORS do not prevent access by other local processes. Run the backend only on a trusted machine and do not expose port `8001`. Depending on the feature, document content, prompts, retrieved context, referenced files, symbols, or series requests are sent to third-party providers configured in `.env`.

## Supported versions

Security fixes are accepted against the default branch of this repository. Older snapshots are not maintained as separate release lines.

## Reporting a vulnerability

Report vulnerabilities privately. Do not open a public issue, pull request, or discussion that describes an exploitable flaw.

Once private vulnerability reporting is enabled for the public repository, use **Security > Report a vulnerability**. If that form is unavailable, email [nebulaicompany@gmail.com](mailto:nebulaicompany@gmail.com). Do not disclose exploit details in a public issue.

Include:

- a description of the issue and its impact
- affected files, routes, or desktop IPC handlers
- steps to reproduce on a local checkout
- whether user documents, API keys, or generated files can leave the intended path
- any proof you already have, without publishing it

You should receive an acknowledgement within 48 to 72 hours after a maintainer sees the report. We will confirm whether the issue is accepted, ask for more detail if needed, and describe the planned fix or the reason it is out of scope.

Do not publish a write-up, proof of concept, or exploit details until we have shipped a fix or told you the report is declined. If we ask for time to patch, keep the report private for that coordinated window.

We will not pursue legal action against researchers who report in good faith through this private channel, stay within the product's documented local-evaluation use, and do not access other users' data, destroy data, or disrupt services.

## Out of scope as product defects

The following are documented properties of the current design, not unexpected exposures by themselves:

- the local API has no authn/authz
- CORS is limited to the desktop `file://` origin and the local backend origin; it is not a security boundary for non-browser clients on the same machine
- Azure Document Intelligence, Cohere, model providers, E2B, market/TCMB data services, Tavily, Wolfram Alpha, RSS publishers, and gold-price providers are external services
- the Electron renderer loads selected styles, fonts, and client-side libraries from cdnjs, jsDelivr, and Google Fonts
- main-chat web search sends the query to Tavily when the user enables that toggle; news-story chat has the Tavily tool available by design
- moderation covers the main chat query paths only, and fails open when the OpenAI moderation request errors; news-story chat is not moderated

Unexpected access beyond loopback, secret leakage into the repository or logs, sandbox escape to the host, or path traversal outside managed document directories should still be reported.
