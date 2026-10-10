# VANI Persona Engine: demo video script (5 to 6 minutes)

Deck: `Echotech.pptx` (12 slides). Three presenters. Total about **5:45**.

| Who | Role in the video | Slides | Time |
|---|---|---|---|
| **Presenter 1** (Lead / storyteller) | Opens, the problem, closes with the ask | 1-4, 11-12 | ~2:00 |
| **Presenter 2** (Product) | The solution and how it adapts | 5-8 | ~1:30 |
| **Presenter 3** (Demo) | Live demo of three sellers, proof | 9-10 + screen | ~2:15 |

Speak slowly, smile, look at the camera on the **bold** lines. Every number below is from the real dataset or our tests.

---

## PART 1: Presenter 1 (0:00 to 1:20)

**[Slide 1, title. Presenter 1 on camera.]**

> Good morning. We are Team Echotech.
>
> **Every big seller on IndiaMART, the one with a warehouse today, started with one phone call.**
>
> Our project is about making that first call count.

**[Slide 2, the seven-step journey. Point to step 1.]**

> This is the journey IndiaMART takes a seller on. A first call, a meeting, a better listing, more enquiries, an upgrade, a warehouse, and finally sales across India.
>
> But look at step one. If that call fails, nothing after it ever happens. No listing, no enquiries, no growth.
>
> Today, VANI makes that call. So we asked one question: **how good is that first call?**

**[Slide 3, the numbers.]**

> We studied 9,657 real VANI calls.
>
> Only 11.2 percent fix a meeting. And 46 percent are over in twenty seconds. Those almost never convert.
>
> Here is the part that stayed with us. When a seller is busy, only 5 percent book. When a seller is confused, 2.6 percent. But when a seller's question gets answered, about the visit for example, 62 percent book.
>
> **So the seller is not the problem. The way we talk to them is.**

**[Slide 4, one script for everyone.]**

> Today every seller hears the same call. Same voice, same pace, same Hinglish, same pitch.
>
> But a Chennai manufacturer, a busy trader in Uttar Pradesh and a new shop owner in Surat are not the same person. Their language, their time and their history are different.
>
> Over to my colleague, who will show you what we built.

---

## PART 2: Presenter 2 (1:20 to 2:55)

**[Slide 5, the four parts of a persona.]**

> Thank you. We built the **VANI Persona Engine**. Before every call, it builds a persona for that one seller.
>
> Four things. The **voice**: Payal or Arjun, the pace, how expressive. The **language**: Hinglish, English or Gujarati, and how formally to speak. The **tone**: how warm, how many words. And the **plan**: an opening built from how the last call ended, and meeting times sellers actually accept.
>
> **And every choice comes with its reason and the evidence behind it. Nothing is a black box.**

**[Slide 6, how it works.]**

> Here is how it works. We take the seller's profile and their past calls. We mine 140 findings from 9,657 calls, and every finding is tested statistically before we use it. The engine builds the persona. Then, during the call, Sarvam does the talking. Saaras listens, the Sarvam LLM understands, and Bulbul speaks.
>
> Underneath, there are hard safety rules. If a seller says "don't call me again", the call ends, always. And a meeting is booked only on a clear yes with a day and a time.

**[Slide 7, the switch table.]**

> And the persona does not stay fixed. **It listens, and changes in the middle of the call.**
>
> Busy seller? VANI gets to the point with one real benefit, but stays calm. Short means fewer words, not faster words. Irritated? A sincere sorry, and it never pushes a booking. Confused? It slows down and uses simpler words. The seller switches language? VANI follows from that very turn. Asks for a manager? It becomes formal and books a real callback from a senior person.

**[Slide 8, human and honest.]**

> Two things we refused to compromise on.
>
> First, **real benefits**. VANI tells a seller what top sellers in their category actually get, from the data. Nothing is invented.
>
> Second, **honesty**. VANI introduces itself by name. If a seller asks "are you a bot?", it says yes, it is IndiaMART's AI assistant, in one warm line. It never pretends to be human.
>
> Let's see it live.

---

## PART 3: Presenter 3 (2:55 to 5:10)

**[Slide 9 for three seconds, then switch to the screen: the VANI app, Live call tab.]**

> Thank you. Same product, same scenario, three very different sellers. Watch the switch log on the right. Every change shows up there, with the reason.

### Seller 1: Quick, Hinglish, busy trader (about 40 seconds)

