# lang.py - Hindi and Gujarati support. A translation layer only, no agent logic.
import os, re
from agent_core import chat_turn, ollama_chat_with_retry, DISCLAIMER

LANGS = {"en": "English", "hi": "हिन्दी", "gu": "ગુજરાતી"}
_NAMES = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}
TRANSLATE_MODEL = os.getenv("TRANSLATE_MODEL", "gemma3:4b")

# Fixed text, never produced by the model. Have a native speaker check these.
DISCLAIMER_T = {
    "hi": ("कृपया छिड़काव से पहले अपने स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से "
           "पुष्टि कर लें। किसान कॉल सेंटर (निःशुल्क): 1800-180-1551"),
    "gu": ("કૃપા કરીને છંટકાવ કરતા પહેલાં તમારા સ્થાનિક કૃષિ વિજ્ઞાન કેન્દ્ર (KVK) અથવા "
           "કૃષિ અધિકારી પાસેથી ખાતરી કરી લો. કિસાન કોલ સેન્ટર (મફત): 1800-180-1551"),
}

UI = {
    "new_chat": {"en": "➕ New chat", "hi": "➕ नई चैट", "gu": "➕ નવી ચેટ"},
    "your_chats": {"en": "Your chats (one crop per chat)", "hi": "आपकी चैट (हर चैट में एक फसल)",
                   "gu": "તમારી ચેટ (દરેક ચેટમાં એક પાક)"},
    "location_title": {"en": "📍 Location for this chat", "hi": "📍 इस चैट के लिए स्थान",
                       "gu": "📍 આ ચેટ માટે સ્થળ"},
    "city": {"en": "City or village", "hi": "शहर या गाँव", "gu": "શહેર અથવા ગામ"},
    "use_coords": {"en": "Use coordinates instead", "hi": "इसके बजाय निर्देशांक (coordinates) इस्तेमाल करें",
                   "gu": "તેના બદલે કોઓર્ડિનેટ્સ વાપરો"},
    "delete_chat": {"en": "🗑️ Delete this chat", "hi": "🗑️ यह चैट हटाएं", "gu": "🗑️ આ ચેટ કાઢી નાખો"},
    "photo_tips": {
        "en": "**Photo tips**  \n- Close-up of **one** leaf  \n- Daylight, no shadow  \n- Keep the camera steady",
        "hi": "**फोटो के सुझाव**  \n- सिर्फ़ **एक** पत्ते की पास से फोटो लें  \n- दिन की रोशनी में लें, छाया न हो  \n- कैमरा स्थिर रखें",
        "gu": "**ફોટા માટે સૂચનો**  \n- માત્ર **એક** પાંદડાનો નજીકથી ફોટો લો  \n- દિવસના અજવાળામાં લો, પડછાયો ન હોય  \n- કેમેરો સ્થિર રાખો"},
    "helpline": {"en": "**Kisan Call Centre (free)**", "hi": "**किसान कॉल सेंटर (निःशुल्क)**",
                 "gu": "**કિસાન કોલ સેન્ટર (મફત)**"},
    "start_title": {"en": "Start a new chat", "hi": "नई चैट शुरू करें", "gu": "નવી ચેટ શરૂ કરો"},
    "start_help": {
        "en": "Each chat is about **one crop**. For a different crop, start another chat. Nothing is mixed between chats.",
        "hi": "हर चैट **एक फसल** के बारे में होती है। दूसरी फसल के लिए नई चैट शुरू करें। चैट आपस में मिलती नहीं हैं।",
        "gu": "દરેક ચેટ **એક પાક** વિશે હોય છે. બીજા પાક માટે નવી ચેટ શરૂ કરો. ચેટ એકબીજામાં ભળતી નથી."},
    "which_crop": {"en": "Which crop do you want to talk about?", "hi": "आप किस फसल के बारे में बात करना चाहते हैं?",
                   "gu": "તમે કયા પાક વિશે વાત કરવા માંગો છો?"},
    "start_btn": {"en": "Start chat", "hi": "चैट शुरू करें", "gu": "ચેટ શરૂ કરો"},
    "chat_title": {"en": "{crop} chat", "hi": "{crop} चैट", "gu": "{crop} ચેટ"},
    "hello": {
        "en": ("Hello! 👋 I'm Crop Guard. Attach a close photo of one affected leaf below, and tell me what "
               "you see (spots, yellowing, when it started). After that you can keep asking me questions about this crop."),
        "hi": ("नमस्ते! 👋 मैं क्रॉप गार्ड हूँ। नीचे प्रभावित पत्ते की पास से खींची फोटो जोड़ें और बताएं कि आपको "
               "क्या दिख रहा है (धब्बे, पीलापन, कब शुरू हुआ)। इसके बाद आप इस फसल के बारे में सवाल पूछ सकते हैं।"),
        "gu": ("નમસ્તે! 👋 હું ક્રૉપ ગાર્ડ છું. નીચે અસરગ્રસ્ત પાંદડાનો નજીકથી લીધેલો ફોટો જોડો અને તમને શું "
               "દેખાય છે તે જણાવો (ડાઘા, પીળાશ, ક્યારે શરૂ થયું). ત્યારબાદ તમે આ પાક વિશે પ્રશ્નો પૂછી શકો છો.")},
    "attach": {"en": "📷 Attach a leaf photo to your next message",
               "hi": "📷 अगले संदेश के साथ पत्ते की फोटो जोड़ें",
               "gu": "📷 આગલા સંદેશ સાથે પાંદડાનો ફોટો જોડો"},
    "chat_input": {"en": "Type your message (for a photo, add a few words about what you see)",
                   "hi": "अपना संदेश लिखें (फोटो के साथ कुछ शब्द जोड़ें)",
                   "gu": "તમારો સંદેશ લખો (ફોટા સાથે થોડા શબ્દો ઉમેરો)"},
    "thinking": {"en": "Thinking...", "hi": "सोच रहा हूँ...", "gu": "વિચારી રહ્યો છું..."},
    "done": {"en": "Done", "hi": "पूरा हुआ", "gu": "પૂરું થયું"},
    "how_decided": {"en": "How the agent decided", "hi": "एजेंट ने कैसे तय किया", "gu": "એજન્ટે કેવી રીતે નક્કી કર્યું"},
    "no_entry": {"en": "No verified entry. Contact your KVK.",
                 "hi": "कोई सत्यापित प्रविष्टि नहीं। अपने KVK से संपर्क करें।",
                 "gu": "કોઈ ચકાસાયેલ નોંધ નથી. તમારા KVK નો સંપર્ક કરો."},
    "no_location": {
        "en": "📍 No location set. Add your city in the sidebar to get a local weather check.",
        "hi": "📍 कोई स्थान सेट नहीं है। स्थानीय मौसम की जाँच के लिए साइडबार में अपना शहर लिखें।",
        "gu": "📍 કોઈ સ્થળ સેટ કરેલ નથી. સ્થાનિક હવામાન તપાસ માટે સાઇડબારમાં તમારું શહેર લખો."},
    "temp": {"en": "Temperature", "hi": "तापमान", "gu": "તાપમાન"},
    "humidity": {"en": "Humidity", "hi": "नमी", "gu": "ભેજ"},
    "rain3": {"en": "Rain (3 days)", "hi": "बारिश (3 दिन)", "gu": "વરસાદ (3 દિવસ)"},
    "fungal": {"en": "Fungal risk", "hi": "फफूंद का खतरा", "gu": "ફૂગનું જોખમ"},
    "crop": {"en": "Crop", "hi": "फसल", "gu": "પાક"},
    "confidence": {"en": "Confidence", "hi": "विश्वास स्तर", "gu": "વિશ્વાસ સ્તર"},
    "noticed": {"en": "What we noticed", "hi": "हमने क्या देखा", "gu": "અમે શું જોયું"},
    "others": {"en": "Other possibilities", "hi": "अन्य संभावनाएँ", "gu": "અન્ય શક્યતાઓ"},
    "weather_for": {"en": "Weather for", "hi": "मौसम का स्थान", "gu": "હવામાનનું સ્થળ"},
    "no_translation": {
        "en": "",
        "hi": "(अनुवाद उपलब्ध नहीं हो सका, इसलिए नीचे अंग्रेज़ी में जवाब दिखाया जा रहा है।)",
        "gu": "(અનુવાદ ઉપલબ્ધ થઈ શક્યો નથી, તેથી નીચે અંગ્રેજીમાં જવાબ બતાવ્યો છે.)"},
    "tagline": {
        "en": "Simple, practical crop health assistance for farmers",
        "hi": "किसानों के लिए सरल और उपयोगी फसल स्वास्थ्य सहायता",
        "gu": "ખેડૂતો માટે સરળ અને વ્યવહારુ પાક સ્વાસ્થ્ય સહાય"},
    "step1_title": {
        "en": "1. Select Crop & Photo",
        "hi": "1. फसल चुनें और फोटो लें",
        "gu": "1. પાક પસંદ કરો અને ફોટો લો"},
    "step1_desc": {
        "en": "Choose your crop and attach a clear close-up photo of an affected leaf, stem, or fruit.",
        "hi": "अपनी फसल चुनें और प्रभावित पत्ते, तने या फल की साफ पास से फोटो जोड़ें।",
        "gu": "તમારો પાક પસંદ કરો અને અસરગ્રસ્ત પાંદડા, દાંડી કે ફળનો સ્પષ્ટ નજીકથી ફોટો જોડો."},
    "step2_title": {
        "en": "2. Disease & Weather Check",
        "hi": "2. रोग और मौसम की जाँच",
        "gu": "2. રોગ અને હવામાન તપાસ"},
    "step2_desc": {
        "en": "Checks visible symptoms, spots, and analyzes local weather for fungal disease risk.",
        "hi": "लक्षणों और धब्बों की जाँच करता है तथा फफूंद के खतरे के लिए स्थानीय मौसम देखता है।",
        "gu": "લક્ષણો અને ડાઘાઓ તપાસે છે અને ફૂગના જોખમ માટે સ્થાનિક હવામાન ચકાસે છે."},
    "step3_title": {
        "en": "3. Safe Care & Support",
        "hi": "3. सुरक्षित देखभाल और सहायता",
        "gu": "3. સુરક્ષિત કાળજી અને સહાય"},
    "step3_desc": {
        "en": "Get simple organic care steps, precautions, and free government Kisan helpline support.",
        "hi": "सरल जैविक उपाय, सावधानियाँ और निःशुल्क सरकारी किसान हेल्पलाइन सहायता प्राप्त करें।",
        "gu": "સરળ જૈવિક ઉપાયો, સાવચેતીઓ અને મફત સરકારી કિસાન હેલ્પલાઇન સહાય મેળવો."},
    "photo_instructions": {
        "en": "Upload a clear photo of an affected leaf, stem, fruit, or plant. Take the photo in daylight with steady hands.",
        "hi": "प्रभावित पत्ते, तने, फल या पौधे की साफ फोटो जोड़ें। दिन के उजाले में स्थिर हाथों से फोटो लें।",
        "gu": "અસરગ્રસ્ત પાંદડા, દાંડી, ફળ કે છોડનો સ્પષ્ટ ફોટો જોડો. દિવસના અજવાળામાં સ્થિર હાથે ફોટો લો."},
    "photo_ready": {
        "en": "Photo attached! Ready to send with your message below.",
        "hi": "फोटो जुड़ गई है! नीचे अपना संदेश लिखकर भेजें।",
        "gu": "ફોટો જોડાઈ ગયો છે! નીચે તમારો સંદેશ લખીને મોકલો."},
    "possible_problem": {
        "en": "Possible Crop Condition",
        "hi": "संभावित फसल समस्या",
        "gu": "સંભવિત પાક સમસ્યા"},
    "unverified_notice": {
        "en": "This is an automated image analysis hypothesis, not a laboratory-confirmed disease. Always consult your local KVK or agricultural officer before applying chemical sprays.",
        "hi": "यह फोटो पर आधारित शुरुआती अनुमान है, प्रयोगशाला द्वारा पुष्टि किया गया रोग नहीं। किसी भी रासायनिक छिड़काव से पहले अपने स्थानीय KVK या कृषि अधिकारी से पुष्टि अवश्य करें।",
        "gu": "આ ફોટો આધારિત પ્રાથમિક અંદાજ છે, પ્રયોગશાળા દ્વારા ખાતરી કરેલ રોગ નથી. કોઈપણ રાસાયણિક છંટકાવ પહેલાં તમારા સ્થાનિક KVK અથવા કૃષિ અધિકારી પાસેથી ખાતરી કરો."},
    "crop_care_title": {
        "en": "Crop Care & Management",
        "hi": "फसल देखभाल और प्रबंधन",
        "gu": "પાકની કાળજી અને વ્યવસ્થાપન"},
    "organic_title": {
        "en": "Organic & Cultural Care",
        "hi": "जैविक और प्राकृतिक देखभाल",
        "gu": "જૈવિક અને કુદરતી સંભાળ"},
    "precaution_title": {
        "en": "Important Caution & Safety",
        "hi": "महत्वपूर्ण सावधानी और सुरक्षा",
        "gu": "મહત્વપૂર્ણ સાવચેતી અને સુરક્ષા"},
    "helpline_desc": {
        "en": "Kisan Call Centre (Toll-Free, Govt. of India): 1800-180-1551",
        "hi": "किसान कॉल सेंटर (निःशुल्क, भारत सरकार): 1800-180-1551",
        "gu": "કિસાન કોલ સેન્ટર (મફત, ભારત સરકાર): 1800-180-1551"},
    "active_crop_badge": {
        "en": "Current Crop Session",
        "hi": "वर्तमान फसल सत्र",
        "gu": "હાલનું પાક સત્ર"},
    "location_help": {
        "en": "Enter your village or city to check local weather and fungal disease risks.",
        "hi": "स्थानीय मौसम और फफूंद के खतरे की जाँच के लिए अपना गाँव या शहर लिखें।",
        "gu": "સ્થાનિક હવામાન અને ફૂગના જોખમ માટે તમારું ગામ અથવા શહેર લખો."},
    "view_steps": {
        "en": "Technical Verification Details (Agent Steps)",
        "hi": "तकनीकी सत्यापन विवरण (एजेंट के कदम)",
        "gu": "તકનીકી ચકાસણી વિગતો (એજન્ટના પગલાં)"},
    "assistant_name": {
        "en": "CropGuard Assistant",
        "hi": "क्रॉपगार्ड सहायक",
        "gu": "ક્રોપગાર્ડ સહાયક"},
    "farmer_label": {
        "en": "Farmer",
        "hi": "किसान",
        "gu": "ખેડૂત"},
}

