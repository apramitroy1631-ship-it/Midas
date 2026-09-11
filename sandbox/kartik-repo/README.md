<div align="center">

<br/>

<h1>
  <img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=900&size=38&duration=3000&pause=1000&color=8B5CF6&center=true&vCenter=true&width=700&lines=Multi-Agent+Marketing+System" alt="Multi-Agent Marketing System" />
</h1>

<p>
  <img src="https://img.shields.io/badge/-%F0%9F%A4%96%20Autonomous%20AI%20Marketing%20Pipeline-8b5cf6?style=for-the-badge&labelColor=0f0f0f&color=8b5cf6" />
</p>

<h3>
  <p>An autonomous AI pipeline that takes a brand and a campaign goal — and outputs a fully researched, strategized, written, QA'd, and analytics-forecasted marketing campaign. Zero human intervention required between steps.</p>
</h3>

<br/>

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/🕸️ LangGraph-Orchestration-ef4444?style=flat-square" />
  <img src="https://img.shields.io/badge/🦜 LangChain-Integrated-1c3f59?style=flat-square" />
  <img src="https://img.shields.io/badge/🧠 Multi--Agent-Pipeline-8b5cf6?style=flat-square" />
  <img src="https://img.shields.io/badge/✅ Pydantic_v2-Validated_I/O-22c55e?style=flat-square" />
  <img src="https://img.shields.io/badge/🔀 LLM-Agnostic-f59e0b?style=flat-square" />
  <img src="https://img.shields.io/badge/📊 LangSmith-Observable-0ea5e9?style=flat-square" />
  <img src="https://img.shields.io/badge/🧠 Brand_Memory-Persistent-7c3aed?style=flat-square" />
  <img src="https://img.shields.io/badge/🌐 Web_Search-Live_Intel-16a34a?style=flat-square" />
  <img src="https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=flat-square&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/MongoDB-Memory_Store-47A248?style=flat-square&logo=mongodb&logoColor=white" />
</p>

<br/>


</div>

---

## 🧩 The Problem It Solves

Marketing campaigns require a chain of specialists — researcher, strategist, copywriter, compliance reviewer, analyst — each handing off manually, inconsistently, and slowly. Most AI tools patch one step. None of them connect the chain.

This system replaces the entire workflow. One brief in, one complete campaign out — researched, strategized, written, QA-gated, and analytics-forecasted autonomously. Brand memory compounds across every run.

Given a brand and a campaign brief, it autonomously:

1. **Researches** the market using live web search and competitor intelligence
2. **Designs a strategy** grounded in that research and the brand's historical memory
3. **Writes channel-native content** (LinkedIn posts, emails, ads — each native to its channel)
4. **QA-reviews** every asset against brand guidelines, blocking anything that violates them
5. **Forecasts performance analytics** including impressions, CTR, conversions, and budget allocation per channel
6. **Publishes** the campaign to the database with full auditability

Each step is an **autonomous AI agent** — specialized, tool-equipped, and orchestrated by a **LangGraph state machine**.

---

## 🏗️ System Workflow

<img width="3000" height="1220" alt="agent_pipeline (2)" src="https://github.com/user-attachments/assets/10b13425-b188-42b9-905e-3edf89304fe4" />

---

## ✨ Key Features

| Feature | Description |
|---|---|
| ⚛ **ReAct Agent Flow** | Agents follow Reason → Act → Observe, invoking tools iteratively — no single-pass guessing |
| 🛠 **Isolated Tool Registries** | Each agent has a strictly scoped toolset — cross-domain tool calls are impossible by design |
| ✅ **Pydantic v2 Validated I/O** | Every agent input/output is a typed model — malformed LLM responses surface as API errors, never propagate silently |
| 🗂 **Single Shared Graph State** | All 6 nodes share one `CampaignState` TypedDict — data flows automatically through the pipeline |
| 🧠 **Context Management** | Each agent receives only its relevant context slice — prevents token overflow and prompt dilution |
| 🔀 **LLM Agnostic** | `LLMFactory` swaps any agent between GPT-4o, Claude, or local Ollama with one config change |
| ⚙️ **Conditional QA Gating** | Zero critical issues → publish. Any critical issues → pipeline halts entirely |
| 🧠 **Persistent Brand Memory** | Brand memory compounds across campaigns — strategy improves with every run |

---

## 🤖 The Agent Pipeline

