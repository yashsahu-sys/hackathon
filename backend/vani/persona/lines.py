"""What VANI says, per language style. Delivery changes per persona; facts never do.

Hindi/Hinglish: Devanagari with English business words in Latin (how VANI's
production prompt writes Hindi). Only respectful fillers (no "यार", "अरे").
Gujarati: Gujarati script with English business words, gender-neutral first person
(બોલું છું) so the same line works for Payal and Arjun. Other regional languages:
a native greeting, then the LLM speaks the language live.
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
        "meeting_ask": "क्या {slot1} executive आपसे 20 मिनट के लिए मिल सकते हैं? चाहें तो online meeting भी हो सकती है।",
        "meeting_confirm": "बहुत बढ़िया जी, {slot} की meeting fix है। Executive एक घंटा पहले आपको call करेंगे। धन्यवाद।",
        "direct": "जी, सीधी बात: free meeting, सिर्फ़ 20 मिनट, ज़्यादा buyers। {slot1} ठीक रहेगा?",
        "clarify": "मैं आसान शब्दों में बताती हूँ। हमारे executive आपके पास आएँगे, आपके products IndiaMART पर ठीक से दिखाएँगे, ताकि नए buyers आपको call करें। इसका कोई charge नहीं है।",
        "rush": "जी, मैं समझ सकती हूँ आप busy हैं। बस एक बात बता दीजिए, {slot1} या {slot2}, कौन सा time ठीक है?",
        "close": "जी बिल्कुल, यही सब executive आपको detail में दिखाएँगे। {slot1} fix कर दूँ?",
        "handoff": "जी ज़रूर, मैं हमारे executive से आपकी बात करवाती हूँ। क्या वे {slot1} आपको call कर सकते हैं?",
        "reassure": "जी, मैं IndiaMART की virtual assistant हूँ, और आपकी meeting एक असली executive से ही fix करवा रही हूँ।",
        "close_no": "कोई बात नहीं जी, आपका समय देने के लिए धन्यवाद। ज़रूरत हो तो IndiaMART हमेशा आपके साथ है।",
        "dnc_close": "माफ़ी चाहती हूँ जी, आगे से आपको इस बारे में call नहीं आएगा। आपका समय देने के लिए धन्यवाद।",
        "callback_confirm": "ठीक है जी, मैं आपको बाद में call करवाती हूँ। धन्यवाद।",
        "ask_time": "जी बढ़िया! किस दिन और किस time आपके लिए ठीक रहेगा? जैसे {slot1} या {slot2}?",
        "confirm_proposed": "ठीक है जी, तो {slot1} fix कर दूँ?",
        "reschedule": "कोई बात नहीं जी। तो {slot1} या {slot2}, इनमें से कौन सा time ठीक रहेगा?",
        "end_close": "माफ़ी चाहती हूँ जी, आपको परेशान करने का इरादा नहीं था। मैं call यहीं ख़त्म करती हूँ। धन्यवाद।",
        "playbook": {
            "busy": "समझ सकती हूँ आप busy हैं। सिर्फ़ meeting का time fix करना है, दस seconds लगेंगे।",
            "call_later": "जी ज़रूर। कब call करूँ, {slot1} या {slot2}?",
            "not_interested": "जी, बस इतना बता दूँ: आपके category के sellers को IndiaMART से हर महीने नए buyers मिल रहे हैं। एक बार 20 मिनट मिलकर देख लीजिए, फ़ैसला आपका।",
            "engagement_drop": "जी, मैं आपका ज़्यादा समय नहीं लूँगी। बस meeting का एक time बता दीजिए।",
            "audio_issue": "जी, आवाज़ साफ़ नहीं आ रही थी। मैं फिर से बताती हूँ, meeting के लिए {slot1} ठीक है?",
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
        "meeting_ask": "Could our executive meet you {slot1} for twenty minutes? An online meeting works too.",
        "meeting_confirm": "Wonderful, your meeting is fixed for {slot}. The executive will call you an hour before. Thank you.",
        "direct": "To be brief: a free twenty-minute meeting, more buyers for you. Does {slot1} work?",
        "clarify": "Let me put it simply. Our executive visits you and shows your products properly on IndiaMART, so new buyers call you. There is no charge.",
        "rush": "I understand you're busy. Just one thing: {slot1} or {slot2}, which suits you?",
        "close": "Certainly, the executive will walk you through all of that. Shall I book {slot1}?",
        "handoff": "Of course, I'll have our executive speak with you. May they call you {slot1}?",
        "reassure": "I'm IndiaMART's virtual assistant, and I'm booking you a meeting with a real executive.",
        "close_no": "No problem at all, thank you for your time. IndiaMART is here whenever you need us.",
        "dnc_close": "I'm sorry for the trouble. You won't get further calls about this. Thank you for your time.",
        "callback_confirm": "Sure, I'll arrange a call back later. Thank you.",
        "ask_time": "Great! Which day and time suit you? For example {slot1} or {slot2}?",
        "confirm_proposed": "Sure, shall I fix {slot1} then?",
        "reschedule": "No problem. Would {slot1} or {slot2} work better?",
        "end_close": "I'm sorry for the trouble. I'll end the call here. Thank you for your time.",
        "playbook": {
            "busy": "I understand. I only need to fix a time, it will take ten seconds.",
            "call_later": "Of course. Shall I call you {slot1} or {slot2}?",
            "not_interested": "Understood. Just so you know, sellers in your category get new buyers on IndiaMART every month. A twenty-minute meeting costs nothing; the decision is yours.",
            "engagement_drop": "I won't take much of your time. Just tell me one time that works for a meeting.",
            "audio_issue": "Sorry, the line wasn't clear. Would {slot1} work for the meeting?",
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
    "gujarati": {
        "greet": {"casual": "કેમ છો", "neutral": "નમસ્તે", "formal": "નમસ્કાર"},
        "opening_history": "{greet}, હું IndiaMART થી {bot} બોલું છું. ગયા વખતે આપણી વાત થઈ હતી, એ જ સંદર્ભમાં તમારા {category} business માટે એક જરૂરી update આપવો હતો.",
        "opening_enquiries": "{greet}, હું IndiaMART થી {bot} બોલું છું. છેલ્લા ત્રણ મહિનામાં તમને {enq_phrase}, એને orders માં ફેરવવા વિશે બે મિનિટ વાત કરવી હતી.",
        "opening_cold": "{greet}, હું IndiaMART થી {bot} બોલું છું. {city} માં {category} ના buyers IndiaMART પર search કરી રહ્યા છે, એ વિશે તમારી સાથે વાત કરવી હતી.",
        "opening_brief": "{greet}, IndiaMART થી {bot} બોલું છું, તમારા {category} business માટે બસ એક મિનિટ લઈશ.",
        "pitch": "અમારા executive તમને મળીને તમારી listing અને catalog સરખી કરી આપે છે, જેથી તમને વધારે સાચા buyers મળે. આ meeting બિલકુલ free છે.",
        "meeting_ask": "શું {slot1} અમારા executive તમને 20 મિનિટ માટે મળી શકે? ઇચ્છો તો online meeting પણ થઈ શકે.",
        "meeting_confirm": "ખૂબ સરસ, {slot} meeting fix છે. Executive એક કલાક પહેલાં તમને call કરશે. આભાર.",
        "direct": "સીધી વાત: free meeting, ફક્ત 20 મિનિટ, વધારે buyers. {slot1} ચાલશે?",
        "clarify": "હું સરળ શબ્દોમાં કહું. અમારા executive તમારી પાસે આવશે, તમારા products IndiaMART પર સરખી રીતે બતાવશે, જેથી નવા buyers તમને call કરે. આનો કોઈ charge નથી.",
        "rush": "હું સમજી શકું છું કે તમે busy છો. બસ એટલું કહો, {slot1} કે {slot2}, કયો time ફાવશે?",
        "close": "ચોક્કસ, આ બધું executive તમને detail માં બતાવશે. {slot1} fix કરી દઉં?",
        "handoff": "ચોક્કસ, હું અમારા executive સાથે તમારી વાત કરાવું છું. શું તેઓ {slot1} તમને call કરી શકે?",
        "reassure": "હું IndiaMART ની virtual assistant છું, અને તમારી meeting એક સાચા executive સાથે fix કરાવું છું.",
        "close_no": "કોઈ વાંધો નહીં, તમારો સમય આપવા બદલ આભાર. જરૂર હોય તો IndiaMART હંમેશા તમારી સાથે છે.",
        "dnc_close": "માફ કરજો, હવેથી તમને આ વિશે call નહીં આવે. તમારો સમય આપવા બદલ આભાર.",
        "callback_confirm": "સારું, હું તમને પછીથી call કરાવું છું. આભાર.",
        "ask_time": "ખૂબ સરસ! કયા દિવસે અને કયા time તમને ફાવશે? જેમ કે {slot1} કે {slot2}?",
        "confirm_proposed": "સારું, તો {slot1} fix કરી દઉં?",
        "reschedule": "કોઈ વાંધો નહીં. તો {slot1} કે {slot2}, આમાંથી કયો time ફાવશે?",
        "end_close": "માફ કરજો, તમને હેરાન કરવાનો ઇરાદો નહોતો. હું call અહીં જ પૂરો કરું છું. આભાર.",
        "playbook": {
            "busy": "સમજી શકું છું કે તમે busy છો. ફક્ત meeting નો time fix કરવો છે, દસ seconds લાગશે.",
            "call_later": "ચોક્કસ. ક્યારે call કરું, {slot1} કે {slot2}?",
            "not_interested": "બસ એટલું કહું: તમારી category ના sellers ને IndiaMART પરથી દર મહિને નવા buyers મળે છે. એક વાર 20 મિનિટ મળીને જોઈ લો, નિર્ણય તમારો.",
            "engagement_drop": "હું તમારો વધારે સમય નહીં લઉં. બસ meeting નો એક time કહી દો.",
            "audio_issue": "માફ કરજો, અવાજ બરાબર નહોતો આવતો. ફરીથી કહું, meeting માટે {slot1} ચાલશે?",
            "already_in_touch": "સરસ કે તમે પહેલેથી જોડાયેલા છો. આ meeting તમારી listing ના review માટે છે, જેથી વધારે result મળે.",
            "executive_gap": "ગયા વખતની તકલીફ માટે માફ કરજો. આ વખતે હું time પાકો કરીને executive પાસે જાતે confirm કરાવીશ.",
            "wrong_contact": "માફ કરજો. શું તમે કહી શકો કે business ના નિર્ણય કોણ લે છે, જેથી હું સાચી વ્યક્તિ સાથે વાત કરું?",
            "not_ready": "બિલકુલ, કોઈ ઉતાવળ નથી. Meeting માં બસ સમજી લો કે શરૂઆત કેવી રીતે કરવી, કોઈ commitment નથી.",
            "mismatch": "ખોટી category દેખાઈ હોય તો માફ કરજો. Executive તમારી સાચી category set કરી આપશે, એ માટે જ આ meeting છે.",
            "trust": "તમારી માહિતી સુરક્ષિત છે. Meeting માં executive પોતાનું ID બતાવશે, અને કોઈ payment માંગવામાં નહીં આવે.",
            "price": "Meeting બિલકુલ free છે. કોઈ paid plan લેવો કે નહીં, એ executive ને મળીને તમે નક્કી કરો.",
            "other_platform": "સરસ. એની સાથે IndiaMART પણ રાખો, ઘણા buyers અહીં search કરે છે. Executive તમને comparison બતાવી દેશે.",
            "bot_question": "હું IndiaMART ની virtual assistant છું, અને meeting એક સાચા executive સાથે fix કરું છું.",
            "identity": "હું IndiaMART થી Payal બોલું છું, તમારા seller account વિશે call કર્યો છે.",
            "purpose": "Call એટલા માટે કર્યો છે કે તમારી listing પર વધારે buyers આવે, અને એ માટે એક free meeting fix કરવી છે.",
            "visit_details": "Executive 20 મિનિટ માટે તમારી office આવશે, અથવા ઇચ્છો તો online meeting કરશે. કોઈ તૈયારીની જરૂર નથી.",
            "value": "તમારી listing સરખી થવાથી સાચા buyers તમને શોધી શકશે, જેથી enquiries અને orders વધે છે.",
            "send_whatsapp": "ચોક્કસ, details WhatsApp પર મોકલી દઉં છું. સાથે meeting નો time પણ fix કરી દઉં?",
        },
    },
}


def lines_for(style: str) -> dict:
    """Hinglish, English and Gujarati have their own lines. Other regional styles open
    with a native greeting but reuse the English structure; the LLM renders them live."""
    return LINES.get(style) or LINES["english"]


# Openings that pick up where the LAST call ended (its disposition), instead of a generic "we spoke last time".
HISTORY_OPENINGS = {
    "hinglish": {
        "callback": "{greet}, मैं IndiaMART से {bot} बोल रही हूँ। पिछली बार आपने कहा था बाद में बात करेंगे, तो आज call किया। आपके {category} business के लिए बस दो मिनट चाहिए।",
        "dropped": "{greet}, मैं IndiaMART से {bot} बोल रही हूँ। पिछली बार हमारी call बीच में कट गई थी, तो दोबारा call किया, आपके {category} business के बारे में।",
        "not_interested": "{greet}, मैं IndiaMART से {bot} बोल रही हूँ। पिछली बार आपने कहा था अभी ज़रूरत नहीं, बस आपके {category} business के लिए एक नई बात बतानी थी, एक मिनट लूँगी।",
        "met": "{greet}, मैं IndiaMART से {bot} बोल रही हूँ। हमारे executive पिछली बार आपसे मिले थे, उसी के follow-up में आपके {category} business के लिए call किया है।",
    },
    "english": {
        "callback": "{greet}, this is {bot} from IndiaMART. Last time you asked us to call back later, so here I am. I just need two minutes about your {category} business.",
        "dropped": "{greet}, this is {bot} from IndiaMART. Our call got cut last time, so I'm calling back about your {category} business.",
        "not_interested": "{greet}, this is {bot} from IndiaMART. Last time you said you didn't need it right now; I have one new thing for your {category} business, just a minute.",
        "met": "{greet}, this is {bot} from IndiaMART. Our executive met you last time, and I'm following up on that for your {category} business.",
    },
    "gujarati": {
        "callback": "{greet}, હું IndiaMART થી {bot} બોલું છું. ગયા વખતે તમે કહ્યું હતું પછી વાત કરીએ, એટલે આજે call કર્યો. તમારા {category} business માટે બસ બે મિનિટ જોઈએ.",
        "dropped": "{greet}, હું IndiaMART થી {bot} બોલું છું. ગયા વખતે આપણો call વચ્ચે કપાઈ ગયો હતો, એટલે ફરી call કર્યો, તમારા {category} business વિશે.",
        "not_interested": "{greet}, હું IndiaMART થી {bot} બોલું છું. ગયા વખતે તમે કહ્યું હતું હમણાં જરૂર નથી, બસ તમારા {category} business માટે એક નવી વાત કહેવી હતી, એક મિનિટ લઈશ.",
        "met": "{greet}, હું IndiaMART થી {bot} બોલું છું. અમારા executive ગયા વખતે તમને મળ્યા હતા, એના follow-up માટે તમારા {category} business વિશે call કર્યો છે.",
    },
}

# Extra phrasings for the lines VANI says most. A real caller never says a sentence the same way to every
# seller: the variant is picked per seller and rotates if the same move comes back in a call.
VARIANTS = {
    "hinglish": {
        "pitch": ["देखिए, हमारे executive आपसे मिलकर आपकी listing ठीक करते हैं, ताकि सही buyers सीधे आपको call करें। Meeting बिल्कुल free है।",
                  "असल में call इसलिए किया कि आपके products IndiaMART पर और अच्छे से दिखें। हमारे executive 20 मिनट मिलकर ये कर देते हैं, कोई charge नहीं।"],
        "meeting_ask": ["तो {slot1} executive आपसे 20 मिनट के लिए मिल लें? Online भी हो सकता है।",
                        "आप बताइए, {slot1} ठीक रहेगा? बस 20 मिनट लगेंगे।"],
        "clarify": ["सीधी सी बात है जी: हमारे executive आपके पास आएँगे और आपके products IndiaMART पर अच्छे से लगा देंगे, ताकि नए buyers आपको ढूँढ सकें। पैसे कुछ नहीं लगते।",
                    "देखिए, बस इतना है: executive आएँगे, आपकी listing ठीक करेंगे, और आपको ज़्यादा enquiries मिलेंगी। ये free है।"],
        "rush": ["बस दस seconds जी। {slot1} या {slot2}, कौन सा ठीक है?",
                 "जी, समझ गई, छोटा रखती हूँ। {slot1} या {slot2}?"],
        "close": ["हाँ जी, ये सब executive आपको खुद दिखा देंगे। {slot1} रख दूँ?", "बढ़िया! तो {slot1} meeting fix कर दूँ?"],
        "ask_time": ["अच्छा जी! तो आपके लिए कौन सा दिन और time ठीक रहेगा, {slot1} या {slot2}?"],
        "reschedule": ["ठीक है जी, कोई दिक्कत नहीं। फिर {slot1} या {slot2} कैसा रहेगा?"],
        "direct": ["जी, एक line में: free meeting, 20 मिनट, ज़्यादा buyers। {slot1} चलेगा?"],
        "not_interested": ["समझ सकती हूँ जी। बस एक बात: आपकी category में sellers को हर महीने नए buyers मिल रहे हैं। एक बार 20 मिनट मिल के देख लीजिए, फिर आप तय करना।"],
        "busy": ["जी, बस दस seconds, सिर्फ़ time fix करना है।"],
        "call_later": ["ज़रूर जी, तो {slot1} या {slot2}, कब call करूँ?"],
    },
    "english": {
        "pitch": ["Basically, our executive meets you and sets up your listing properly, so the right buyers call you directly. It's completely free.",
                  "I'm calling so your products show up better on IndiaMART. Our executive does that in a free twenty-minute meeting."],
        "meeting_ask": ["So, could our executive drop by {slot1}? Just twenty minutes, or online if you prefer.",
                        "Would {slot1} work for you? It takes only twenty minutes."],
        "clarify": ["Simply put: our executive visits, puts your products up properly on IndiaMART, and new buyers find you. No charge."],
        "rush": ["Just ten seconds. {slot1} or {slot2}, which one?"],
        "close": ["Great! The executive will show you all of that. Shall I book {slot1}?"],
        "ask_time": ["Lovely! Which day and time suit you, {slot1} or {slot2}?"],
        "reschedule": ["That's fine. How about {slot1} or {slot2} then?"],
        "direct": ["In one line: free meeting, twenty minutes, more buyers. Does {slot1} work?"],
        "not_interested": ["I understand. Just one thing: sellers in your category get new buyers here every month. Meet once for twenty minutes, then decide."],
    },
    "gujarati": {
        "pitch": ["જુઓ, અમારા executive તમને મળીને listing સરખી કરી આપે છે, જેથી સાચા buyers સીધા તમને call કરે. આ meeting free છે."],
        "meeting_ask": ["તો {slot1} executive તમને 20 મિનિટ મળી લે? Online પણ ચાલશે."],
        "clarify": ["સીધી વાત છે: executive આવશે, તમારા products IndiaMART પર સરખા મૂકશે, અને નવા buyers તમને શોધશે. કોઈ પૈસા નથી."],
        "rush": ["બસ દસ seconds. {slot1} કે {slot2}, કયું ફાવશે?"],
        "close": ["સરસ! તો {slot1} meeting fix કરી દઉં?"],
        "ask_time": ["સરસ! તો કયો દિવસ અને time ફાવશે, {slot1} કે {slot2}?"],
        "reschedule": ["વાંધો નહીં. તો {slot1} કે {slot2} કેવું રહેશે?"],
    },
}


def variant(style: str, key: str, base: str, seed: str, uses: int = 0) -> str:
    """The base line or one of its variants: stable per seller, rotating when the move repeats in a call."""
    import zlib
    options = [base] + VARIANTS.get(style, {}).get(key, [])
    return options[(zlib.crc32(f"{seed}:{key}".encode()) + uses) % len(options)]
