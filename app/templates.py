"""Bot lines per language style.

Hindi/Hinglish are written the way Saaras transcribes code-mixed speech and the
way Bulbul reads it best: Hindi words in Devanagari, English words in Latin.
In live mode the LLM writes the turns; these lines are the opening, the
objection playbook shown in the persona spec, and the offline fallback.
"""

GENDER_FORMS = {
    "female": {"rahi": "रही", "lungi": "लूँगी", "chahti": "चाहती", "sakti": "सकती", "karungi": "करूँगी", "bot": "Anaya"},
    "male": {"rahi": "रहा", "lungi": "लूँगा", "chahti": "चाहता", "sakti": "सकता", "karungi": "करूँगा", "bot": "Arjun"},
}

LINES = {
    "hinglish": {
        "opening_short": "Hello {addr}, IndiaMART से {bot} बोल {rahi} हूँ। बस 30 seconds {lungi}, आपके {category} business के लिए एक काम की बात है।",
        "opening_value": "नमस्ते {addr}, IndiaMART से {bot} बोल {rahi} हूँ। {city} में {category} के buyers हर महीने IndiaMART पर search करते हैं, मैं बताना {chahti} थी कि आप उनसे ज़्यादा leads कैसे ले सकते हैं।",
        "opening_detailed": "नमस्ते {addr}, मैं IndiaMART से {bot} बोल {rahi} हूँ। आप हमारे platform पर {category} के seller हैं। हमारे executive आपसे मिलकर आपका catalog और leads बढ़ाने में मदद कर सकते हैं। क्या आपके पास दो मिनट हैं?",
        "pitch": "पिछले महीने आपको {enq} enquiries आईं। हमारा executive आपकी listing ठीक करके और leads लाने में मदद कर सकता है, और यह meeting बिल्कुल free है।",
        "pitch_new": "अभी आपकी listing पर enquiries नहीं आ रहीं, जबकि {city} में {category} के buyers रोज़ search करते हैं। हमारा executive free में आपकी listing ठीक कर देगा।",
        "meeting_ask": "तो क्या कल सुबह 11 बजे हमारे executive आपसे 20 मिनट के लिए मिल सकते हैं?",
        "meeting_confirm": "बढ़िया {addr}! कल सुबह 11 बजे की meeting fix है। Executive आपको एक घंटा पहले call करेंगे। धन्यवाद!",
        "direct": "सीधी बात {addr}: free meeting, 20 मिनट, ज़्यादा leads। कल 11 बजे चलेगा?",
        "clarify": "मैं आसान भाषा में बताती हूँ: हमारा आदमी आपकी दुकान पर आएगा, आपके products online डालेगा, ताकि नए buyers आपको call करें। इसका कोई charge नहीं है।",
        "rush_ask": "समझ गई, आप busy हैं। बस एक बात: कल सुबह 11 बजे या शाम 5 बजे, कौन सा time ठीक रहेगा?",
        "interest_close": "बिल्कुल! इसीलिए executive से मिलना सबसे अच्छा रहेगा, वो सब details में बताएंगे। कल 11 बजे fix कर दूँ?",
        "human_handoff": "ज़रूर, मैं हमारे executive से आपकी बात करवाती हूँ। क्या वो कल 11 बजे आपको call कर सकते हैं?",
        "close_no": "कोई बात नहीं {addr}, आपका time देने के लिए धन्यवाद। ज़रूरत हो तो IndiaMART app पर हम हमेशा हैं।",
        "objections": {
            "busy": "समझ {sakti} हूँ आप busy हैं। सिर्फ़ meeting का time fix करना है, 10 seconds लगेंगे।",
            "not_interested": "ठीक है, बस एक बात: {city} के {category} sellers को IndiaMART से हर महीने नए buyers मिल रहे हैं। एक बार executive से मिलकर देख लीजिए, फ़ैसला आपका।",
            "already_other_platform": "बहुत अच्छा! दूसरे portal के साथ IndiaMART भी रखिए, ज़्यादातर बड़े buyers यहीं search करते हैं। Executive आपको दोनों का comparison दिखा देंगे।",
            "cost": "Meeting बिल्कुल free है। Paid plan लेना है या नहीं, वो executive से मिलकर आप तय कीजिए।",
            "roi": "आपको पिछले महीने {enq} enquiries आईं। Executive आपके data से दिखाएंगे कि listing ठीक करने पर कितने extra orders आ सकते हैं, फिर आप ROI खुद देख लीजिए।",
            "send_whatsapp": "ज़रूर, details WhatsApp पर भेज {karungi}। पर 20 मिनट की meeting में executive आपके numbers देखकर बताएंगे, वो ज़्यादा काम का रहेगा।",
            "think_later": "बिल्कुल सोच लीजिए। मैं बस एक tentative slot रख देती हूँ, कल 11 बजे, आप चाहें तो cancel कर सकते हैं।",
            "language": "माफ़ कीजिए, आप जिस भाषा में comfortable हैं, मैं उसी में बात {karungi}।",
        },
    },
    "hindi": {
        "opening_short": "नमस्कार {addr}, मैं इंडियामार्ट से {bot} बोल {rahi} हूँ। केवल आधा मिनट {lungi}, आपके व्यापार के लिए एक ज़रूरी बात है।",
        "opening_value": "नमस्कार {addr}, मैं इंडियामार्ट से {bot} बोल {rahi} हूँ। {city} में {category} के खरीदार हर महीने इंडियामार्ट पर खोज करते हैं। मैं बताना {chahti} थी कि आप उनसे ज़्यादा ऑर्डर कैसे पा सकते हैं।",
        "opening_detailed": "नमस्कार {addr}, मैं इंडियामार्ट से {bot} बोल {rahi} हूँ। आप हमारे मंच पर {category} के विक्रेता हैं। हमारे प्रतिनिधि आपसे मिलकर आपका व्यापार बढ़ाने में मदद कर सकते हैं। क्या आपके पास दो मिनट हैं?",
        "pitch": "पिछले महीने आपको {enq} पूछताछ आईं। हमारे प्रतिनिधि आपकी जानकारी सुधारकर और पूछताछ लाने में मदद कर सकते हैं, और यह मुलाक़ात बिल्कुल निःशुल्क है।",
        "pitch_new": "अभी आपकी जानकारी पर पूछताछ नहीं आ रही, जबकि {city} में {category} के खरीदार रोज़ खोज करते हैं। हमारे प्रतिनिधि निःशुल्क आपकी जानकारी ठीक कर देंगे।",
        "meeting_ask": "क्या कल सुबह ग्यारह बजे हमारे प्रतिनिधि आपसे बीस मिनट के लिए मिल सकते हैं?",
        "meeting_confirm": "बहुत बढ़िया {addr}। कल सुबह ग्यारह बजे की मुलाक़ात तय हो गई है। प्रतिनिधि एक घंटा पहले फ़ोन करेंगे। धन्यवाद।",
        "direct": "सीधी बात {addr}: निःशुल्क मुलाक़ात, बीस मिनट, ज़्यादा ऑर्डर। कल ग्यारह बजे ठीक रहेगा?",
        "clarify": "आसान शब्दों में: हमारे प्रतिनिधि आपके पास आएँगे, आपके सामान की जानकारी इंटरनेट पर डालेंगे, ताकि नए ग्राहक आपसे संपर्क करें। इसका कोई शुल्क नहीं है।",
        "rush_ask": "मैं समझती हूँ आप व्यस्त हैं। बस इतना बताइए: कल सुबह ग्यारह बजे या शाम पाँच बजे?",
        "interest_close": "जी बिल्कुल। इसीलिए प्रतिनिधि से मिलना सबसे अच्छा रहेगा। कल ग्यारह बजे तय कर दूँ?",
        "human_handoff": "जी ज़रूर, मैं हमारे प्रतिनिधि से आपकी बात करवाती हूँ। क्या वे कल ग्यारह बजे आपको फ़ोन कर सकते हैं?",
        "close_no": "कोई बात नहीं {addr}, समय देने के लिए धन्यवाद। ज़रूरत हो तो इंडियामार्ट हमेशा आपके साथ है।",
        "objections": {
            "busy": "मैं समझ {sakti} हूँ। केवल मुलाक़ात का समय तय करना है, दस सेकंड लगेंगे।",
            "not_interested": "जी ठीक है। बस इतना जान लीजिए कि {city} के {category} विक्रेताओं को हर महीने नए खरीदार मिल रहे हैं। एक बार मिलकर देख लीजिए।",
            "already_other_platform": "बहुत अच्छा। उसके साथ इंडियामार्ट भी रखिए, ज़्यादातर बड़े खरीदार यहीं खोजते हैं।",
            "cost": "मुलाक़ात पूरी तरह निःशुल्क है। आगे का निर्णय आपका होगा।",
            "roi": "पिछले महीने आपको {enq} पूछताछ आईं। प्रतिनिधि आपके आँकड़ों से दिखाएँगे कि कितने अतिरिक्त ऑर्डर आ सकते हैं।",
            "send_whatsapp": "जी, जानकारी व्हाट्सऐप पर भेज {karungi}। पर मुलाक़ात में आपके आँकड़े देखकर बात करना ज़्यादा उपयोगी रहेगा।",
            "think_later": "जी, सोच लीजिए। मैं कल ग्यारह बजे का समय रख देती हूँ, आप चाहें तो रद्द कर सकते हैं।",
            "language": "क्षमा कीजिए, आप जिस भाषा में सहज हैं, मैं उसी में बात {karungi}।",
        },
    },
    "english": {
        "opening_short": "Hi {addr}, this is {bot} from IndiaMART. Just thirty seconds, I have something useful for your {category} business.",
        "opening_value": "Good day {addr}, this is {bot} from IndiaMART. Buyers in {city} search for {category} on IndiaMART every month, and I wanted to share how you can win more of those orders.",
        "opening_detailed": "Good day {addr}, this is {bot} calling from IndiaMART. You are listed with us as a {category} supplier. Our executive can visit you and help grow your catalogue and enquiries. Do you have two minutes?",
        "pitch": "Last month you received {enq} enquiries. Our executive can improve your listing to bring in more, and the visit is completely free of charge.",
        "pitch_new": "Your listing isn't getting enquiries yet, while buyers in {city} search for {category} every day. Our executive will fix your listing for free.",
        "meeting_ask": "Would tomorrow at 11 AM work for a twenty-minute visit from our executive?",
        "meeting_confirm": "Wonderful, {addr}. Your meeting is confirmed for tomorrow at 11 AM. The executive will call you an hour before. Thank you for your time.",
        "direct": "To be brief, {addr}: a free twenty-minute visit, more enquiries for you. Does tomorrow at 11 work?",
        "clarify": "Let me put it simply. Our executive visits you, puts your products online properly, and new buyers start calling you. There is no charge for this.",
        "rush_ask": "I understand you are busy. Just one question: tomorrow 11 AM or 5 PM, which suits you?",
        "interest_close": "Certainly. That is exactly what the executive will walk you through. Shall I book tomorrow at 11 AM?",
        "human_handoff": "Of course, I will have our executive speak with you directly. May they call you tomorrow at 11 AM?",
        "close_no": "No problem at all, {addr}. Thank you for your time. IndiaMART is here whenever you need us.",
        "objections": {
            "busy": "I understand. I only need to fix a time, it will take ten seconds.",
            "not_interested": "Understood. Just so you know, {category} suppliers in {city} are getting new buyers on IndiaMART every month. A short visit costs you nothing.",
            "already_other_platform": "That is great. Keep it, and add IndiaMART as well; most large buyers search here. The executive can show you a side-by-side comparison.",
            "cost": "The visit is completely free. Whether you take a paid plan later is entirely your decision.",
            "roi": "You received {enq} enquiries last month. The executive will use your own numbers to show how many extra orders a better listing brings, so you can judge the return yourself.",
            "send_whatsapp": "Certainly, I will send the details on WhatsApp. But twenty minutes with your numbers in front of you will be far more useful.",
            "think_later": "Of course, take your time. I will hold a tentative slot tomorrow at 11 AM, and you can cancel anytime.",
            "language": "My apologies. I will continue in whichever language you are comfortable with.",
        },
    },
}

LANGUAGE_NAMES = {
    "hi-IN": "Hindi", "en-IN": "English", "ta-IN": "Tamil", "te-IN": "Telugu", "kn-IN": "Kannada",
    "ml-IN": "Malayalam", "bn-IN": "Bengali", "gu-IN": "Gujarati", "mr-IN": "Marathi",
    "pa-IN": "Punjabi", "od-IN": "Odia",
}


def lines_for(style: str) -> dict:
    # Regional styles reuse the English lines offline; live, the LLM speaks the regional language.
    return LINES.get(style, LINES["english"])


def fill(text: str, ctx: dict) -> str:
    try:
        return text.format(**ctx)
    except (KeyError, IndexError):
        return text