**[Type glid `241920440`, click Load. Show the persona panel: "Quick · Hinglish · Formal · One-breath". Click Start call.]**

> Seller one cuts calls short. His history says so. So VANI opens in one breath: name, IndiaMART, one minute.

**[Mic or type, as the seller:]** *"Haan bolo."*
**[VANI pitches the free meeting.]**

**[Seller:]** *"Abhi busy hoon, jaldi batao."*

> Watch this. He's busy. VANI does not speed up and race through. It gives him one real benefit: top sellers on IndiaMART get nine-plus enquiries in three months. Then it offers two times. Rush is now on the switch log.

**[Seller:]** *"Theek hai, kal 5 baje."*

> **Meeting fixed, tomorrow 5 PM. Under thirty seconds.**

### Seller 2: Patient, English, Chennai (about 50 seconds)

**[Type glid `112087076`, click Load (Chennai). Persona: "Patient · English · Formal". Start call.]**

> Seller two is in Chennai and never spoke Hindi on past calls. So VANI opens in simple English, at a slower pace.

**[Seller:]** *"Yes, tell me."*

**[Seller, switching to Hindi:]** *"Abhi busy hoon, baad mein call karna."*

> Now the seller switched to Hindi. And VANI says: "ji zaroor, Hindi mein baat karte hain." It switched language **and** handled the rush in the same turn. Two cards on the switch log.

**[Seller:]** *"Matlab? Samjha nahi."*

> Confused. The pace drops to 0.85, the words get simpler.

**[Seller:]** *"Kya fayda hoga?"*

> A sceptical question. It answers with real numbers from his own category, and doesn't push the slot yet.

**[Seller:]** *"Theek hai, kal 11 baje aa jaiye."*

> **Three persona changes in one call, and a meeting fixed.**

### Seller 3: A new seller, Gujarati (about 45 seconds)

**[Open "+ New seller". Fill in: Surat, Gujarat, Cotton Sarees, Wholesaler, GST year 2025. Click Add. Start call.]**

> Seller three joined IndiaMART last week. There is no history at all. So VANI builds the persona from similar sellers, and opens with "Kem cho", and a welcome.

**[Seller:]** *"Gujarati ma vaat karo ne, Hindi nathi aavdtu."*

> He wants Gujarati. From this turn, VANI speaks Gujarati. Native lines, Gujarati voice.

**[Seller:]** *"Kale free nathi, somvare savare 11 vage rakho."*

> He said: not tomorrow, Monday 11 AM. VANI takes **his** time, not ours, and reads it back.

**[Seller:]** *"Haa saru che."*

> **Meeting fixed, Monday 11 AM, in Gujarati.**

**[Slide 10, built and tested.]**

> All of this is tested. 355 automated tests, and 17 full browser scenarios that cover every switch. Testing caught real bugs. A frustrated seller was being booked. Now never. "Eleven nahi, five baje" booked eleven. Now it's five, the seller's time.

---

## PART 4: Presenter 1 (5:10 to 5:45)

**[Slide 11, what this means.]**

> So what does this mean for IndiaMART?
>
> Fewer calls lost in the first twenty seconds. Busy and confused sellers handled, not lost. And trust: honest, respectful, in the seller's own language.
>
> Our ask is simple. **Let us A/B test this against today's bot**, on meeting rate and early drops. The data will tell us.

**[Slide 12, closing. Presenter 1 on camera.]**

> IndiaMART is the growth partner at every stage. **VANI Persona Engine makes sure the first stage, the first call, actually happens.**
>
> Thank you.

---

## Shooting checklist

- **Run the three calls once before recording.** The live LLM phrases things a little differently each time; the flow and the switch cards stay the same.
- **Say the seller lines exactly as written** (or type them). They are tested to trigger each switch.
- **Zoom the screen to the chat and switch log**, not the browser chrome. Keep the switch log visible while VANI speaks.
- **Privacy:** the seller card shows real company names and the glid box shows IDs. Crop or blur them in the edit, or keep the camera on the chat and persona panel. No CSV data on screen.
- **Audio:** record Bulbul's voice from the app (not through the room mic) so it is clear. Use a headset mic for the seller lines.
- **Backup:** if the network fails, the app still runs on rules; record that take too, just in case.
- **Timing guide:** Part 1 ~1:20, Part 2 ~1:35, Part 3 ~2:15, Part 4 ~0:35. If you run long, cut Seller 2's "Kya fayda hoga?" step first.
