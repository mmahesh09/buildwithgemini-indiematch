# IndieMatch — Autonomous Freelance Marketplace Concierge

An agent-first freelance marketplace and autonomous matchmaking concierge built on the **Google Agent Development Kit (ADK)** and powered by **Gemini 2.5 Flash**.

IndieMatch connects verified independent talent with founders and businesses. The autonomous concierge handles talent matching, contract search, real-time live market inquiries via the Arbeitnow public API, project scoping, and cost estimations, rendering results as rich, interactive **A2UI** cards.

![IndieMatch Autonomous Agent Demo](assets/demo.gif)

---

## 🌟 What the Agent Does

IndieMatch operates as an intelligent matchmaking concierge for both clients and freelancers:

- **Client Talent Matching**: Evaluates verified specialist profiles (AI/ML architects, cloud engineers, design leads, full-stack developers) filtered by domain, hourly rate ceiling, and technical skills.
- **Contract & Job Search**: Surfaces verified client contracts with filters for budget minimums, hourly compensation, contract duration, and remote scope.
- **Live Job Market Inquiries**: Calls the free public **Arbeitnow API** in real time to fetch open remote job listings across tech, engineering, and product roles.
- **Project Scoping & Cost Estimation**: Automatically calculates billable hours, complexity adjustments (1.0x to 2.0x), sprint urgency tiers (standard vs. expedited), and estimated delivery timelines.
- **Lead Qualification & CRM**: Captures client project requirements and stores qualified leads for intake and follow-up.
- **Agent-First UI (A2UI)**: Formats agent recommendations as native A2UI cards (`Card`, `Column`, `Row`, and `Text` hierarchy) rather than plain unstructured text.

---

## 🛠️ Architecture & Google Cloud Integration

The agent is built with **Google ADK** and structured according to `agents-cli-manifest.yaml`:

| Component | Implementation | Status |
| :--- | :--- | :--- |
| **Reasoning Model** | `Gemini 2.5 Flash` (`gemini-3.8-flash`) via `google.adk.models.Gemini` | Wired & Active |
| **Agent Framework** | Google Agent Development Kit (`google-adk`) | Wired & Active |
| **A2UI Protocol** | A2UI v0.8 specification via `after_model_callback=a2ui_callback` | Wired & Active |
| **A2A Protocol** | Agent-to-Agent protocol endpoints (`/a2a/app`, `.well-known/agent-card.json`) | Wired & Active |
| **Session Service** | In-Memory Session Service (`InMemorySessionService`) | Wired & Active |
| **Artifact Service** | In-Memory / Cloud Storage (`GcsArtifactService` via `LOGS_BUCKET_NAME`) | Configurable |
| **Web & Proxy Server** | FastAPI application with real-time WebSocket Community Lounge | Wired & Active |

### 🔧 Wired Agent Tools (`app/agent.py`)

1. `search_freelance_jobs`: Searches curated platform contracts by country, budget, hourly rate, and category.
2. `search_freelancers`: Searches verified freelancer profiles by hourly rate, country, category, and skill keyword.
3. `fetch_live_market_jobs`: Connects to the public **Arbeitnow Job Board API** to query real-world remote positions.
4. `calculate_project_estimate`: Scoping calculator for billable hours, complexity multipliers, urgency surcharges, and timelines.
5. `save_lead`: In-memory qualification tracker for client opportunities.

---

## 📋 Planned Capabilities (Not Yet Implemented)

The following features from `project_brief.md` are roadmap items and not currently implemented in the codebase:

- **Vertex AI Memory Bank**: *Planned, not yet implemented.* The agent currently uses in-memory session state.
- **AI Image Generation**: *Planned, not yet implemented.* Generating personalized project roadmaps or welcome quote badges with Gemini image models.
- **External Database (Firestore)**: *Planned, not yet implemented.* Leads and contracts are managed in-memory.
- **Google Calendar / Sheets Integration**: *Planned, not yet implemented.* Automated intro call scheduling and CRM spreadsheet export.

---

## 🚀 Local Setup & Run Instructions

### Prerequisites
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- Google Cloud SDK (`gcloud`) with Vertex AI API enabled

### 1. Clone & Install Dependencies

```bash
git clone <your-repo-url>
cd simple-agent

# Install dependencies using uv
uv sync
```

### 2. Configure Environment

Copy the example environment file and set your Google Cloud project details:

```bash
cp .env.example .env
```

Ensure your environment has authentication configured:

```bash
gcloud auth application-default login
```

### 3. Run the Agent Locally

You can run the agent locally through any of the following surfaces:

#### Option A: ADK Web Playground
Launch the local ADK developer playground with live reload:

```bash
uv run agents-cli playground
```

#### Option B: Standalone FastAPI Backend
Start the local FastAPI server hosting the A2A endpoints and chat interface:

```bash
uv run python app/fast_api_app.py
```

#### Option C: Full-Stack Frontend & Community Lounge
Run the full-stack web application with the A2A proxy and WebSocket lounge:

```bash
uv run python frontend/main.py
```

---

## 🧪 Testing

Run unit and integration test suites:

```bash
uv run pytest tests/unit tests/integration
```

---

## 📄 License

Apache License 2.0. Copyright 2026 Google LLC.