STEPS = {
    "🔍 Looking at your photo": {"hi": "🔍 आपकी फोटो देख रहा हूँ", "gu": "🔍 તમારો ફોટો જોઈ રહ્યો છું"},
    "🌦️ Checking the weather": {"hi": "🌦️ मौसम देख रहा हूँ", "gu": "🌦️ હવામાન તપાસી રહ્યો છું"},
    "📍 Finding your location": {"hi": "📍 आपका स्थान ढूँढ रहा हूँ", "gu": "📍 તમારું સ્થળ શોધી રહ્યો છું"},
    "📖 Looking up verified treatment": {"hi": "📖 जाँची हुई उपचार जानकारी देख रहा हूँ",
                                         "gu": "📖 ચકાસાયેલ ઉપચાર માહિતી જોઈ રહ્યો છું"},
    "🧐 Double-checking the answer": {"hi": "🧐 जवाब दोबारा जाँच रहा हूँ", "gu": "🧐 જવાબ ફરી તપાસી રહ્યો છું"},
}
RISK = {"HIGH": {"hi": "ज़्यादा", "gu": "વધુ"}, "MODERATE": {"hi": "मध्यम", "gu": "મધ્યમ"},
        "LOW": {"hi": "कम", "gu": "ઓછું"}}
CONF = {"high": {"hi": "ऊँचा", "gu": "ઊંચો"}, "medium": {"hi": "मध्यम", "gu": "મધ્યમ"},
        "low": {"hi": "कम", "gu": "ઓછો"}}