| Agent | Tools | LLM Calls | Output Schema |
|---|---|---|---|
| 🔍 Research | `web_search`, `serper_competitor_lookup` | Multi-step (ReAct) | `ResearchOutput` |
| 📊 Strategy | `get_brand_memory`, `get_past_campaigns`, `get_brand_guidelines` | Multi-step (ReAct) | `StrategyOutput` |
| ✍️ Content | `get_brand_guidelines`, `get_brand_tone` | Multi-step (ReAct) | `ContentOutput` |
| 🔎 QA | None (reasoning only) | Single | `QAReport` |
| 📈 Analytics | None (reasoning only) | Single | `AnalyticsReport` |
| 📤 Publish | None | — | Persists to MongoDB |

---

## 🤖 Agents Explained

### 1. 🔍 Research Agent
- Calls **Tavily** (semantic web search) and **Serper** (Google Search API) for live market data
- Gathers competitor intelligence, trend signals, and audience insights
- Outputs structured research JSON fed directly into the strategy agent

### 2. 📊 Strategy Agent
- Consumes research output + brand memory (past campaigns, guidelines, insights)
- Designs a data-driven campaign strategy: objectives, channels, tactics, timeframes
- Uses `get_brand_memory` and `get_past_campaigns` to ensure brand continuity
- Explicitly constrained: no aspirational fluff — only measurable, budget-realistic objectives

### 3. ✍️ Content Agent
- Writes channel-native assets (copy varies dramatically per channel — TikTok ≠ email ≠ ad)
- Respects brand tone, USP, and content restrictions via `get_brand_guidelines` / `get_brand_tone`
- Uses multi-step tool calling (up to 4 steps) before producing final JSON output

### 4. 🔎 QA Agent
Reviews every content asset against 5 quality dimensions:
- Brand identity without name-dropping
- USP clarity
- Channel-native format/tone
- Content restriction compliance
- CTA specificity and goal alignment

**Hard gate**: critical issues block publishing and halt the pipeline entirely.

### 5. 📈 Analytics Agent
- Forecasts impressions, clicks, CTR, conversion rate, and budget allocation per channel
- Arithmetically consistent channel-level breakdowns
- Returns structured `AnalyticsReport` for storage and display

### 6. 📤 Publish Node
- Persists finalized campaign (strategy + content + QA report + analytics) to MongoDB
- Associates campaign with brand for historical memory and future strategy improvement

---

## 🛠 Tools Explained

### Research Agent
- **`web_search`** — Tavily semantic search for live market trends, audience signals, and industry news. Results trimmed before injection to preserve context budget.
- **`serper_competitor_lookup`** — Serper Google Search API for real-time competitor positioning and share of voice signals.

### Strategy Agent
- **`get_brand_memory`** — Fetches brand's full memory from MongoDB: past campaign IDs, accumulated insights, and guidelines. Always called first.
- **`get_past_campaigns`** — Retrieves historical campaign records. Lets the agent build on what worked and avoid repeating what didn't.
- **`get_brand_guidelines`** — Loads preferred channels, visual style rules, and hard content restrictions.

### Content Agent
- **`get_brand_guidelines`** — Pulls content restrictions and channel preferences before writing a single word.
- **`get_brand_tone`** — Retrieves the brand's tone of voice, USP, and target audience. Ensures every asset sounds like the brand, not generic AI output.

---

## 📊 LangSmith Trace

<img width="1543" height="901" alt="Langsmith trace v2" src="https://github.com/user-attachments/assets/45edff50-23e5-43ad-a113-876966a53a2b" />

---

## 🛠️ Tech Stack

### Backend
| Technology | Role |
|---|---|
| **LangGraph** | Stateful multi-agent orchestration with conditional routing |
| **FastAPI** | REST API framework, auto-documented via OpenAPI |
| **LangSmith** | Full pipeline tracing and observability |
| **Pydantic v2** | Schema validation across all agent I/O and API requests |
| **MongoDB (PyMongo)** | Brand profiles, campaign history, memory storage |

### AI / LLM
| Technology | Role |
|---|---|
| **OpenAI GPT-4o-mini** | Default agent model (all 5 agents configurable independently) |
| **Anthropic Claude** | Alternate provider, agent-level configurable |
| **Ollama** | Local LLM fallback (llama3.1:8b) — full offline capability |
| **LLMFactory** | Provider-agnostic factory — swap LLMs per agent with one config change |
| **Tavily** | Semantic web search for research agent |
| **Serper** | Google Search API for competitor lookup |

