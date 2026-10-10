# Deploy the live demo on Vercel

The deploy runs on the **public demo dataset** in `demo/`: 8 fictional sellers in the real CSV
format, plus only *aggregates* from the real data (`evidence.json`: rates and counts;
`demand.json`: top-10% enquiries per category group). Real seller data (`data/private/`) is
gitignored and never deployed.

## Steps (5 minutes)

1. Go to **vercel.com** → sign in with GitHub → **Add New… → Project**.
2. Import **yashsahu-sys/hackathon**.
3. **Branch:** in *Settings → Git → Production Branch* set `claude/happy-hypatia-1z0cqw`
   (or merge it into `main` first).
4. **Framework preset:** *Other*. Leave build/output settings empty (`vercel.json` handles it).
5. **Environment variables:** add `SARVAM_API_KEY` = your key. (Without it the app runs in offline mode:
   rules + browser voice.)
6. **Deploy.** Your link: `https://<project>.vercel.app`.

## Demo sellers on the live link

| glid | Seller (fictional) | Persona |
|---|---|---|
| 90000001 | Embroidery shop, Lucknow | Quick · Hinglish · one-breath (busy) |
| 90000002 | Plywood maker, Chennai | Patient · English · follow-up |
| 90000003 | Saree wholesaler, Vadodara | "Kem cho" · enquiry-led (switch to Gujarati) |
| 90000004 | Packaging, Pune | follow-up: asked for a callback last time |
| 90000005 | Agro trader, Jaipur | follow-up: said not interested last time |
| 90000006 | Steel fabricator, Ludhiana | Formal · large company · met last time |
| 90000007 | Spices, Kochi | English · category-led, no history |
| 90000008 | Jute bags, Kolkata | follow-up, asked for WhatsApp details |

"+ New seller" also works (stored in `/tmp`, cleared when the server restarts).

## Know before you share

- **The Sarvam key is spent by anyone with the link.** Share it only with judges, or turn on
  *Vercel → Settings → Deployment Protection*. Rotate the key after the hackathon.
- **Serverless:** a call's state lives in the server's `/tmp`. On low traffic Vercel keeps one instance
  warm, so calls work; if an instance is recycled mid-call you'll see "session not found": just start
  the call again. For a long-lived demo, a single always-on server (Render/Railway) avoids this.
- **Mic** works because Vercel serves HTTPS.
- Regenerate the demo data: `cd backend && python -m vani.tools.make_demo_data` (on a machine that has the
  real data, so the aggregates are refreshed).
