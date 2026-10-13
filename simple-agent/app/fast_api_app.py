# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
from collections.abc import AsyncIterator

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes

load_dotenv()
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=True,
    lifespan=lifespan,
)
app.title = "simple-agent"
app.description = "API for interacting with the Agent simple-agent"

# Mount custom FreelanceLeadMatch UI with Country, Amount, and Job Type filters
static_dir = os.path.join(AGENT_DIR, "frontend", "static")
if os.path.exists(static_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from app.agent import (
        search_freelance_jobs,
        search_freelancers,
        calculate_project_estimate,
        save_lead,
        fetch_live_market_jobs,
    )

    @app.get("/")
    @app.get("/leads-ui")
    async def serve_leads_ui():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/api/jobs/live-market")
    async def api_live_market_jobs(
        query: str = "",
        remote_only: bool = True,
        limit: int = 5,
    ):
        results = fetch_live_market_jobs(
            query=query if query else None,
            remote_only=remote_only,
            limit=limit,
        )
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
            country=None if country == "All" else country,
            min_amount=None if min_amount == 0 else min_amount,
            max_amount=None if max_amount == 999999.0 else max_amount,
            min_hourly_rate=None if min_hourly_rate == 0 else min_hourly_rate,
            job_type=None if job_type == "All" else job_type,
            category=None if category == "All" else category,
        )
        return JSONResponse({"jobs": results, "count": len(results)})

    @app.get("/api/freelancers")
    async def api_search_freelancers(
        country: str = "All",
        max_hourly_rate: float = 999999.0,
        min_hourly_rate: float = 0.0,
        category: str = "All",
        skill: str = "All",
    ):
        results = search_freelancers(
            country=None if country == "All" else country,
            max_hourly_rate=None if max_hourly_rate == 999999.0 else max_hourly_rate,
            min_hourly_rate=None if min_hourly_rate == 0 else min_hourly_rate,
            category=None if category == "All" else category,
            skill=None if skill == "All" else skill,
        )
        return JSONResponse({"freelancers": results, "count": len(results)})

    import datetime
    import uuid
    from typing import List, Dict, Any
    from pydantic import BaseModel
    from fastapi import WebSocket, WebSocketDisconnect

    class CommunityMessagePayload(BaseModel):
        sender_name: str
        role: str  # "client" or "freelancer"
        text: str
        avatar_initials: str = ""

    # In-memory community chat store
    GLOBAL_COMMUNITY_MESSAGES: List[Dict[str, Any]] = [
        {
            "id": "msg-101",
            "sender_name": "Marcus Vance",
            "role": "client",
            "avatar_initials": "MV",
            "company": "Vance FinTech",
            "text": "Hello everyone! We are looking for an AI Agent Architect to build an autonomous ledger reconciliation engine using Vertex AI and ADK. Budget is $15,000 for a 4-week sprint. Anyone available immediately?",
            "timestamp": 1728800000.0,
            "time_display": "10:15 AM",
        },
        {
            "id": "msg-102",
            "sender_name": "Elena Rostova",
            "role": "freelancer",
            "avatar_initials": "ER",
            "title": "Principal AI Architect",
            "text": "Hi Marcus! That aligns right with what I specialize in. I just architected a multi-agent orchestration pipeline with A2A protocol and tool sandboxes. Would love to review the spec and share benchmarks.",
            "timestamp": 1728800120.0,
            "time_display": "10:17 AM",
        },
        {
            "id": "msg-103",
            "sender_name": "David Hayes",
            "role": "client",
            "avatar_initials": "DH",
            "company": "HealthAI Labs",
            "text": "Quick question for the front-end engineers here: Who has deep experience building sub-50ms responsive design systems with Tailwind and fluid typography?",
            "timestamp": 1728800300.0,
            "time_display": "10:20 AM",
        },
        {
            "id": "msg-104",
            "sender_name": "Sarah Chen",
            "role": "freelancer",
            "avatar_initials": "SC",
            "title": "Staff Front-End & Design Systems",
            "text": "Hi David! I specialize in Apple-quality WCAG AAA design systems. Built them for 3 scaleups with 0.1 CLS and 60fps animations. Feel free to inspect my profile or message me directly!",
            "timestamp": 1728800450.0,
            "time_display": "10:22 AM",
        },
        {
            "id": "msg-105",
            "sender_name": "Liam Thorne",
            "role": "freelancer",
            "avatar_initials": "LT",
            "title": "Lead Cloud & Kubernetes Architect",
            "text": "Any founders running into Vertex AI quota throttling or VPC Service Controls challenges on GKE? Happy to do a quick 20-minute architecture review in the lounge.",
            "timestamp": 1728800600.0,
            "time_display": "10:25 AM",
        }
    ]

    class CommunityConnectionManager:
        def __init__(self):
            self.active_connections: List[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

        async def broadcast(self, message: dict):
            for conn in list(self.active_connections):
                try:
                    await conn.send_json(message)
                except Exception:
                    self.disconnect(conn)

    chat_manager = CommunityConnectionManager()

    @app.get("/api/community/messages")
    async def get_community_messages():
        return JSONResponse({
            "messages": GLOBAL_COMMUNITY_MESSAGES,
            "count": len(GLOBAL_COMMUNITY_MESSAGES),
            "online_count": max(len(chat_manager.active_connections), 1) + 17
        })

    @app.post("/api/community/messages")
    async def post_community_message(payload: CommunityMessagePayload):
        now = datetime.datetime.now()
        initials = payload.avatar_initials.strip()
        if not initials:
            parts = payload.sender_name.strip().split()
            initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else ""))[:2].upper() if parts else "IM"

        msg = {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "sender_name": payload.sender_name.strip() or ("Client Founder" if payload.role == "client" else "Freelance Specialist"),
            "role": payload.role if payload.role in ["client", "freelancer"] else "freelancer",
            "avatar_initials": initials,
            "text": payload.text.strip(),
            "timestamp": now.timestamp(),
            "time_display": now.strftime("%I:%M %p"),
        }
        GLOBAL_COMMUNITY_MESSAGES.append(msg)
        await chat_manager.broadcast({"type": "new_message", "message": msg})
        return JSONResponse({"status": "success", "message": msg})

    @app.websocket("/ws/community")
    async def websocket_community(websocket: WebSocket):
        await chat_manager.connect(websocket)
        try:
            await websocket.send_json({
                "type": "init",
                "messages": GLOBAL_COMMUNITY_MESSAGES,
                "online_count": max(len(chat_manager.active_connections), 1) + 17
            })
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "send_message":
                    raw_text = data.get("text", "").strip()
                    if raw_text:
                        now = datetime.datetime.now()
                        s_name = data.get("sender_name", "").strip() or ("Client Founder" if data.get("role") == "client" else "Freelancer Pro")
                        role = data.get("role", "freelancer")
                        parts = s_name.split()
                        initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else ""))[:2].upper() if parts else "IM"
                        new_msg = {
                            "id": f"msg-{uuid.uuid4().hex[:8]}",
                            "sender_name": s_name,
                            "role": role if role in ["client", "freelancer"] else "freelancer",
                            "avatar_initials": initials,
                            "text": raw_text,
                            "timestamp": now.timestamp(),
                            "time_display": now.strftime("%I:%M %p"),
                        }
                        GLOBAL_COMMUNITY_MESSAGES.append(new_msg)
                        await chat_manager.broadcast({"type": "new_message", "message": new_msg})
        except WebSocketDisconnect:
            chat_manager.disconnect(websocket)
        except Exception:
            chat_manager.disconnect(websocket)

    app.mount("/static", StaticFiles(directory=static_dir), name="custom_static")


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


