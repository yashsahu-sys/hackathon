"""What VANI says, per language style. Delivery changes per persona; facts never do.

Hindi/Hinglish: Devanagari with English business words in Latin (how VANI's
production prompt writes Hindi). Only respectful fillers (no "यार", "अरे").
Regional languages: a native greeting, then the LLM speaks the language live.
"""

REGIONAL_GREETING = {
    "gu-IN": "Kem cho", "mr-IN": "Namaskar", "bn-IN": "Nomoshkar", "pa-IN": "Sat Sri Akal ji",
    "ta-IN": "Vanakkam", "te-IN": "Namaskaram", "kn-IN": "Namaskara", "ml-IN": "Namaskaram", "od-IN": "Namaskar",
}

# Data labels -> playbook keys
OBJECTION_KEY = {
    "Seller Unavailability & Scheduling Constraints": "busy",
    "Callback / Deferred Engagement (Neutral)": "call_later",
    "Callback / Deferred Engagement": "call_later",
    "Call Quality / Technical Failures": "audio_issue",
    "No Seller Response / Engagement Drop": "engagement_drop",
    "Explicit Disinterest / Refusal": "not_interested",
    "Call Handling / Executive Gaps": "executive_gap",
    "Wrong Contact / Business Not Applicable": "wrong_contact",
    "Existing Engagement / Past Experience": "already_in_touch",
    "Not Ready / Needs Time / Early-Stage Seller": "not_ready",
    "Product / Service / Business Mismatch": "mismatch",
    "Information / Trust / Privacy Concerns": "trust",
}
DISPOSITION_KEY = {
    "callback_requested": "call_later", "not_interested": "not_interested", "already_in_touch_with_im": "already_in_touch",
    "budget_issue_denial": "price", "wrong_number": "wrong_contact", "alternate_number_or_not_dm": "wrong_contact",
    "call_dropped": "engagement_drop",
}
QUESTION_KEY = {
    "Identity Confirmation": "identity", "AI Bot Confirmation": "bot_question", "Purpose Reason": "purpose",
    "Pricing Payment": "price", "Meeting Visit": "visit_details", "Benefit Value": "value", "Clarification": "purpose",
}