CROPS_T = {
    "Not sure": {"hi": "पता नहीं", "gu": "ખબર નથી"}, "Tomato": {"hi": "टमाटर", "gu": "ટામેટા"},
    "Potato": {"hi": "आलू", "gu": "બટાકા"}, "Grape": {"hi": "अंगूर", "gu": "દ્રાક્ષ"},
    "Cotton": {"hi": "कपास", "gu": "કપાસ"}, "Groundnut": {"hi": "मूंगफली", "gu": "મગફળી"},
    "Onion": {"hi": "प्याज", "gu": "ડુંગળી"}, "Wheat": {"hi": "गेहूँ", "gu": "ઘઉં"},
    "Pomegranate": {"hi": "अनार", "gu": "દાડમ"}, "Other": {"hi": "अन्य", "gu": "અન્ય"},
}

def t(key, lang):
    d = UI.get(key, {})
    return d.get(lang) or d.get("en", key)

def step_label(s, lang):
    return STEPS.get(s, {}).get(lang, s) if lang != "en" else s

def risk_label(v, lang):
    return RISK.get(v, {}).get(lang, v) if lang != "en" else v

def conf_label(v, lang):
    return CONF.get(str(v).lower(), {}).get(lang, str(v).title()) if lang != "en" else str(v).title()

