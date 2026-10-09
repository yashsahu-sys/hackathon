"""FastAPI server. Run: uvicorn app.main:app --reload --port 8000"""
import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config
from .conversation import Session
from .evidence import EvidenceStore
from .persona import generate_persona, system_prompt
from .sarvam import SarvamClient, SarvamError

app = FastAPI(title="Persona Generator for IndiaMART Voice Bot")
evidence = EvidenceStore.load()
client = SarvamClient() if config.LIVE else None
sessions: dict[str, Session] = {}


def _sellers() -> dict:
    out = {}
    for folder in (config.DATA / "sellers", config.DATA / "private" / "sellers"):
        for path in sorted(folder.glob("*.json")) if folder.exists() else []:
            s = json.loads(path.read_text())
            out[s["seller_id"]] = s
    return out


class SellerRequest(BaseModel):
    seller_id: str | None = None
    seller: dict | None = None


def _resolve(req: SellerRequest) -> dict:
    if req.seller:
        missing = {"seller_id", "name"} - set(req.seller)
        if missing:
            raise HTTPException(400, f"seller JSON missing {sorted(missing)}")
        return req.seller
    seller = _sellers().get(req.seller_id or "")
    if not seller:
        raise HTTPException(404, f"unknown seller {req.seller_id}")
    return seller


def _public(persona: dict) -> dict:
    return {k: v for k, v in persona.items() if not k.startswith("_")}


@app.get("/")
def index():
    return FileResponse(config.ROOT / "web" / "index.html")


@app.get("/api/health")
def health():
    return {"mode": "live" if config.LIVE else "offline", "chat_model": config.CHAT_MODEL,
            "stt_model": config.STT_MODEL, "tts_model": config.TTS_MODEL,
            "evidence_calls": len(evidence.calls), "evidence_synthetic": evidence.synthetic}


@app.get("/api/sellers")
def sellers():
    return list(_sellers().values())


@app.post("/api/persona")
def persona(req: SellerRequest):
    seller = _resolve(req)
    p = generate_persona(seller, evidence)
    return {"persona": _public(p), "system_prompt": system_prompt(p, seller)}


@app.post("/api/session")
def start(req: SellerRequest):
    session = Session(_resolve(req), evidence, client)
    sessions[session.id] = session
    bot = session.open()
    return {"session_id": session.id, "persona": session._snapshot(), "bot": bot,
            "system_prompt": system_prompt(session.persona, session.seller), "mode": "live" if session.live else "offline"}


@app.post("/api/session/{sid}/turn")
async def turn(sid: str, text: str | None = Form(None), audio: UploadFile | None = File(None)):
    session = sessions.get(sid)
    if not session:
        raise HTTPException(404, "session not found")
    stt_language = None
    if audio is not None:
        if not session.live:
            raise HTTPException(400, "audio needs SARVAM_API_KEY; offline mode takes typed/browser-recognised text")
        try:
            stt = session.transcribe(await audio.read())
        except SarvamError as exc:
            raise HTTPException(502, f"speech-to-text failed: {exc}")
        text, stt_language = stt["transcript"], stt.get("language_code")
    if not text or not text.strip():
        raise HTTPException(400, "nothing heard, try again")
    return session.seller_turn(text.strip(), stt_language)


@app.get("/api/session/{sid}")
def summary(sid: str):
    session = sessions.get(sid)
    if not session:
        raise HTTPException(404, "session not found")
    return session.summary()
