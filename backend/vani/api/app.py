"""FastAPI app.   uvicorn vani.api.app:app --port 8000   (from backend/)"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from vani.config import REPO_ROOT, Settings, get_settings
from vani.domain.live import CallStatus, Channel
from vani.integrations.sarvam.client import SarvamError
from vani.persona.distinct import distance, most_distinct
from vani.persona.prompt import agent_variables, system_prompt
from vani.runtime.service import CallClosed, NotFound, TurnResult

from .deps import Container
from .schemas import AgentEnd, AgentStart, AgentTurn, BatchPersonas, EndCall, StartCall, TTSRequest

log = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 5 * 1024 * 1024
WEB_DIR = REPO_ROOT / "web"


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.c = container or Container.build(settings or get_settings())
        yield
        speech = app.state.c.speech
        if hasattr(speech, "aclose"):
            await speech.aclose()

    app = FastAPI(title="VANI Persona Engine", version="1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(NotFound)
    async def _nf(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(CallClosed)
    async def _closed(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def _bad(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(SarvamError)
    async def _sarvam(_, exc):
        return JSONResponse({"detail": f"Sarvam: {exc}"}, status_code=502)

    def c(request: Request) -> Container:
        return request.app.state.c

    v1 = "/api/v1"

    # ------------------------------------------------------------- system
    @app.get(f"{v1}/health")
    def health(ct: Container = Depends(c)):
        return {"status": "ok", "mode": "live" if ct.speech.enabled else "offline",
                "models": {"stt": ct.settings.sarvam_stt_model, "tts": ct.settings.sarvam_tts_model,
                           "llm": ct.settings.sarvam_chat_model},
                "evidence_findings": len(ct.evidence), "evidence_baseline": ct.evidence.baseline}

    # ------------------------------------------------------------ sellers
    @app.get(f"{v1}/sellers")
    def sellers(state: str | None = None, business_kind: str | None = None, with_transcripts: bool | None = None,
                limit: int = Query(20, ge=1, le=200), ct: Container = Depends(c)):
        return [_seller_summary(p) for p in ct.repo.search(state=state, business_kind=business_kind,
                                                           with_transcripts=with_transcripts, limit=limit)]

    @app.get(f"{v1}/sellers/{{glid}}")
    def seller(glid: str, ct: Container = Depends(c)):
        ctx = ct.repo.get_context(glid)
        if ctx is None:
            raise NotFound(f"seller {glid} not found")
        return {"profile": ctx.profile.model_dump(mode="json"),
                "calls": [x.model_dump(mode="json") for x in ctx.calls],
                "turns": len(ctx.turns)}

    @app.get(f"{v1}/sellers/{{glid}}/persona")
    def persona(glid: str, voice_gender: str | None = Query(None, pattern="^(male|female)$"), ct: Container = Depends(c)):
        p, profile = ct.calls.persona_for(glid, voice_gender)
        return {"persona": p.model_dump(mode="json"), "system_prompt": system_prompt(p, profile),
                "agent_variables": agent_variables(p, profile)}

    @app.post(f"{v1}/personas/batch")
    def personas(body: BatchPersonas, ct: Container = Depends(c)):
        out = []
        for g in body.seller_glids:
            try:
                out.append(ct.calls.persona_for(g)[0].model_dump(mode="json"))
            except NotFound:
                out.append({"seller_glid": g, "error": "not found"})
        return out

    @app.get(f"{v1}/demo-sellers")
    def demo_sellers(k: int = Query(3, ge=2, le=5), pool: int = Query(150, ge=5, le=1000), ct: Container = Depends(c)):
        """The k most contrasting sellers (with call history) for a side-by-side voice demo."""
        key = (k, pool)
        cache = ct.__dict__.setdefault("_demo_cache", {})
        if key not in cache:
            profiles = {p.glid: p for p in ct.repo.search(with_transcripts=True, limit=pool)}
            personas = [ct.calls.persona_for(g)[0] for g in profiles]
            chosen, min_d = most_distinct(personas, k)
            cache[key] = {
                "min_pairwise_distance": min_d,
                "pairwise": [[distance(a, b) for b in chosen] for a in chosen],
                "sellers": [{**_seller_summary(profiles[p.seller_glid]), "persona": p.model_dump(mode="json")}
                            for p in chosen],
            }
        return cache[key]

    # ----------------------------------------------------------- evidence
    @app.get(f"{v1}/evidence")
    def evidence(min_strength: str = Query("moderate", pattern="^(weak|moderate|strong)$"), kind: str | None = None,
                 ct: Container = Depends(c)):
        rank = {"weak": 1, "moderate": 2, "strong": 3}
        fs = [f for f in ct.evidence.raw.get("findings", []) if rank[f["strength"]] >= rank[min_strength]
              and (kind is None or f["kind"] == kind)]
        return {"baseline": ct.evidence.baseline, "caveats": ct.evidence.caveats, "findings": fs}

    @app.get(f"{v1}/evidence/{{fid}}")
    def finding(fid: str, ct: Container = Depends(c)):
        f = ct.evidence.get(fid)
        if not f:
            raise NotFound(f"finding {fid} not found")
        return f

    # -------------------------------------------------------------- calls
    @app.post(f"{v1}/calls", status_code=201)
    async def start_call(body: StartCall, ct: Container = Depends(c)):
        s, bot = await ct.calls.start(body.seller_glid, body.channel, voice_gender=body.voice_gender)
        return {"session_id": s.session_id, "persona": s.persona.model_dump(mode="json"), "bot": bot.__dict__,
                "mode": "live" if ct.speech.enabled else "offline"}

    @app.post(f"{v1}/calls/{{sid}}/turns")
    async def turn(sid: str, text: str | None = Form(None), audio: UploadFile | None = File(None),
                   ct: Container = Depends(c)):
        raw = None
        if audio is not None:
            raw = await audio.read()
            if len(raw) > MAX_AUDIO_BYTES:
                raise HTTPException(413, "audio too large (max 5 MB per turn)")
            if not ct.speech.enabled:
                raise HTTPException(400, "audio needs SARVAM_API_KEY; offline mode accepts text")
        return _turn_json(await ct.calls.seller_turn(sid, text=text, audio=raw))

    @app.post(f"{v1}/calls/{{sid}}/end")
    def end_call(sid: str, body: EndCall | None = None, ct: Container = Depends(c)):
        s = ct.calls.end(sid, body.outcome if body else None)
        return {"session_id": s.session_id, "status": s.status.value, "outcome": s.outcome.value}

    @app.get(f"{v1}/calls/{{sid}}")
    def get_call(sid: str, ct: Container = Depends(c)):
        s = ct.store.get(sid)
        if s is None:
            raise NotFound(f"session {sid} not found")
        return s.model_dump(mode="json")

    @app.get(f"{v1}/calls")
    def list_calls(limit: int = Query(50, ge=1, le=500), ct: Container = Depends(c)):
        return ct.store.list_sessions(limit)

    @app.get(f"{v1}/switch-log")
    def switch_log(seller_glid: str | None = None, limit: int = Query(200, ge=1, le=2000), ct: Container = Depends(c)):
        return [e.model_dump(mode="json") for e in ct.store.switch_log(seller_glid, limit)]

    @app.post(f"{v1}/tts")
    async def tts(body: TTSRequest, ct: Container = Depends(c)):
        """Speak a line in a given persona voice (Compare view). Offline: audio_b64 is null, browser speaks."""
        if not ct.speech.enabled:
            return {"audio_b64": None, "mode": "offline"}
        audio = await ct.speech.tts(body.text, body.language_code, body.speaker, body.pace, body.pitch, body.temperature)
        return {"audio_b64": audio, "mode": "live"}

    # ------------------------------------------------- Sarvam agent tools
    def tool_auth(x_tool_secret: str | None = Header(None), ct: Container = Depends(c)):
        if x_tool_secret != ct.settings.agent_tool_secret:
            raise HTTPException(401, "bad or missing X-Tool-Secret")

    @app.post(f"{v1}/agent-tools/start_call", dependencies=[Depends(tool_auth)])
    async def agent_start(body: AgentStart, ct: Container = Depends(c)):
        s, bot = await ct.calls.start(body.seller_glid, Channel.sarvam_agent, speak=False, voice_gender=body.voice_gender)
        return {"session_id": s.session_id, **ct.calls.agent_directives(s)}

    @app.post(f"{v1}/agent-tools/analyze_turn", dependencies=[Depends(tool_auth)])
    async def agent_turn(body: AgentTurn, ct: Container = Depends(c)):
        r = await ct.calls.seller_turn(body.session_id, text=body.seller_utterance, speak=False)
        d = ct.calls.agent_directives(r.session, r.move)
        last = r.switches[-1] if r.switches else None
        return {**d, "switched": bool(r.switches),
                "switch_signal": last.signal.value if last else "",
                "switch_reason": last.reason if last else "",
                "suggested_reply": r.bot.text,
                "end_call": r.session.status == CallStatus.ended,
                "outcome": r.session.outcome.value}

    @app.post(f"{v1}/agent-tools/end_call", dependencies=[Depends(tool_auth)])
    def agent_end(body: AgentEnd, ct: Container = Depends(c)):
        s = ct.calls.end(body.session_id, body.outcome)
        return {"session_id": s.session_id, "outcome": s.outcome.value, "switches": len(s.switch_log)}

    if WEB_DIR.exists():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(WEB_DIR / "index.html")

    return app


def _seller_summary(p) -> dict:
    return {"glid": p.glid, "company_name": p.company_name, "city": p.city, "state": p.state,
            "business_kind": p.business_kind.value, "turnover": p.turnover_raw, "language_code": p.language_code,
            "bot_answered": p.bot_history.answered, "missing_fields": p.missing_fields}


def _turn_json(r: TurnResult) -> dict:
    s = r.session
    return {"session_id": s.session_id, "seller_text": r.seller_text,
            "signals": [x.model_dump(mode="json") for x in r.signals],
            "switches": [x.model_dump(mode="json") for x in r.switches],
            "persona": s.persona.model_dump(mode="json"), "bot": r.bot.__dict__, "move": r.move,
            "stage": s.stage, "status": s.status.value, "outcome": s.outcome.value,
            "meeting_slot": s.meeting_slot, "warnings": r.warnings}


app = create_app()
