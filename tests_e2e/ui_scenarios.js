// PS04 UI scenarios: every mid-call persona switch, driven through the real web UI.
// Run (server must be up):  node tests_e2e/ui_scenarios.js http://127.0.0.1:8001
// Needs: npm i -D playwright  (then: npx playwright install chromium)
// playwright may be installed in the repo root, backend/ or wherever you run this from
const path = require('path');
const where = [process.cwd(), __dirname, path.join(__dirname, '..'), path.join(__dirname, '..', 'backend'), '/opt/node-tools'];
let chromium;
try { ({ chromium } = require(require.resolve('playwright', { paths: where }))); }
catch { console.error('playwright not found. Run:  npm i -D playwright  (in the repo root)'); process.exit(1); }
const BASE = process.argv[2] || 'http://127.0.0.1:8001';
const OUT = require('path').join(__dirname, 'out'); require('fs').mkdirSync(OUT, { recursive: true });
const G = '241920440';
const SC = [
  { name: 'S1 rush -> faster pace, 2 slots', turns: ['Haan bolo', 'Abhi busy hoon, jaldi bolo'], expect: { signal: 'rush', field: 'voice.pace' } },
  { name: 'S2 frustration -> calm, direct, never booked', turns: ['Haan bolo', 'Kitni baar call karoge, pareshan kar diya, theek hai kal 11 baje'], expect: { ack: ['माफ़ी', 'माफ़ कीजिए', 'समझ सकती'], signal: 'frustration', notBooked: true } },
  { name: 'S3 confusion -> slower, simpler', turns: ['Haan bolo', 'Samajh nahi aaya, kya bol rahe ho'], expect: { ack: ['माफ़ कीजिए', 'ओह', 'फिर से'], signal: 'confusion', field: 'voice.pace' } },
  { name: 'S4 interest -> close', turns: ['Haan bolo', 'Accha, interesting hai, aur batao kitne buyers milenge'], expect: { ack: ['बढ़िया', 'वाह'], signal: 'interest' } },
  { name: 'S5 language -> English', turns: ['Sorry, can you speak in English please'], expect: { ack: ['in English'], signal: 'language_switch', lang: 'en-IN' } },
  { name: 'S6 language -> Gujarati + slot', turns: ['Gujarati ma vaat karo ne, Hindi nathi aavdtu', 'kale free nathi, somvare savare 11 vage rakho', 'haa saru che'], expect: { ack: ['ગુજરાતીમાં'], signal: 'language_switch', lang: 'gu-IN', booked: true } },
  { name: 'S7 slow down', turns: ['Haan bolo', 'Thoda dheere boliye please'], expect: { ack: ['आराम से', 'धीरे-धीरे'], signal: 'slow_down', field: 'voice.pace' } },
  { name: 'S8 bot question', turns: ['Aap robot ho kya?'], expect: { signal: 'bot_question' } },
  { name: 'S9 human request', turns: ['Haan bolo', 'Kisi insaan se baat karao'], expect: { signal: 'human_request' } },
  { name: 'S10 do not call', turns: ['Dubara call mat kijiye'], expect: { ended: 'declined' } },
  { name: 'S11 end call', turns: ['Haan bolo', 'Call cut kar do'], expect: { ended: 'declined', notBooked: true } },
  { name: 'S12 slot negotiation 5 vs 11', turns: ['Haan bolo', 'Theek hai', '11 baje nahi, 5 baje karte hai', 'haan theek hai'], expect: { booked: true, slot: '5 PM' } },
  { name: 'S13 two refusals', turns: ['Nahi chahiye', 'Bola na interest nahi hai'], expect: { ended: 'declined' } },
  { name: 'S14 multi-switch: rush then confusion then English', turns: ['Abhi busy hoon', 'Samajh nahi aaya', 'Please speak in English, I am from Chennai', 'Okay, tomorrow at 5 PM works'], expect: { minSwitches: 3, booked: true } },
  { name: 'S16 curious seller: answers first, meeting after', turns: ['Haan bolo', 'Accha, ye buyers kaise milte hain?', 'Aur executive aakar kya karenge?', 'Iska kuch paisa lagega kya?', 'Theek hai samajh gaya, kal 5 baje aa jaiye'], expect: { booked: true, slot: '5 PM', explains: 3 } },
  { name: 'S15 male voice + seller gender', voice: 'male', turns: ['Haan bol raha hoon, batao', 'Theek hai main free hoon kal'], expect: { signal: 'seller_gender' } },
];
(async () => {
  const b = await chromium.launch().catch(() => chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }));
  const results = [];
  for (const sc of SC) {
    const p = await b.newPage({ viewport: { width: 1500, height: 950 } });
    await p.addInitScript(() => { window.speechSynthesis = { speak: (u) => setTimeout(() => u.onend && u.onend(), 5), cancel() {}, getVoices: () => [] }; HTMLMediaElement.prototype.play = function () { setTimeout(() => this.onended && this.onended(), 5); return Promise.resolve(); }; });
    await p.goto(BASE + '/');
    if (sc.voice === 'male') await p.click('#voice button[data-g="male"]');
    await p.fill('#glid', G); await p.click('#load');
    await p.waitForSelector('#start:not([disabled])');
    await p.click('#start');
    await p.waitForFunction(() => /Your turn|turn/i.test(document.getElementById('status').textContent) || document.querySelectorAll('.bubble.bot').length > 0, null, { timeout: 40000 });
    const resps = [];
    p.on('response', async (r) => { if (r.url().includes('/turns')) { try { resps.push(await r.json()); } catch {} } });
    for (const t of sc.turns) {
      const n = resps.length;
      if (await p.isDisabled('#say')) break;
      await p.fill('#say', t); await p.click('#send');
      for (let i = 0; i < 300 && resps.length === n; i++) await p.waitForTimeout(100);
      await p.waitForFunction(() => /Your turn|Call ended|⚠/.test(document.getElementById('status').textContent), null, { timeout: 40000 });
    }
    await p.screenshot({ path: `${OUT}/${sc.name.split(' ')[0]}.png` });
    const sigs = new Set(resps.flatMap((r) => r.switches.map((s) => s.signal)));
    const fields = new Set(resps.flatMap((r) => r.switches.flatMap((s) => s.changes.map((c) => c.field))));
    const last = resps[resps.length - 1] || {};
    const e = sc.expect, fails = [];
    if (e.signal && !sigs.has(e.signal)) fails.push(`no ${e.signal} switch`);
    if (e.field && !fields.has(e.field)) fails.push(`${e.field} unchanged`);
    if (e.lang && last.persona?.language.code !== e.lang) fails.push(`lang ${last.persona?.language.code}`);
    if (e.booked && last.outcome !== 'meeting_fixed') fails.push(`not booked (${last.outcome})`);
    if (e.notBooked && resps.some((r) => r.outcome === 'meeting_fixed')) fails.push('BOOKED');
    if (e.slot && !(last.meeting_slot || '').includes(e.slot)) fails.push(`slot ${last.meeting_slot}`);
    if (e.ack && !resps.some((r) => e.ack.some((w) => r.bot.text.includes(w)))) fails.push(`no ack ${e.ack}`);
    if (e.explains && resps.filter((r) => r.move === 'explain').length < e.explains) fails.push('did not explain');
    if (e.ended && last.outcome !== e.ended) fails.push(`outcome ${last.outcome}`);
    if (e.minSwitches && resps.flatMap((r) => r.switches).length < e.minSwitches) fails.push('too few switches');
    const logCards = await p.$$eval('#log .event', (x) => x.length);
    results.push({ name: sc.name, pass: !fails.length, fails, switches: [...sigs], logCards,
      convo: resps.map((r) => ({ slot: r.meeting_slot, s: r.seller_text, b: r.bot.text, move: r.move, pace: r.bot.pace, temp: r.bot.temperature, lang: r.bot.language_code, out: r.outcome })) });
    await p.close();
  }
  await b.close();
  require('fs').writeFileSync(`${OUT}/results.json`, JSON.stringify(results, null, 1));
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} ${r.name} | switches=${r.switches} cards=${r.logCards} ${r.fails.join('; ')}`);
})();