LINES = {
    "hinglish": {
        "greet": {"casual": "नमस्ते जी", "neutral": "नमस्ते जी", "formal": "नमस्कार जी"},
        "opening_history": "{greet}, मैं IndiaMART से {bot} बोल रही हूँ। पिछली बार आपसे बात हुई थी, उसी सिलसिले में आपके {category} business के लिए एक ज़रूरी update देना था।",
        "opening_enquiries": "{greet}, मैं IndiaMART से {bot} बोल रही हूँ। पिछले तीन महीने में आपको {enq_phrase}, उन्हें orders में बदलने के बारे में दो मिनट बात करनी थी।",
        "opening_cold": "{greet}, मैं IndiaMART से {bot} बोल रही हूँ। {city} में {category} के buyers IndiaMART पर search कर रहे हैं, उसी बारे में आपसे बात करनी थी।",
        "opening_brief": "{greet}, IndiaMART से {bot} बोल रही हूँ, आपके {category} business के लिए बस एक मिनट लूँगी।",
        "pitch": "हमारे executive आपसे मिलकर आपकी listing और catalog ठीक करते हैं, ताकि आपको ज़्यादा सही buyers मिलें। यह meeting बिल्कुल free है।",
        "meeting_ask": "क्या कल सुबह 11 बजे executive आपसे 20 मिनट के लिए मिल सकते हैं? चाहें तो online meeting भी हो सकती है।",
        "meeting_confirm": "बहुत बढ़िया जी, कल सुबह 11 बजे की meeting fix है। Executive एक घंटा पहले आपको call करेंगे। धन्यवाद।",
        "direct": "जी, सीधी बात: free meeting, सिर्फ़ 20 मिनट, ज़्यादा buyers। कल 11 बजे ठीक रहेगा?",
        "clarify": "मैं आसान शब्दों में बताती हूँ। हमारे executive आपके पास आएँगे, आपके products IndiaMART पर ठीक से दिखाएँगे, ताकि नए buyers आपको call करें। इसका कोई charge नहीं है।",
        "rush": "जी, मैं समझ सकती हूँ आप busy हैं। बस एक बात बता दीजिए, कल सुबह 11 बजे या शाम 5 बजे, कौन सा time ठीक है?",
        "close": "जी बिल्कुल, यही सब executive आपको detail में दिखाएँगे। कल 11 बजे fix कर दूँ?",
        "handoff": "जी ज़रूर, मैं हमारे executive से आपकी बात करवाती हूँ। क्या वे कल 11 बजे आपको call कर सकते हैं?",
        "reassure": "जी, मैं IndiaMART की virtual assistant हूँ, और आपकी meeting एक असली executive से ही fix करवा रही हूँ।",
        "close_no": "कोई बात नहीं जी, आपका समय देने के लिए धन्यवाद। ज़रूरत हो तो IndiaMART हमेशा आपके साथ है।",
        "dnc_close": "माफ़ी चाहती हूँ जी, आगे से आपको इस बारे में call नहीं आएगा। आपका समय देने के लिए धन्यवाद।",
        "callback_confirm": "ठीक है जी, मैं आपको बाद में call करवाती हूँ। धन्यवाद।",
        "playbook": {
            "busy": "समझ सकती हूँ आप busy हैं। सिर्फ़ meeting का time fix करना है, दस seconds लगेंगे।",
            "call_later": "जी ज़रूर। कब call करूँ, आज शाम 5 बजे या कल सुबह?",
            "not_interested": "जी, बस इतना बता दूँ: आपके category के sellers को IndiaMART से हर महीने नए buyers मिल रहे हैं। एक बार 20 मिनट मिलकर देख लीजिए, फ़ैसला आपका।",
            "engagement_drop": "जी, मैं आपका ज़्यादा समय नहीं लूँगी। बस meeting का एक time बता दीजिए।",
            "audio_issue": "जी, आवाज़ साफ़ नहीं आ रही थी। मैं फिर से बताती हूँ, meeting के लिए कल 11 बजे ठीक है?",
            "already_in_touch": "बहुत अच्छा कि आप पहले से जुड़े हैं। यह meeting आपकी listing की review के लिए है, ताकि जो चल रहा है उससे ज़्यादा result मिले।",
            "executive_gap": "पिछली बार की असुविधा के लिए माफ़ी चाहती हूँ। इस बार मैं time पक्का करके executive को खुद confirm करवाऊँगी।",
            "wrong_contact": "माफ़ कीजिए। क्या आप बता सकते हैं business के decisions कौन लेते हैं, ताकि मैं सही व्यक्ति से बात करूँ?",
            "not_ready": "बिल्कुल, कोई जल्दी नहीं। Meeting में बस समझ लीजिए कि शुरुआत कैसे करें, कोई commitment नहीं है।",
            "mismatch": "माफ़ कीजिए अगर गलत category दिखी हो। Executive आपकी सही category set कर देंगे, इसी के लिए यह meeting है।",
            "trust": "आपकी जानकारी सुरक्षित है। Meeting में executive अपना ID दिखाएँगे, और कोई payment नहीं माँगा जाएगा।",
            "price": "Meeting बिल्कुल free है। कोई paid plan लेना है या नहीं, वह executive से मिलकर आप तय करें।",
            "other_platform": "बहुत अच्छा। उसके साथ IndiaMART भी रखिए, बहुत से buyers यहीं search करते हैं। Executive आपको comparison दिखा देंगे।",
            "bot_question": "जी, मैं IndiaMART की virtual assistant हूँ, और meeting एक असली executive के साथ fix कर रही हूँ।",
            "identity": "जी, मैं IndiaMART से Payal बोल रही हूँ, आपके seller account के बारे में call किया है।",
            "purpose": "जी, call इसलिए किया है कि आपकी listing पर ज़्यादा buyers आएँ, और इसके लिए एक free meeting fix करनी है।",
            "visit_details": "Executive 20 मिनट के लिए आपके office आएँगे, या चाहें तो online meeting कर लेंगे। कोई तैयारी नहीं चाहिए।",
            "value": "आपकी listing ठीक होने से सही buyers आपको ढूँढ पाएँगे, जिससे enquiries और orders बढ़ते हैं।",
            "send_whatsapp": "ज़रूर, details WhatsApp पर भेज देती हूँ। साथ में meeting का time भी fix कर दूँ?",
        },
    },
    "english": {
        "greet": {"casual": "Hello", "neutral": "Hello", "formal": "Good day"},
        "opening_history": "{greet}, this is {bot} from IndiaMART. We spoke last time, and I have a quick update for your {category} business.",
        "opening_enquiries": "{greet}, this is {bot} from IndiaMART. You received {enq_phrase} in the last three months, and I'd like two minutes on turning them into orders.",
        "opening_cold": "{greet}, this is {bot} from IndiaMART. Buyers in {city} are searching for {category} on IndiaMART, and I wanted to talk to you about that.",
        "opening_brief": "{greet}, {bot} from IndiaMART, I'll take just one minute about your {category} business.",
        "pitch": "Our executive meets you and fixes your listing and catalogue, so the right buyers find you. The meeting is completely free.",
        "meeting_ask": "Could our executive meet you tomorrow at 11 AM for twenty minutes? An online meeting works too.",
        "meeting_confirm": "Wonderful, your meeting is fixed for tomorrow at 11 AM. The executive will call you an hour before. Thank you.",
        "direct": "To be brief: a free twenty-minute meeting, more buyers for you. Does tomorrow at 11 work?",
        "clarify": "Let me put it simply. Our executive visits you and shows your products properly on IndiaMART, so new buyers call you. There is no charge.",
        "rush": "I understand you're busy. Just one thing: tomorrow 11 AM or 5 PM, which suits you?",
        "close": "Certainly, the executive will walk you through all of that. Shall I book tomorrow at 11?",
        "handoff": "Of course, I'll have our executive speak with you. May they call you tomorrow at 11?",
        "reassure": "I'm IndiaMART's virtual assistant, and I'm booking you a meeting with a real executive.",
        "close_no": "No problem at all, thank you for your time. IndiaMART is here whenever you need us.",
        "dnc_close": "I'm sorry for the trouble. You won't get further calls about this. Thank you for your time.",
        "callback_confirm": "Sure, I'll arrange a call back later. Thank you.",
        "playbook": {
            "busy": "I understand. I only need to fix a time, it will take ten seconds.",
            "call_later": "Of course. Shall I call you this evening at 5 or tomorrow morning?",
            "not_interested": "Understood. Just so you know, sellers in your category get new buyers on IndiaMART every month. A twenty-minute meeting costs nothing; the decision is yours.",
            "engagement_drop": "I won't take much of your time. Just tell me one time that works for a meeting.",
            "audio_issue": "Sorry, the line wasn't clear. Would tomorrow at 11 work for the meeting?",
            "already_in_touch": "Good that you're already with us. This meeting reviews your listing so you get more from it.",
            "executive_gap": "I'm sorry about last time. This time I'll confirm the slot with the executive myself.",
            "wrong_contact": "Sorry about that. Could you tell me who handles the business decisions, so I reach the right person?",
            "not_ready": "No hurry at all. The meeting just shows how to get started, with no commitment.",
            "mismatch": "Sorry if the category looked wrong. The executive will set the right category; that's what the meeting is for.",
            "trust": "Your details are safe. The executive will show their ID, and no payment is asked for.",
            "price": "The meeting is free. Whether you take a paid plan is entirely your decision after meeting the executive.",
            "other_platform": "Great. Keep that, and add IndiaMART too; many buyers search here. The executive can show a comparison.",
            "bot_question": "I'm IndiaMART's virtual assistant, and I'm booking the meeting with a real executive.",
            "identity": "This is Payal from IndiaMART, calling about your seller account.",
            "purpose": "I'm calling so more buyers find your listing, and to fix a free meeting for that.",
            "visit_details": "The executive visits your office for twenty minutes, or meets you online. No preparation needed.",
            "value": "A better listing helps the right buyers find you, which brings more enquiries and orders.",
            "send_whatsapp": "Sure, I'll send the details on WhatsApp. Shall I also fix the meeting time?",
        },
    },
}


def lines_for(style: str) -> dict:
    """Regional styles open with a native greeting but reuse the English/Hinglish
    structure; the LLM renders them in the regional language live."""
    return LINES["english"] if style in ("english", "regional") else LINES["hinglish"]