def crop_label(name, lang):
    local = CROPS_T.get(name, {}).get(lang)
    return f"{local} · {name}" if (lang != "en" and local) else name

# ---------- language detection ----------
_HI = re.compile(r"[\u0900-\u097F]")
_GU = re.compile(r"[\u0A80-\u0AFF]")

def detect_script(text):
    """Hindi or Gujarati if the text uses that script, else None (Marathi also uses the Hindi script)."""
    g, d = len(_GU.findall(text)), len(_HI.findall(text))
    if g == 0 and d == 0:
        return None
    return "gu" if g >= d else "hi"

# ---------- translation ----------
_DIG = str.maketrans("०१२३४५६७८९૦૧૨૩૪૫૬૭૮૯", "01234567890123456789")
_NUM = re.compile(r"\d+(?:\.\d+)?")
_LATIN = re.compile(r"[A-Za-z]{4,}")

def _nums(s):
    return sorted(_NUM.findall(s.translate(_DIG)))

def _ask(system, text):
    r = ollama_chat_with_retry(
        model=TRANSLATE_MODEL,
        options={"temperature": 0},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
    )
    return r["message"]["content"].strip()

def to_english(text, lang):
    system = (f"Translate the farmer's message from {_NAMES[lang]} into plain English. It may be written in "
              "Roman letters (for example Hinglish). Keep numbers and place names. Local crop words: "
              "kapas/kapaas=cotton, mungfali/sing/magfali=groundnut, kanda/pyaaz/dungli=onion, "
              "tamatar/tameta=tomato, aloo/batata=potato, angoor/draksh=grape, anar/dadam=pomegranate, "
              "gehun/ghau=wheat. Do not answer the message and do not add anything. "
              "If it is already English, return it unchanged. Output only the translation.")
    try:
        return _ask(system, text) or text
    except Exception:
        return text

