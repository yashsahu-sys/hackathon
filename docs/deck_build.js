// VANI Persona Engine — IndiaMART Voice AI Hackathon 2.0 deck (PS04)
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require(process.env.SKILL + "/scripts/apply_theme.js");

const THEME = {
  name: "IndiaMART Growth",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1A1F36", lt1: "FFFFFF", dk2: "1C2F7A", lt2: "EEF3FB",
    accent1: "D3222A", accent2: "2E9E5B", accent3: "F29D1F", accent4: "7B4FC9", accent5: "1798C7", accent6: "E04E8C",
    hlink: "1C2F7A", folHlink: "7B4FC9",
  },
};
const H = THEME.colors;
const W = 13.333, Hh = 7.5;

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = "VANI Persona Engine";
  pres.author = "VANI Persona Engine team";
  pres.company = "IndiaMART Voice AI Hackathon 2.0";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // ------------------------------------------------------------- layouts
  const footer = (dark) => ({ text: { text: "IndiaMART  ·  VANI Persona Engine  ·  PS04", options: {
    x: 0.6, y: 7.0, w: 7, h: 0.3, fontSize: 10, color: dark ? C.background2 : "6A7090", isTextBox: true, margin: 0 } } });
  pres.defineSlideMaster({
    title: "TITLE_DARK", background: { color: H.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.0, w: 11.5, h: 1.9, fontSize: 48, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.05, w: 11.5, h: 1.2, fontSize: 22, color: C.background2, valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT", background: { color: H.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontSize: 34, bold: true, color: C.text2, valign: "middle", align: "left", margin: 0 }, text: "" } },
      footer(false),
    ],
    slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "6A7090" },
  });
  pres.defineSlideMaster({
    title: "CONTENT_TINT", background: { color: H.lt2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontSize: 34, bold: true, color: C.text2, valign: "middle", align: "left", margin: 0 }, text: "" } },
      footer(false),
    ],
    slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "6A7090" },
  });

  const card = (s, x, y, w, h, fill, name) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill },
    shadow: { type: "outer", color: "1C2F7A", opacity: 0.12, blur: 6, offset: 2, angle: 90 }, objectName: name });
  const circleIcon = async (s, Comp, x, y, d, fill, name) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: name + " circle" });
    s.addImage({ data: await icon(Comp, "FFFFFF"), x: x + d * 0.25, y: y + d * 0.25, w: d * 0.5, h: d * 0.5, objectName: name + " icon" });
  };
  const txt = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, valign: "top", fontSize: 14, color: C.text1, ...o });

  // ------------------------------------------------------------- 1 title
  pres.addSection({ title: "Story" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Story" });
  txt(s, "IndiaMART Voice AI Hackathon 2.0  ·  PS04 Persona Design", { x: 0.8, y: 1.2, w: 11, h: 0.5, fontSize: 16, color: C.accent3, bold: true });
  s.addText("From the First Call to a Bigger Business", { placeholder: "title" });
  s.addText("VANI Persona Engine: a voice, language and plan for every seller, backed by past calls and adapted live", { placeholder: "body" });
  txt(s, "Team: ______  ·  ______  ·  ______", { x: 0.8, y: 6.3, w: 8, h: 0.4, fontSize: 14, color: C.background2 });
  s.addNotes("Open with the seller's journey: every big IndiaMART seller started with one phone call. Our work makes that first call count.");

  // ------------------------------------------------------------- 2 journey
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Story" });
  s.addText("Every big seller's journey starts with one call", { placeholder: "title" });
  const steps = [
    [fa.FaPhoneAlt, "Initial call", "VANI calls and asks for a free meeting", H.accent1],
    [fa.FaHandshake, "Meeting", "Executive visits, shows real examples", H.accent5],
    [fa.FaStore, "Better listing", "Photos, prices, right category", H.accent2],
    [fa.FaChartLine, "More enquiries", "Right buyers find the seller", H.accent3],
    [fa.FaArrowUp, "Upgrade", "Higher listing, bigger reach", H.accent4],
    [fa.FaWarehouse, "Warehouse", "More stock, more capacity", H.accent6],
    [fa.FaGlobeAsia, "Pan-India", "Sells across India and beyond", H.dk2],
  ];
  const sw = 1.62, gap = 0.12, x0 = 0.6;
  for (let i = 0; i < steps.length; i++) {
    const [Ic, t, d, col] = steps[i];
    const x = x0 + i * (sw + gap), first = i === 0;
    card(s, x, 1.75, sw, 2.95, first ? "FDECEC" : H.lt2, `step ${i + 1}`);
    await circleIcon(s, Ic, x + (sw - 0.8) / 2, 2.0, 0.8, col, `step ${i + 1}`);
    txt(s, `${i + 1}`, { x: x + 0.12, y: 1.85, w: 0.4, h: 0.3, fontSize: 12, bold: true, color: col });
    txt(s, t, { x: x + 0.1, y: 3.0, w: sw - 0.2, h: 0.45, fontSize: 15, bold: true, align: "center", color: C.text2 });
    txt(s, d, { x: x + 0.12, y: 3.5, w: sw - 0.24, h: 1.1, fontSize: 13, align: "center", color: "3D4466" });
  }
  card(s, 0.6, 5.05, 12.1, 1.5, H.dk2, "step 1 callout");
  txt(s, [
    { text: "Step 1 decides whether the journey starts at all.  ", options: { bold: true, color: C.background1 } },
    { text: "If the first call fails, the shop never gets its listing, its enquiries or its warehouse. That call is what we rebuilt.", options: { color: C.background2 } },
  ], { x: 0.9, y: 5.2, w: 11.5, h: 1.2, fontSize: 18, valign: "middle" });
  s.addNotes("Mirror the IndiaMART growth story: small shop to warehouse. Point to step 1: VANI makes this call today, and that is where most journeys stop.");

  // ------------------------------------------------------------- 3 problem stats
  pres.addSection({ title: "Problem" });
  s = pres.addSlide({ masterName: "CONTENT_TINT", sectionTitle: "Problem" });
  s.addText("Today, most first calls end before they start", { placeholder: "title" });
  const stats = [["9,657", "answered VANI calls analysed", C.text2], ["11.2%", "fix a meeting", C.accent2], ["46%", "are over within 20 seconds", C.accent1]];
  for (let i = 0; i < 3; i++) {
    card(s, 0.6, 1.6 + i * 1.75, 4.6, 1.55, H.lt1, `stat ${i + 1}`);
    txt(s, stats[i][0], { x: 0.85, y: 1.72 + i * 1.75, w: 4.1, h: 0.8, fontSize: 44, bold: true, color: stats[i][2] });
    txt(s, stats[i][1], { x: 0.85, y: 2.55 + i * 1.75, w: 4.1, h: 0.45, fontSize: 15, color: "3D4466" });
  }
  card(s, 5.6, 1.6, 7.1, 5.05, H.lt1, "chart card");
  s.addChart(pres.charts.BAR, [{ name: "Meeting rate %", labels: ["Asked about the visit", "Asked about price", "All calls", "Seller busy", "Not interested", "Seller confused", "Over in 20 s"], values: [62.6, 19.6, 11.2, 5.0, 3.8, 2.6, 0.04] }], {
    x: 5.8, y: 1.75, w: 6.7, h: 4.8, barDir: "bar", showTitle: true, title: "Meeting rate by what happened on the call (%)",
    titleFontSize: 14, titleColor: H.dk2, titleFontFace: "+mn-lt", chartColors: [H.accent2, H.accent2, H.dk2, H.accent3, H.accent1, H.accent1, H.accent1],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0#", dataLabelFontSize: 11, dataLabelColor: H.dk1, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: "3D4466", catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, catAxisOrientation: "maxMin",
  });
  s.addNotes("Real numbers from the dataset. A busy or confused seller almost never books; a seller whose question gets answered (visit, price) books far more often. One script cannot do both.");

  // ------------------------------------------------------------- 4 one script
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem" });
  s.addText("One script for every seller is the real problem", { placeholder: "title" });
  card(s, 0.6, 1.6, 5.8, 4.95, H.lt2, "today card");
  txt(s, "Today: every seller hears the same call", { x: 0.9, y: 1.85, w: 5.2, h: 0.5, fontSize: 20, bold: true, color: C.text2 });
  txt(s, [
    { text: "Same voice, same pace, same Hinglish", options: { bullet: true, breakLine: true } },
    { text: "Same pitch whether the seller is busy, curious or annoyed", options: { bullet: true, breakLine: true } },
    { text: "Same opening, even for a seller who asked for a call back", options: { bullet: true, breakLine: true } },
    { text: "Misses the moment a seller changes language", options: { bullet: true } },
  ], { x: 0.9, y: 2.55, w: 5.3, h: 3.7, fontSize: 16, paraSpaceAfter: 10, color: "3D4466" });
  card(s, 6.9, 1.6, 5.8, 4.95, H.dk2, "sellers card");
  txt(s, "But sellers are not the same", { x: 7.2, y: 1.85, w: 5.2, h: 0.5, fontSize: 20, bold: true, color: C.background1 });
  const diffs = [[fa.FaLanguage, "Language", "Hinglish, English, Gujarati, Tamil..."], [fa.FaStore, "Business", "Micro retailer to Rs 100 Cr manufacturer"],
                 [fa.FaClock, "Time", "Some are driving, some want details"], [fa.FaHistory, "History", "Asked for a callback, or said no last time"]];
  for (let i = 0; i < diffs.length; i++) {
    await circleIcon(s, diffs[i][0], 7.2, 2.6 + i * 0.95, 0.65, [H.accent1, H.accent3, H.accent2, H.accent5][i], diffs[i][1]);
    txt(s, diffs[i][1], { x: 8.05, y: 2.6 + i * 0.95, w: 4.4, h: 0.32, fontSize: 16, bold: true, color: C.background1 });
    txt(s, diffs[i][2], { x: 8.05, y: 2.93 + i * 0.95, w: 4.4, h: 0.32, fontSize: 14, color: C.background2 });
  }

  // ------------------------------------------------------------- 5 solution
  pres.addSection({ title: "Solution" });
  s = pres.addSlide({ masterName: "CONTENT_TINT", sectionTitle: "Solution" });
  s.addText("VANI Persona Engine: a persona for every seller", { placeholder: "title" });
  const quad = [
    [fa.FaMicrophone, "Voice", "Payal or Arjun, the speaker, pace and expressiveness, set from the seller's history", H.accent1],
    [fa.FaLanguage, "Language", "Hinglish, English or Gujarati, formality, and how to address the seller", H.accent5],
    [fa.FaSmile, "Tone", "Warmth, empathy and how many words per turn", H.accent2],
    [fa.FaClipboardList, "Plan", "An opening built from the last call, objection answers, and slots sellers actually accept", H.accent4],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.15;
    card(s, x, y, 5.95, 1.95, H.lt1, quad[i][1]);
    await circleIcon(s, quad[i][0], x + 0.3, y + 0.5, 0.95, quad[i][3], quad[i][1]);
    txt(s, quad[i][1], { x: x + 1.5, y: y + 0.3, w: 4.2, h: 0.45, fontSize: 20, bold: true, color: C.text2 });
    txt(s, quad[i][2], { x: x + 1.5, y: y + 0.8, w: 4.2, h: 1.0, fontSize: 14, color: "3D4466" });
  }
  txt(s, [{ text: "Every choice comes with its reason, ", options: { bold: true } }, { text: "the past-call evidence behind it, and a confidence level. Nothing is a black box." }],
      { x: 0.6, y: 6.05, w: 12.1, h: 0.5, fontSize: 16, color: C.text2 });

  // ------------------------------------------------------------- 6 how it works
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solution" });
  s.addText("How it works", { placeholder: "title" });
  const flow = [
    [fa.FaDatabase, "Seller data", "5,000 profiles, 9,657 past calls, 4,920 transcript turns"],
    [fa.FaFlask, "Evidence", "140 findings, tested statistically before use"],
    [fa.FaUserCog, "Persona", "Voice, language, tone, plan, with reasons"],
    [fa.FaSlidersH, "Live adapter", "Reads every seller turn, switches the persona"],
    [fa.FaVolumeUp, "Sarvam", "Saaras listens, the Sarvam LLM understands, Bulbul speaks"],
  ];
  const fw = 2.2, fg = 0.275;
  for (let i = 0; i < flow.length; i++) {
    const x = 0.6 + i * (fw + fg);
    card(s, x, 1.9, fw, 3.0, i === 4 ? H.dk2 : H.lt2, flow[i][1]);
    await circleIcon(s, flow[i][0], x + (fw - 0.85) / 2, 2.15, 0.85, [H.accent5, H.accent4, H.accent2, H.accent3, H.accent1][i], flow[i][1]);
    txt(s, flow[i][1], { x: x + 0.12, y: 3.15, w: fw - 0.24, h: 0.45, fontSize: 17, bold: true, align: "center", color: i === 4 ? C.background1 : C.text2 });
    txt(s, flow[i][2], { x: x + 0.15, y: 3.65, w: fw - 0.3, h: 1.15, fontSize: 13, align: "center", color: i === 4 ? C.background2 : "3D4466" });
    if (i < flow.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + fw + 0.03, y: 3.25, w: 0.22, h: 0.3, fill: { color: H.dk2 }, line: { color: H.dk2 }, flipH: false, objectName: `arrow ${i + 1}` });
  }
  card(s, 0.6, 5.3, 12.1, 1.3, H.lt2, "safety card");
  await circleIcon(s, fa.FaShieldAlt, 0.85, 5.5, 0.9, H.accent2, "safety");
  txt(s, [{ text: "Safe by design.  ", options: { bold: true, color: C.text2 } },
          { text: "Hard rules run under the LLM: do-not-call always ends the call, a meeting is booked only on a clear yes with a day and time, and if the LLM fails the call carries on with rules and tested lines.", options: { color: "3D4466" } }],
      { x: 1.95, y: 5.45, w: 10.5, h: 1.0, fontSize: 15, valign: "middle" });

  // ------------------------------------------------------------- 7 live adaptation
  pres.addSection({ title: "Live" });
  s = pres.addSlide({ masterName: "CONTENT_TINT", sectionTitle: "Live" });
  s.addText("It listens, and changes in the middle of the call", { placeholder: "title" });
  const hdr = (t) => ({ text: t, options: { bold: true, color: H.lt1, fill: { color: H.dk2 }, fontSize: 15 } });
  const row = (a, b, c) => [{ text: a, options: { bold: true, color: H.dk2 } }, { text: b }, { text: c, options: { color: "3D4466" } }];
  s.addTable([
    [hdr("When the seller..."), hdr("VANI changes to..."), hdr("Why")],
    row("is busy", "calm 1.05x, one real benefit, two time slots", "Short means fewer words, not faster words"),
    row("is irritated", "even 1.0x, a sincere sorry, never books the meeting", "Booking an annoyed seller is a lost seller"),
    row("is confused or says 'slow down'", "0.85x, simpler words, one idea per sentence", "Confused sellers book only 2.6% of the time"),
    row("switches language", "Hinglish, English or Gujarati from that turn", "The seller's language beats our script"),
    row("asks for a manager", "formal and slower, books a real senior callback", "It is a trust test: say yes, don't argue"),
    row("is curious", "answers first, asks for the meeting later", "Sellers who ask about the visit book 62.6%"),
    row("speaks fast or slow", "matches their measured speed (median 2.6 words/s)", "Measured from the voice, not guessed"),
  ], { x: 0.6, y: 1.55, w: 12.1, colW: [3.0, 4.9, 4.2], fontSize: 14, fontFace: "Calibri", color: H.dk1, fill: { color: H.lt1 },
       border: { type: "solid", pt: 1, color: "D5DCEE" }, rowH: 0.6, valign: "middle", margin: [0.06, 0.12, 0.06, 0.12] });
  txt(s, "Every switch is logged live: signal, what changed, and why.", { x: 0.6, y: 6.55, w: 12.1, h: 0.35, fontSize: 13, italic: true, color: C.text2 });

  // ------------------------------------------------------------- 8 human & honest
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Live" });
  s.addText("Sounds human, stays honest", { placeholder: "title" });
  const hon = [
    [fa.FaChartBar, "Real benefits", "\"Top sellers in your category get 9+ enquiries in three months; you got 2. A better listing closes that gap.\"", "Numbers come from the data. Nothing is invented.", H.accent2],
    [fa.FaIdBadge, "Honest identity", "\"Ji, main IndiaMART se Arjun bol raha hoon.\"", "If asked, it says it is an AI assistant, in one warm line. It never claims to be human.", H.accent5],
    [fa.FaHeart, "Respect for the seller", "\"Achha sawaal hai ji\", \"Maafi chahti hoon\"", "Do-not-call ends the call. Their time beats ours: slots at 11-12 and 2-5 PM, learned from 1,078 meetings.", H.accent1],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.6, 3.9, 5.0, H.lt2, hon[i][1]);
    await circleIcon(s, hon[i][0], x + 0.3, 1.85, 0.85, hon[i][4], hon[i][1]);
    txt(s, hon[i][1], { x: x + 0.3, y: 2.85, w: 3.3, h: 0.45, fontSize: 20, bold: true, color: C.text2 });
    txt(s, hon[i][2], { x: x + 0.3, y: 3.4, w: 3.3, h: 1.5, fontSize: 15, italic: true, color: C.text1 });
    txt(s, hon[i][3], { x: x + 0.3, y: 4.95, w: 3.3, h: 1.5, fontSize: 13, color: "3D4466" });
  }

  // ------------------------------------------------------------- 9 demo
  pres.addSection({ title: "Demo" });
  s = pres.addSlide({ masterName: "CONTENT_TINT", sectionTitle: "Demo" });
  s.addText("Demo: three sellers, three personas", { placeholder: "title" });
  const demo = [
    ["Quick · Hinglish · busy trader", "North India, often cuts calls short", "One-breath opening, 1.05x, benefit first, two slots", H.accent1],
    ["Patient · English · Chennai", "Tamil Nadu, no Hindi on past calls", "Simple English, 0.9x. Switches to Hinglish the moment the seller does", H.accent5],
    ["Welcome · Gujarati · new seller", "Surat, joined after the data snapshot", "\"Kem cho\", a welcome opening, then a live switch to Gujarati with Gujarati slots", H.accent2],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.6, 3.9, 4.2, H.lt1, `demo ${i + 1}`);
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 1.85, w: 0.7, h: 0.7, fill: { color: demo[i][3] }, line: { color: demo[i][3] }, objectName: `demo ${i + 1} badge` });
    txt(s, `${i + 1}`, { x: x + 0.3, y: 1.85, w: 0.7, h: 0.7, fontSize: 22, bold: true, color: C.background1, align: "center", valign: "middle" });
    txt(s, demo[i][0], { x: x + 0.3, y: 2.75, w: 3.3, h: 0.8, fontSize: 19, bold: true, color: C.text2 });
    txt(s, demo[i][1], { x: x + 0.3, y: 3.6, w: 3.3, h: 0.7, fontSize: 14, color: "6A7090" });
    txt(s, demo[i][2], { x: x + 0.3, y: 4.3, w: 3.3, h: 1.3, fontSize: 16, color: C.text1 });
  }
  txt(s, "Live on Sarvam: Saaras speech-to-text, the Sarvam LLM, Bulbul voices. Same scenario, three different calls.", { x: 0.6, y: 6.1, w: 12.1, h: 0.4, fontSize: 15, color: C.text2, bold: true });

  // ------------------------------------------------------------- 10 built & tested
  pres.addSection({ title: "Proof" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Proof" });
  s.addText("Built and tested end to end", { placeholder: "title" });
  const proof = [["355", "automated tests pass"], ["17", "browser scenarios, every switch"], ["3", "languages live: Hinglish, English, Gujarati"], ["140", "findings mined from real calls"]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + i * 3.075;
    card(s, x, 1.7, 2.9, 2.3, H.lt2, `proof ${i + 1}`);
    txt(s, proof[i][0], { x: x + 0.25, y: 1.9, w: 2.4, h: 1.0, fontSize: 54, bold: true, color: [C.accent1, C.accent5, C.accent2, C.accent4][i] });
    txt(s, proof[i][1], { x: x + 0.25, y: 2.95, w: 2.45, h: 0.9, fontSize: 15, color: "3D4466" });
  }
  card(s, 0.6, 4.35, 12.1, 2.25, H.dk2, "found card");
  txt(s, "What testing caught and fixed", { x: 0.9, y: 4.55, w: 11.5, h: 0.45, fontSize: 18, bold: true, color: C.background1 });
  txt(s, [
    { text: "A frustrated \"theek hai, kal 11 baje\" was being booked: now never", options: { bullet: true, breakLine: true } },
    { text: "\"11 baje nahi, 5 baje karte hain\" booked 11 AM: now 5 PM, the seller's time", options: { bullet: true, breakLine: true } },
    { text: "Seller switched language, the LLM kept the old one: the switch now always wins", options: { bullet: true } },
  ], { x: 0.9, y: 5.05, w: 11.5, h: 1.45, fontSize: 15, color: C.background2, paraSpaceAfter: 4 });

  // ------------------------------------------------------------- 11 impact
  s = pres.addSlide({ masterName: "CONTENT_TINT", sectionTitle: "Proof" });
  s.addText("What this means for IndiaMART", { placeholder: "title" });
  card(s, 0.6, 1.6, 6.1, 5.0, H.lt1, "impact card");
  txt(s, "More first calls turn into journeys", { x: 0.9, y: 1.8, w: 5.6, h: 0.45, fontSize: 20, bold: true, color: C.text2 });
  txt(s, [
    { text: "Fewer calls lost in the first 20 seconds", options: { bullet: true, breakLine: true } },
    { text: "Busy and confused sellers handled, not lost", options: { bullet: true, breakLine: true } },
    { text: "Meetings that sellers actually keep", options: { bullet: true, breakLine: true } },
    { text: "Trust: honest, respectful, in the seller's language", options: { bullet: true } },
  ], { x: 0.9, y: 2.4, w: 5.6, h: 2.6, fontSize: 16, paraSpaceAfter: 10, color: "3D4466" });
  txt(s, "Measure it: A/B test against today's bot on meeting rate and early drops.", { x: 0.9, y: 5.3, w: 5.6, h: 0.9, fontSize: 14, italic: true, color: C.text2 });
  card(s, 7.0, 1.6, 5.7, 5.0, H.dk2, "next card");
  txt(s, "Next steps", { x: 7.3, y: 1.8, w: 5.1, h: 0.45, fontSize: 20, bold: true, color: C.background1 });
  const nxt = [[fa.FaUserTie, "Senior callbacks straight into the CRM"], [fa.FaSyncAlt, "Learn from VANI's own calls, next call starts smarter"],
               [fa.FaLanguage, "Native lines for Tamil, Marathi, Bengali"], [fa.FaVial, "A/B test live against today's bot"]];
  for (let i = 0; i < 4; i++) {
    await circleIcon(s, nxt[i][0], 7.3, 2.5 + i * 0.95, 0.65, [H.accent1, H.accent3, H.accent5, H.accent2][i], `next ${i + 1}`);
    txt(s, nxt[i][1], { x: 8.15, y: 2.5 + i * 0.95, w: 4.3, h: 0.65, fontSize: 15, color: C.background1, valign: "middle" });
  }

  // ------------------------------------------------------------- 12 close
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Close" });
  s.addText("IndiaMART: Your Growth Partner, at Every Stage", { placeholder: "title" });
  s.addText("VANI makes the first call count.   More visibility  ·  More leads  ·  More sales  ·  A bigger tomorrow", { placeholder: "body" });
  txt(s, "Thank you", { x: 0.8, y: 6.2, w: 6, h: 0.5, fontSize: 18, bold: true, color: C.accent3 });

  const out = process.argv[2];
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
})();
