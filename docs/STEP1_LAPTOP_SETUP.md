# Step 1: Laptop setup (about 15 minutes)

Goal: code chal jaaye, real data load ho jaaye, aur Sarvam key teeno APIs (STT, TTS, LLM) pe kaam kare.

Commands for **Windows** (Command Prompt / PowerShell) and **Mac/Linux** are given side by side.

---

## 1.1 Check Python and Git

```
python --version        (Windows: if this fails, try  py --version)
git --version
```

- Python **3.10 or newer** chahiye. Nahi hai toh python.org se install karo, aur installer me **"Add Python to PATH"** tick karna.
- Git nahi hai toh git-scm.com se install karo.

## 1.2 Get the code

```
git clone https://github.com/yashsahu-sys/hackathon.git
cd hackathon
git checkout claude/happy-hypatia-1z0cqw
```

## 1.3 Create a virtual environment and install packages

Windows:
```
python -m venv .venv
.venv\Scripts\activate
cd backend
pip install -r requirements.txt
```

Mac/Linux:
```
python3 -m venv .venv
source .venv/bin/activate
cd backend
pip install -r requirements.txt
```

Prompt ke aage `(.venv)` dikhna chahiye. **Har naye terminal me activate dobara karna padega.**

If `pip install` fails behind the office proxy:
```
pip install -r requirements.txt --proxy http://<proxy-host>:<port>
```
(Proxy address IT team / browser settings se milega.)

## 1.4 Create the .env file

Still inside `backend/`:

Windows: `copy .env.example .env`, then `notepad .env`
Mac/Linux: `cp .env.example .env`, then `nano .env` (or open it in VS Code)

Fill these two lines and save:
```
SARVAM_API_KEY=sk_...your key...
AGENT_TOOL_SECRET=vani-hackathon-tools
```
Baaki lines waise hi rehne do. `.env` git me nahi jaati, isliye key safe hai.

## 1.5 Put the data in place

1. Drive folder se **"Global Context - Seller Dataset.zip"** download karo.
2. Unzip karo.
3. Repo me ye folder banao (agar nahi hai): `hackathon/data/private/raw/gc/`
4. CSV files **seedha usi folder me** daalo, kisi sub-folder me nahi:

```
hackathon/
  data/private/raw/gc/
    gc_seller_profile.csv      <- required
    gc_bot_calls.csv           <- required
    gc_bot_call_turns.csv      <- needed for transcripts
    gc_executive_calls.csv
    (other gc_*.csv files can stay, they're ignored)
```

Check (from `backend/`):
- Windows: `dir ..\data\private\raw\gc`
- Mac/Linux: `ls ../data/private/raw/gc`

`data/private/` is gitignored: customer data never goes to GitHub.

## 1.6 Run the doctor

From `backend/`:
```
python -m vani.tools.doctor
```
Har line `[ OK ]` honi chahiye, sirf "warehouse built" aur "evidence mined" abhi `[FAIL]` honge (next step me banenge). Koi aur `[FAIL]` ho toh uske neeche likha fix karo.

## 1.7 Build the warehouse and mine the evidence

```
python -m vani.data.warehouse
python -m vani.evidence.miner
```

Expected output:
```
{'seller_profile': 5000, 'bot_calls': 9657, 'bot_call_turns': 4920, 'executive_calls': 2580}
140 findings, 26 strong/moderate -> ...data/private/evidence.json
```
Doosra command ~5 second leta hai. Ab `python -m vani.tools.doctor` chalao: sab `[ OK ]` aana chahiye.

## 1.8 Sarvam smoke test (most important)

```
python -m vani.tools.smoke
```

Expected:
```
TTS  ok  bulbul:v3  ... KB  0.8s
STT  ok  saaras:v3  1.1s  -> 'नमस्ते जी, मैं IndiaMART से पायल बोल रही हूँ ...' (hi-IN)
LLM  ok  sarvam-105b  1.5s  -> '...'
```

Phir `hackathon/data/private/out/smoke_tts.wav` kholke **suno**: Payal ki aawaz me Hindi line aani chahiye.

| What you see | What it means | Fix |
|---|---|---|
| `-> network: can't reach api.sarvam.ai` | Office network/VPN Sarvam block kar raha hai | Mobile hotspot pe try karo, ya IT se `api.sarvam.ai` allow karwao |
| `-> key rejected` (401/403) | Key galat ya expired | dashboard.sarvam.ai se key dobara copy karo |
| `-> request/model rejected` (400/404) | Model ka naam aapke account pe nahi hai | `.env` me model badlo, jaise `SARVAM_CHAT_MODEL=sarvam-m` |
| `-> rate limited / out of credits` (429) | Credits khatam | Sarvam team se baat karo |
| `UnicodeEncodeError` | Purana code | `git pull`, ye fix ho chuka hai |

## 1.9 Run the tests

```
python -m pytest -q
```
Expected: `... passed` (about 1 minute; real-data tests run because the data is present). Koi `failed` aaye toh output mujhe bhejo.

## 1.10 Start the server

```
python -m uvicorn vani.api.app:app --port 8000
```
Browser me kholo: **http://localhost:8000/docs**. Saari APIs yahan try kar sakte ho:
- `GET /api/v1/health` → `"mode": "live"` hona chahiye (key sahi hai toh)
- `GET /api/v1/sellers?with_transcripts=true` → koi glid copy karo
- `GET /api/v1/sellers/{glid}/persona` → us seller ka persona, har field ke reason ke saath

Server band karna: terminal me `Ctrl + C`.

---

## Mujhe wapas kya bhejna hai

1. `python -m vani.tools.smoke` ka **poora output**
2. `python -m pytest -q` ki **last line**
3. `smoke_tts.wav` ki aawaz theek lagi ya nahi (ek line)

**Kabhi mat bhejna:** asli CSV ka data / rows. Sirf errors aur output.
