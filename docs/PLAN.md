# F13 Demo – Plan (draft)

Status: **draft, waiting on the open questions at the end.**

## 1. What F13 is

F13 is the open-source AI assistant ("KI-Assistenz") of the State of
Baden-Württemberg, developed by InnoLab_bw with PD and operated at BITBW. It has
been open source since 23 July 2025. The code is on openCode under
MPL-2.0: <https://gitlab.opencode.de/f13>.

- Browser-based assistant for drafting text, processing documents and research.
- Built for open-source LLMs. It can run fully self-hosted without an external
  cloud, but it can also use hosted models.
- It is a set of microservices. A central **Core** service connects the
  **Frontend** to the feature services:

| Repo (`gitlab.opencode.de/f13/microservices/…`) | Role |
| --- | --- |
| `frontend` / `f13-frontend` | Web UI |
| `core` | API layer between frontend and services (v3: APISIX gateway) |
| `chat` | Chat against local or externally hosted LLMs |
| `summary` | Map-reduce summaries of documents |
| `parser` | Turns `.pdf` / `.docx` into text (latest seen: v2.1.5, CPU-only by default) |
| `rag` | Natural-language search over texts and databases |

> **Not yet verified:** These details come from secondary sources and still need
> checking against the official READMEs: the frontend stack (React or Svelte),
> guest mode vs. Keycloak login in v3, the OPA sidecar that chat v3 needs, and the
> exact compose files. `gitlab.opencode.de` was blocked from the environment where
> this plan was written.

## 2. Demo goal (proposed default)

A **self-hosted, reproducible F13 instance** that starts with one command and
runs a short scripted walkthrough of about 10 minutes:

1. **Chat:** ask a question in plain language, then draft a citizen-facing
   letter ("Bürgerbrief") in simple language ("Leichte Sprache").
2. **Summary:** upload a public PDF, such as a published administrative
   regulation, and get a structured summary.
3. *(Optional)* **RAG:** search a small knowledge base of public documents and
   get answers with sources.
4. **Sovereignty:** show that the model runs locally or on a German or EU
   provider and that no data leaves the setup.

## 3. Architecture for the demo

```
Browser ──► Frontend ──► Core (APISIX) ──┬─► Chat ────┐
                                         ├─► Summary ─┼─► LLM endpoint (OpenAI-compatible)
                                         │     └─► Parser
                                         └─► RAG (optional) ──► vector DB
```

There are three options for the LLM endpoint (see open question Q2):

| Option | Good for | Requirements |
| --- | --- | --- |
| **A. Ollama** on a laptop or VM | Offline demo, cheap | ≥16 GB RAM, small model (7–14B); answers are slower |
| **B. vLLM** on a GPU VM | Realistic speed, "like production" | GPU VM (e.g. 1× L4/A10/L40S); costs per hour |
| **C. Hosted OpenAI-compatible API** (e.g. STACKIT AI Model Serving) | Fastest to set up | API key; data goes to the provider |

## 4. Phases

### Phase 0: Decisions (½ day)
- Answer the open questions in §7, then fix the scope (2 or 3 features) and the
  demo date.

### Phase 1: Recon (½–1 day)
- Clone `core`, `frontend`, `chat`, `summary` and `parser` (and `rag` if needed)
  from openCode.
- Read each README and pin the versions and image tags in `versions.env`.
- Write down the config files for each service, e.g. summary uses
  `general.yml`, `llm_models.yml` and `prompt_maps.yml`.

### Phase 2: LLM backend (½ day)
- Set up the chosen endpoint (A, B or C).
- Smoke test: `curl …/v1/chat/completions` returns an answer.
- Choose the model. It should be good in German, for example Mistral Small or a
  Llama 3.x / Qwen instruct model, and its license must allow the demo.

### Phase 3: Minimal stack: Chat (1 day)
- Write `docker-compose.yml` in this repo with frontend, core, chat and an
  LLM config pointing to the endpoint.
- `make up` starts the stack; chat works in the browser.

### Phase 4: Summary + Parser (½–1 day)
- Add `summary` and the CPU `parser` to the compose stack.
- Test with 2–3 public PDFs (stored in `demo-data/`).

