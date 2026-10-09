# Demo script (5-7 min)

Screen: `localhost:8000`. Ek member laptop chalata hai, non-tech member **seller ka role** karta hai (mic pe bolta hai).

## 0:00 to 0:30: Problem
> "Aaj Voice Bot har seller se ek hi aawaz, ek hi style me baat karta hai. Delhi ka 27 saal ka trader aur Coimbatore ka 58 saal ka manufacturer, dono ko same treatment. Meetings fix nahi hoti."

## 0:30 to 1:30: Generator (sabse important line yahan bolo)
> "Humne personas nahi likhe. Humne woh system banaya jo personas likhta hai, aur call ke beech unhe badalta bhi hai."

- Dropdown me **Rohit Malhotra** chuno → **Generate persona**
- Persona card dikhao: "Quick · Hinglish · Straight-to-the-point"
- Do "why" line padho: "Hinglish ne North me 46% meetings fix ki, aaj ke Hindi bot ki 31%" aur "pichli call 38 second me kaati thi, isliye chhota opening"
- **Senthil** chuno → "Patient · English · Formal". Bolo: "South me data regional language kehta hai, par Senthil ji ne pichli call me khud English maangi thi, seller ki apni history jeet ti hai"
- Agar jury ka koi member ho: **Custom** button → naya seller JSON paste → generate. (Unseen seller = sabse strong proof)

## 1:30 to 3:30: Do alag calls, same goal
**Call 1: Rohit** (Start call)
- Seller: "Haan bolo"
- Bot fast Hinglish me pitch karega

**Call 2: Senthil** (Start call)
- Seller: "Yes, tell me"
- Bot slow, formal English. **Farak sunao.**

## 3:30 to 5:00: The money shot 🎯
**Call 3: Harish Mehta** (Start call)
- Seller: "Haan bolo"
- Seller (gusse me): **"Yaar point pe aao, kitni der se bol rahe ho!"**
  → Right side **switch log** me FRUSTRATION card aayega: pace 1.0→1.15, sentences chhote, strategy direct
  → Bot ki aawaz tez aur seedhi ho jaayegi. **2 second ruko, jury ko sunne do.**
- Seller: **"Sorry, can you speak in English please"**
  → LANGUAGE SWITCH card, bot English me aa jaayega
- Seller: "Yes okay, 11 AM tomorrow works"
  → ✅ **Meeting fixed**

> "Har switch ka log hai: signal kya tha, seller ne kya bola, kya badla, kyun badla."

## 5:00 to 6:00: Impact
- `samples/backtest.json` ka number. **Sirf real data wala number bolo.** Synthetic hai to bolo: "synthetic data pe method validate kiya; real data pe lift X% hai"
- "Calls per meeting: Y se Z", har executive ka time bachta hai

## 6:00 to 6:30: Close
> "Yeh persona layer channel-agnostic hai. Same generator WhatsApp aur chat bot ko bhi chala sakta hai. Aur har decision ka reason hai, toh business team audit kar sakti hai."

## Backup plan
- Mic kaam na kare → chips (ready-made lines) pe click karo, same flow
- Internet jaaye → `.env` se key hata ke server restart, offline mode (browser voice)
