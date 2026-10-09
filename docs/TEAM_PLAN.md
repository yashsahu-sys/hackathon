# Team plan: kaun kya karega

Code ka 80% ready hai (persona generator, live switch, switch log, UI, tests). Aaj ka kaam: **Sarvam se jodna, real data lagana, aawaz tune karna, demo pakka karna.**

## Roles

### A: Tech lead (Yash)
| # | Kaam | Kab tak |
|---|---|---|
| A1 | Laptop pe repo clone, `pip install -r requirements.txt`, `python -m uvicorn app.main:app --port 8000`, browser me `localhost:8000` khol ke offline mode check | 11:00 |
| A2 | Sarvam key `.env` me daalo, top-right badge **LIVE** dikhna chahiye. Ek call karke suno: aawaz aayi? mic chala? | 11:45 |
| A3 | Organisers se real seller data + past call data ka **format** lo. Column names Claude ko bhejo (data rows nahi!), converter likhwao | 1:00 |
| A4 | Real data `data/private/` me daalo, `python scripts/backtest.py` chalao, **asli lift number** nikaalo | 3:30 |
| A5 | Sarvam dashboard pe Agent banao: `samples/personas/S101_system_prompt.txt` paste karo, **Agent ID** note karo (submission me chahiye) | Day 2, 12:00 |

### B: Second tech member
| # | Kaam | Kab tak |
|---|---|---|
| B1 | Setup same as A1 apne laptop pe | 11:00 |
| B2 | Mic se 20+ alag lines bolo (gussa, confusion, busy, English switch). Jo line pakdi nahi gayi, list banao, Claude se `app/signals.py` me add karwao | 1:00 |
| B3 | **Aawaz tune karo**: Bulbul v3 ke voices sun ke `app/persona.py` me `VOICE_MAP` set karo (casual / neutral / formal ke liye best male + female) | 3:30 |
| B4 | Latency check: har turn kitne second? 3s se zyada ho to bolo | 5:00 |

### C: Non-tech member (score ka ~40% inke haath me hai)
| # | Kaam | Kab tak |
|---|---|---|
| C1 | `docs/DEMO_SCRIPT.md` padho, 3 seller roles practice karo (Rohit, Senthil, Mehta) | 1:00 |
| C2 | Business impact slide: "abhi kitne calls me meeting fix hoti hai" organisers/NHD team se poocho. Ye number + backtest lift = humari story | 3:30 |
| C3 | `skills.md` me "Day log" bharte raho: kya try kiya, kya toota, kya badla | poora din |
| C4 | Day 2: demo video record (5-7 min), screen + aawaz dono | Day 2, 12:30 |

## Timeline

**Day 1 (aaj)**
- 10:30 to 12:00: A1-A2, B1, C1. **Pehle aawaz aani chahiye, baaki sab baad me.**
- 1:00 to 3:30: real data (A3-A4), signals testing (B2), impact numbers (C2)
- **3:30 mentor check-in.** Sarvam walon se poocho: (1) Bulbul v3 me sabse natural Hinglish voice kaunsi? (2) Agent ID kaise milega submission ke liye? (3) STT latency kam karne ka tareeka?
- 3:30 to 6:00: voice tuning (B3), bugs fix, pehla full rehearsal
- 6:00 stand-up: **target = live mode me 3 sellers ki call + ek mid-call switch kaam kar raha ho**

**Day 2**
- 10:00 to 11:30: polish only, naya feature nahi
- **11:30: CODE FREEZE**
- 11:30 to 12:30: 2 rehearsal
- 12:30 to 2:00: video record, README/skills.md final, `python scripts/run_demo.py` se samples refresh
- **2:00 submission window khulte hi submit karo.** Baad me chahe to improve karte raho.

## Rules jo yaad rakhne hain
- Real customer data **kabhi** GitHub pe ya chat me mat daalo. Sirf `data/private/` (gitignored).
- Demo me koi bhi number bolo to batao ki real data pe hai ya synthetic pe. Synthetic ko asli result mat bolna.
- Network gaya to: `.env` se key hata ke restart karo, offline mode me demo chalega.