### Phase 5 (optional): RAG (1 day)
- Add the `rag` service and its vector DB, index `demo-data/`, and check that
  answers include sources.

### Phase 6: Make it demo-ready (½–1 day)
- `docs/DEMO-SCRIPT.md`: click-by-click script with the exact prompts and
  expected results.
- `scripts/healthcheck.sh`: checks all services and the LLM before going on stage.
- `scripts/reset.sh`: clears chat history and uploads.
- **Fallback:** a screen recording of the full run in case the network or GPU
  fails.
- One full dry run on the target machine.

**Estimated effort:** 3–5 days, depending on RAG and on how well the upstream
compose files work.

## 5. Proposed repo layout

```
f13-demo/
├── docker-compose.yml        # whole demo stack
├── versions.env              # pinned F13 image tags/commits
├── config/                   # per-service config (llm_models.yml, prompt maps, …)
├── demo-data/                # public sample documents only
├── scripts/                  # up/down, healthcheck, reset
├── docs/
│   ├── PLAN.md               # this file
│   └── DEMO-SCRIPT.md        # walkthrough
└── Makefile                  # make up / down / check / reset
```

## 6. Risks

| Risk | Mitigation |
| --- | --- |
| Upstream compose files or docs are incomplete or don't match v3 | Recon phase first; pin versions; keep our own compose file |
| Login/auth (Keycloak vs. guest mode) blocks the demo | Prefer guest mode for the demo; add Keycloak only if login is needed |
| Local model too slow or weak in German | Test early (Phase 2); keep option C as a backup |
| GPU VM not available on demo day | Book or start it ahead of time; have the recording as fallback |
| Data protection | Only public documents; no real personal data in prompts |
| Network or venue Wi-Fi | Option A/B runs fully offline; recording as fallback |

## 7. Open questions

1. **Audience and purpose:** internal showcase, customer or authority pitch,
   conference talk, or a hands-on workshop?
2. **LLM backend:** A (Ollama, local), B (vLLM on GPU) or C (hosted API)? Is
   there a GPU or a cloud account available?
3. **Where does it run?** A presenter's laptop, a cloud VM, or a shared URL
   that others can open?
4. **Features:** chat + summary only, or RAG as well? Is there a specific use
   case or document set that should be shown?
5. **Language and branding:** should the UI and demo be in German (F13
   default) or English? Any custom branding?
6. **Deadline:** when is the demo?

## Sources

- [F13 KI Assistenz – EU OSS Catalogue](https://interoperable-europe.ec.europa.eu/eu-oss-catalogue/solutions/f13-ki-assistenz)
- [F13 KI Assistenz – openCode](https://opencode.de/de/software/f-13-ki-assistenz-5250)
- [F13 wird Open Source – Staatsanzeiger](https://www.staatsanzeiger.de/nachrichten/politik-und-verwaltung/f13-wird-open-source-baden-wuerttemberg-bringt-ki-in-die-verwaltung/)
- [KI-Assistenz F13 wird Open-Source-Software – Treffpunkt Kommune](https://www.treffpunkt-kommune.de/der-startschuss-fuer-ein-souveraenes-europaeisches-ki-oekosystem-ki-assistenz-f13-wird-open-source-software/)
- [F13 Kennenlernen – f13-os.de](https://f13-os.de/kennenlernen/)
- [openCode F13 group](https://gitlab.opencode.de/f13) – microservices: [chat](https://gitlab.opencode.de/f13/microservices/chat), [core](https://gitlab.opencode.de/f13/microservices/core), [frontend](https://gitlab.opencode.de/f13/microservices/frontend), [summary](https://gitlab.opencode.de/f13/microservices/summary), [parser releases](https://gitlab.opencode.de/f13/microservices/parser/-/releases), [rag](https://gitlab.opencode.de/f13/microservices/rag)
- [STACKIT F13 offering](https://stackit.de/en/?p=43779021)
- [vLLM OpenAI-compatible server](https://docs.vllm.ai/en/v0.8.5/serving/openai_compatible_server.html)