_SCRIPT = "\u0900-\u097F\u0A80-\u0AFF"

def tidy(s):
    """Put a space where a Hindi/Gujarati word touches an English word."""
    s = re.sub(f"([{_SCRIPT}])([A-Za-z])", r"\1 \2", s)
    return re.sub(f"([A-Za-z])([{_SCRIPT}])", r"\1 \2", s)

def from_english(report, lang):
    if lang == "en":
        return report
    had_disclaimer = DISCLAIMER in report
    body = report.replace(DISCLAIMER, "").strip()
    out = ""
    if body:
        system = (f"Translate this farm advice into simple, everyday {_NAMES[lang]} that a farmer understands. "
                  "Rules: do not add, remove or change any advice. Never add product names, chemical names or "
                  "doses. Keep every number exactly as written. Keep line breaks, dashes and markdown symbols. "
                  "Translate every ordinary English word (such as bulb, root, leaf) into the target language. "
                  "Keep only disease names in English, in brackets. Write complete sentences. Keep names of "
                  "organisations and websites in English. Output only the translation.")
        try:
            out = _ask(system, body)
            new_words = ({w.lower() for w in _LATIN.findall(out)}
                         - {w.lower() for w in _LATIN.findall(body)})
            if not out or _nums(out) != _nums(body) or new_words:
                raise ValueError("translation failed the safety check")
            out = tidy(out)
        except Exception:
            out = (t("no_translation", lang) + "\n\n" + body).strip()
    if had_disclaimer:
        out = (out + "\n\n" + DISCLAIMER_T[lang]).strip()
    return out

# ---------- the wrapper the app calls ----------
async def chat_turn_multilingual(conv, user_text, image_path=None, on_step=None):
    lang = detect_script(user_text) or conv.get("lang", "en")
    english = user_text if lang == "en" else to_english(user_text, lang)
    out = await chat_turn(conv, english, image_path, on_step)      # your existing agent, unchanged
    out["lang"] = lang
    out["reply_en"] = out["reply"]
    out["reply"] = from_english(out["reply"], lang)
    return out