---

## 🔌 API Reference

### Brands
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/brands` | List all brands |
| `POST` | `/brands` | Create brand with memory |
| `GET` | `/brands/{id}` | Get brand + full memory |
| `PUT` | `/brands/{id}` | Update brand context |
| `DELETE` | `/brands/{id}` | Delete brand + memory |

### Campaigns
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/brands/{brand_id}/campaigns` | List brand campaigns |
| `POST` | `/brands/{brand_id}/campaigns/` | **Trigger full AI pipeline** |
| `GET` | `/brands/{brand_id}/campaigns/{id}` | Get campaign with all agent outputs |
| `DELETE` | `/brands/{brand_id}/campaigns/{id}` | Delete campaign |

### Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check |

---

## 📂 Project Structure

```
├── app/
│   ├── main.py                    # FastAPI app, middleware, router registration
│   ├── config.py                  # Agent → provider/model mapping
│   ├── core/
│   │   ├── settings.py            # Pydantic settings (env-driven)
│   │   └── logging.py             # Structured logging setup
│   ├── api/
│   │   ├── routes_brand.py        # CRUD: brands
│   │   ├── routes_campaign.py     # CRUD: campaigns (nested under brands)
│   │   └── routes_analytics.py    # Analytics endpoints
│   ├── agents/
│   │   ├── research_agent.py      # Market research + competitor intel
│   │   ├── strategy_agent.py      # Campaign strategy generation
│   │   ├── content_agent.py       # Multi-channel content writing
│   │   ├── qa_agent.py            # Content quality & compliance review
│   │   └── analytics_agent.py     # Performance forecasting
│   ├── graph/
│   │   ├── builder.py             # LangGraph pipeline definition + conditional routing
│   │   ├── state.py               # CampaignState TypedDict
│   │   └── nodes/                 # One node per agent
│   ├── tools/
│   │   ├── research/              # web_search, serper_competitor_lookup
│   │   ├── strategy/              # get_brand_memory, get_past_campaigns, get_brand_guidelines
│   │   └── content/               # get_brand_guidelines, get_brand_tone
│   ├── services/
│   │   ├── brand_service.py       # Brand business logic
│   │   ├── campaign_service.py    # Campaign orchestration (triggers graph)
│   │   └── llm/
│   │       └── llm_factory.py     # Provider-agnostic LLM factory
│   ├── db/
│   │   ├── mongodb.py             # MongoDB client singleton
│   │   └── repositories/          # brand_repo, campaign_repo, analytics_repo
│   ├── memory/
│   │   └── brand_memory.py        # Brand memory read/write (persistent cross-campaign)
│   └── schemas/                   # Pydantic models: brand, campaign, strategy, content, analytics, qa
├── Frontend/
├── docker/
│   └── docker-compose.yml         # MongoDB + Redis services
├── requirements.txt
└── .env.example
```

---

## 🚀 Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for MongoDB + Redis)

### 1. Start Infrastructure
```bash
docker compose -f docker/docker-compose.yml up -d
```

### 2. Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in API keys
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 3. Frontend
```bash
cd Frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

---

## 🔑 Environment Variables

```bash
# LLM Providers (configure at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434/v1

# Search tools
TAVILY_API_KEY=tvly-...
SERPER_API_KEY=...

# Infrastructure
MONGODB_URI=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379/0

# Observability
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
```

---

## 💡 What Makes This Stand Out

- **End-to-end autonomous pipeline** — not just an LLM wrapper. Real agents with tools, memory, and conditional logic.
- **Production-grade code structure** — repository pattern, service layer, Pydantic schemas throughout, environment-driven config, structured logging.
- **Graceful degradation** — works with OpenAI, Anthropic, or a fully local Ollama stack. Designed for real-world deployment constraints.
- **Agent specialization** — each agent has a distinct system prompt, tool set, and output schema. No monolithic "do everything" prompt.
- **Memory that compounds** — brand memory persists and improves across campaigns, making it genuinely more useful over time.
- **Observable by design** — LangSmith tracing gives full visibility into every LLM call, tool use, and routing decision across the pipeline.

---

*Built with FastAPI · LangGraph · LangChain · React · MongoDB · Docker*
