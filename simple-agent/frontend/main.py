"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

def _load_resource() -> str:
    if "AGENT_ENGINE_RESOURCE_NAME" in os.environ:
        return os.environ["AGENT_ENGINE_RESOURCE_NAME"]
    meta_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "deployment_metadata.json",
    )
    if os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                return json.load(f).get("remote_agent_runtime_id", "")
        except Exception:
            pass
    return "projects/830911902525/locations/us-east1/reasoningEngines/1859050961708777472"


RESOURCE = _load_resource()
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        # Agent Runtime does not serve a public card URL, so point the client at
        # the passthrough base for message sends.
        card.url = A2A_BASE
        for iface in getattr(card, "additional_interfaces", []) or []:
            iface.url = A2A_BASE
        _card = card
    return _card


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI.

    Text parts pass through as {"kind": "text"}. A2UI data parts (tagged
    application/json+a2ui) become {"kind": "a2ui", "data": <message>} so the UI
    renders the card; each data part is one A2UI message (beginRendering or
    surfaceUpdate).
    """
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            raw_data = root.data
            meta = getattr(root, "metadata", None) or {}
            if isinstance(raw_data, dict) and "metadata" in raw_data and not meta:
                meta = raw_data.get("metadata") or {}
                if "data" in raw_data:
                    raw_data = raw_data.get("data")
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": raw_data})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        # Non-streaming fallback: pull parts from the final task's artifacts.
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        # The turn produced no text or UI (e.g. the agent only ran tools, or a
        # tool stalled). Be honest rather than silent.
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# -----------------------------------------------------------------------------
# IndieMatch REST & WebSocket Endpoints (Matching UI & Live Market API)
# -----------------------------------------------------------------------------
import sys
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

_this_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_this_dir)
for p in [_this_dir, _parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.data_tools import (
        search_freelance_jobs,
        search_freelancers,
        calculate_project_estimate,
        save_lead,
        fetch_live_market_jobs,
        GLOBAL_JOBS,
        FREELANCERS,
    )
except Exception:
    try:
        from data_tools import (
            search_freelance_jobs,
            search_freelancers,
            calculate_project_estimate,
            save_lead,
            fetch_live_market_jobs,
            GLOBAL_JOBS,
            FREELANCERS,
        )
    except Exception as e:
        print(f"Warning importing data_tools: {e}")
        search_freelance_jobs = lambda **kw: []
        search_freelancers = lambda **kw: []
        fetch_live_market_jobs = lambda **kw: []
        GLOBAL_JOBS = []
        FREELANCERS = []

COMMUNITY_MESSAGES = [
    {
        "id": "msg-1",
        "sender": "Elena Rostova",
        "role": "Freelancer",
        "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
        "text": "Just closed a high-ticket contract through IndieMatch! Clients here appreciate quality craftsmanship.",
        "timestamp": "10:14 AM",
    },
    {
        "id": "msg-2",
        "sender": "David Vance",
        "role": "Client",
        "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
        "text": "Hiring 2 senior engineers for our Gemini 1.5 Pro migration project. Check my active contract listing!",
        "timestamp": "10:18 AM",
    },
    {
        "id": "msg-3",
        "sender": "Kenji Takahashi",
        "role": "Freelancer",
        "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
        "text": "Excited to be on IndieMatch. The real-time leads concierge makes sourcing contracts effortless.",
        "timestamp": "10:22 AM",
    },
]

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

class ChatMessageIn(BaseModel):
    sender: str
    role: str
    text: str
    avatar: str | None = None

@app.get("/api/jobs/live-market")
async def api_live_market_jobs(query: str = "", remote_only: bool = True, limit: int = 5):
    results = fetch_live_market_jobs(query=query if query else None, remote_only=remote_only, limit=limit)
    return JSONResponse({"jobs": results, "count": len(results), "source": "Arbeitnow Public API"})

@app.get("/api/jobs")
async def api_search_jobs(
    country: str = "All",
    min_amount: float = 0.0,
    max_amount: float = 999999.0,
    min_hourly_rate: float = 0.0,
    job_type: str = "All",
    category: str = "All",
):
    results = search_freelance_jobs(
        country=country,
        min_amount=min_amount,
        max_amount=max_amount,
        min_hourly_rate=min_hourly_rate,
        job_type=job_type,
        category=category,
    )
    return JSONResponse({"jobs": results, "count": len(results), "total_available": len(GLOBAL_JOBS)})

@app.get("/api/freelancers")
async def api_search_freelancers(
    country: str = "All",
    max_hourly_rate: float = 999999.0,
    min_hourly_rate: float = 0.0,
    category: str = "All",
    skill: str = "All",
):
    results = search_freelancers(
        country=country,
        max_hourly_rate=max_hourly_rate,
        min_hourly_rate=min_hourly_rate,
        category=category,
        skill=skill,
    )
    return JSONResponse({"freelancers": results, "count": len(results), "total_available": len(FREELANCERS)})

@app.get("/api/community/messages")
async def get_community_messages():
    return JSONResponse({"messages": COMMUNITY_MESSAGES})

@app.post("/api/community/send")
async def send_community_message(payload: ChatMessageIn):
    now_str = datetime.datetime.now().strftime("%I:%M %p")
    msg_id = f"msg-{len(COMMUNITY_MESSAGES) + 1}-{uuid.uuid4().hex[:4]}"
    avatar = payload.avatar or (
        "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80"
        if payload.role.lower() == "freelancer"
        else "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=150&auto=format&fit=crop&q=80"
    )
    new_msg = {
        "id": msg_id,
        "sender": payload.sender,
        "role": payload.role,
        "avatar": avatar,
        "text": payload.text,
        "timestamp": now_str,
    }
    COMMUNITY_MESSAGES.append(new_msg)
    await manager.broadcast({"type": "new_message", "message": new_msg})
    return JSONResponse({"status": "success", "message": new_msg})

@app.websocket("/ws/community")
async def websocket_community(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "history", "messages": COMMUNITY_MESSAGES})
        while True:
            data = await websocket.receive_json()
            sender = data.get("sender", "Anonymous")
            role = data.get("role", "Member")
            text = data.get("text", "")
            avatar = data.get("avatar") or (
                "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80"
                if role.lower() == "freelancer"
                else "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=150&auto=format&fit=crop&q=80"
            )
            now_str = datetime.datetime.now().strftime("%I:%M %p")
            msg_id = f"msg-{len(COMMUNITY_MESSAGES) + 1}-{uuid.uuid4().hex[:4]}"
            new_msg = {
                "id": msg_id,
                "sender": sender,
                "role": role,
                "avatar": avatar,
                "text": text,
                "timestamp": now_str,
            }
            COMMUNITY_MESSAGES.append(new_msg)
            await manager.broadcast({"type": "new_message", "message": new_msg})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
