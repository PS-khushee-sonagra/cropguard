# app.py - Crop Guard chat UI (one chat = one crop)
from lang import (chat_turn_multilingual, LANGS, t, step_label, risk_label,
                  conf_label, crop_label)
import asyncio, json, time, uuid
from pathlib import Path
import streamlit as st
from PIL import Image
from agent_core import new_context

BASE = Path(__file__).parent
UPLOADS = BASE / "Uploads"
UPLOADS.mkdir(exist_ok=True)
STORE = BASE / "chats.json"
DATA_DIR = BASE / "Data"
DATA_CROPS = sorted(
    (
        path.stem.title()
        for path in DATA_DIR.glob("*.json")
        if path.stem.casefold() != "treatments"
    ),
    key=str.casefold,
)
CROPS = ["Not sure", *DATA_CROPS, "Other"]

st.set_page_config(
    page_title="CropGuard — Farmer Crop Care Assistant",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- farmer-centric translations & helper ----------
UI_EXTRA = {
    "tagline": {
        "en": "Simple, practical crop health assistance for farmers",
        "hi": "किसानों के लिए सरल और उपयोगी फसल स्वास्थ्य सहायता",
        "gu": "ખેડૂતો માટે સરળ અને વ્યવહારુ પાક સ્વાસ્થ્ય સહાય",
    },
    "step1_title": {
        "en": "1. Select Crop & Photo",
        "hi": "1. फसल चुनें और फोटो लें",
        "gu": "1. પાક પસંદ કરો અને ફોટો લો",
    },
    "step1_desc": {
        "en": "Choose your crop and attach a clear close-up photo of an affected leaf, stem, or fruit.",
        "hi": "अपनी फसल चुनें और प्रभावित पत्ते, तने या फल की पास से साफ फोटो जोड़ें।",
        "gu": "તમારો પાક પસંદ કરો અને અસરગ્રસ્ત પાંદડા, દાંડી કે ફળનો સ્પષ્ટ નજીકથી ફોટો જોડો.",
    },
    "step2_title": {
        "en": "2. Disease & Weather Check",
        "hi": "2. रोग और मौसम की जाँच",
        "gu": "2. રોગ અને હવામાન તપાસ",
    },
    "step2_desc": {
        "en": "Checks visible symptoms, spots, and analyzes local weather for fungal disease risk.",
        "hi": "दिखने वाले लक्षणों, धब्बों की जाँच करता है तथा फफूंद के खतरे के लिए स्थानीय मौसम देखता है।",
        "gu": "દેખાતા લક્ષણો, ડાઘાઓ તપાસે છે અને ફૂગના જોખમ માટે સ્થાનિક હવામાન ચકાસે છે.",
    },
    "step3_title": {
        "en": "3. Safe Care & Support",
        "hi": "3. सुरक्षित देखभाल और सहायता",
        "gu": "3. સુરક્ષિત કાળજી અને સહાય",
    },
    "step3_desc": {
        "en": "Get simple organic care steps, precautions, and free government Kisan helpline support.",
        "hi": "सरल जैविक उपाय, सावधानियाँ और निःशुल्क सरकारी किसान हेल्पलाइन सहायता प्राप्त करें।",
        "gu": "સરળ જૈવિક ઉપાયો, સાવચેતીઓ અને મફત સરકારી કિસાન હેલ્પલાઇન સહાય મેળવો.",
    },
    "photo_instructions": {
        "en": "Upload a clear photo of an affected leaf, stem, fruit, or plant. Take the photo in daylight with steady hands.",
        "hi": "प्रभावित पत्ते, तने, फल या पौधे की साफ फोटो जोड़ें। दिन के उजाले में स्थिर हाथों से फोटो लें।",
        "gu": "અસરગ્રસ્ત પાંદડા, દાંડી, ફળ કે છોડનો સ્પષ્ટ ફોટો જોડો. દિવસના અજવાળામાં સ્થિર હાથે ફોટો લો.",
    },
    "photo_ready": {
        "en": "Photo attached! Ready to send with your message below.",
        "hi": "फोटो जुड़ गई है! नीचे अपना संदेश लिखकर भेजें।",
        "gu": "ફોટો જોડાઈ ગયો છે! નીચે તમારો સંદેશ લખીને મોકલો.",
    },
    "possible_problem": {
        "en": "Possible Crop Condition",
        "hi": "संभावित फसल समस्या",
        "gu": "સંભવિત પાક સમસ્યા",
    },
    "unverified_notice": {
        "en": "This is an automated image analysis hypothesis, not a laboratory-confirmed disease. Always consult your local KVK or agricultural officer before applying chemical sprays.",
        "hi": "यह फोटो पर आधारित शुरुआती अनुमान है, प्रयोगशाला द्वारा पुष्टि किया गया रोग नहीं। किसी भी रासायनिक छिड़काव से पहले अपने स्थानीय KVK या कृषि अधिकारी से पुष्टि अवश्य करें।",
        "gu": "આ ફોટો આધારિત પ્રાથમિક અંદાજ છે, પ્રયોગશાળા દ્વારા ખાતરી કરેલ રોગ નથી. કોઈપણ રાસાયણિક છંટકાવ પહેલાં તમારા સ્થાનિક KVK અથવા કૃષિ અધિકારી પાસેથી ખાતરી કરો.",
    },
    "crop_care_title": {
        "en": "Crop Care & Management",
        "hi": "फसल देखभाल और प्रबंधन",
        "gu": "પાકની કાળજી અને વ્યવસ્થાપન",
    },
    "organic_title": {
        "en": "Organic & Cultural Care",
        "hi": "जैविक और प्राकृतिक देखभाल",
        "gu": "જૈવિક અને કુદરતી સંભાળ",
    },
    "precaution_title": {
        "en": "Important Caution & Safety",
        "hi": "महत्वपूर्ण सावधानी और सुरक्षा",
        "gu": "મહત્વપૂર્ણ સાવચેતી અને સુરક્ષા",
    },
    "helpline_desc": {
        "en": "Kisan Call Centre (Toll-Free, Govt. of India): 1800-180-1551",
        "hi": "किसान कॉल सेंटर (निःशुल्क, भारत सरकार): 1800-180-1551",
        "gu": "કિસાન કોલ સેન્ટર (મફત, ભારત સરકાર): 1800-180-1551",
    },
    "active_crop_badge": {
        "en": "Current Crop Session",
        "hi": "वर्तमान फसल सत्र",
        "gu": "હાલનું પાક સત્ર",
    },
    "location_help": {
        "en": "Enter your village or city to check local weather and fungal disease risks.",
        "hi": "स्थानीय मौसम और फफूंद के खतरे की जाँच के लिए अपना गाँव या शहर लिखें।",
        "gu": "સ્થાનિક હવામાન અને ફૂગના જોખમ માટે તમારું ગામ અથવા શહેર લખો.",
    },
    "view_steps": {
        "en": "Technical Verification Details (Agent Steps)",
        "hi": "तकनीकी सत्यापन विवरण (एजेंट के कदम)",
        "gu": "તકનીકી ચકાસણી વિગતો (એજન્ટના પગલાં)",
    },
}

def tr(key, lang):
    if key in UI_EXTRA:
        d = UI_EXTRA[key]
        return d.get(lang) or d.get("en", key)
    return t(key, lang)

# ---------- custom farmer-first design system ----------
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;500;600;700&family=Noto+Sans+Gujarati:wght@400;500;600;700&display=swap');

    :root {
      --primary-green: #2E7D32;
      --dark-green: #1B5E20;
      --light-green: #E8F5E9;
      --accent-green: #4CAF50;
      --soft-sage: #F2F7F2;
      --warm-bg: #F7FAF7;
      --card-bg: #FFFFFF;
      --text-main: #1D3124;
      --text-muted: #4B6351;
      --border-light: #DCE7DD;
      --border-green: #A5D6A7;
      --warning-amber: #FFF9E6;
      --warning-border: #FFE082;
      --warning-text: #7A5300;
      --danger-red: #D32F2F;
      --danger-bg: #FFEBEE;
      --helpline-bg: #FFF3E0;
      --helpline-border: #FFB74D;
      --helpline-text: #E65100;
      --shadow-sm: 0 2px 6px rgba(27, 94, 32, 0.05);
      --shadow-md: 0 4px 16px rgba(27, 94, 32, 0.08);
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
    }

    /* Global Typography & Background */
    html, body, [data-testid="stAppViewContainer"] {
      font-family: 'Plus Jakarta Sans', 'Noto Sans Devanagari', 'Noto Sans Gujarati', system-ui, sans-serif !important;
      background-color: var(--warm-bg) !important;
      color: var(--text-main) !important;
    }

    /* Main Container Spacing */
    .main .block-container {
      padding-top: 1.5rem !important;
      padding-bottom: 5rem !important;
      max-width: 980px !important;
    }

    /* Streamlit Header Bar */
    header[data-testid="stHeader"] {
      background-color: transparent !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
      background-color: var(--soft-sage) !important;
      border-right: 1px solid var(--border-light) !important;
    }

    section[data-testid="stSidebar"] .block-container {
      padding-top: 1.25rem !important;
    }

    /* Farmer Brand Card in Sidebar */
    .sidebar-brand-card {
      background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
      color: white !important;
      padding: 16px 14px;
      border-radius: var(--radius-md);
      margin-bottom: 16px;
      box-shadow: var(--shadow-md);
      text-align: center;
    }
    .sidebar-brand-title {
      font-size: 1.35rem;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: white !important;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .sidebar-brand-tagline {
      font-size: 0.85rem;
      opacity: 0.95;
      color: #E8F5E9 !important;
      margin-top: 4px;
      font-weight: 500;
    }

    /* Sidebar Section Cards */
    .sidebar-card {
      background: white;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-md);
      padding: 14px;
      margin-top: 12px;
      margin-bottom: 12px;
      box-shadow: var(--shadow-sm);
    }

    .sidebar-card-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--dark-green);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Buttons */
    .stButton > button {
      border-radius: var(--radius-sm) !important;
      font-weight: 600 !important;
      font-size: 0.95rem !important;
      padding: 0.55rem 1.1rem !important;
      min-height: 44px !important;
      transition: all 0.2s ease !important;
    }

    .stButton > button[kind="primary"] {
      background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%) !important;
      border: none !important;
      color: white !important;
      box-shadow: 0 4px 12px rgba(46, 125, 50, 0.25) !important;
    }

    .stButton > button[kind="primary"]:hover {
      background: linear-gradient(135deg, #388E3C 0%, #2E7D32 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(46, 125, 50, 0.35) !important;
    }

    .stButton > button[kind="secondary"] {
      background: white !important;
      border: 1px solid var(--border-light) !important;
      color: var(--text-main) !important;
    }

    .stButton > button[kind="secondary"]:hover {
      border-color: var(--primary-green) !important;
      background-color: var(--light-green) !important;
      color: var(--dark-green) !important;
    }

    /* Welcome Hero Card */
    .welcome-hero {
      background: linear-gradient(145deg, #FFFFFF 0%, #F1F8F2 100%);
      border: 1px solid var(--border-green);
      border-radius: var(--radius-lg);
      padding: 28px 24px;
      margin-bottom: 22px;
      box-shadow: var(--shadow-md);
      text-align: center;
    }

    .welcome-badge {
      display: inline-block;
      background-color: var(--light-green);
      color: var(--dark-green);
      font-size: 0.85rem;
      font-weight: 700;
      padding: 5px 14px;
      border-radius: 30px;
      margin-bottom: 12px;
      border: 1px solid var(--border-green);
    }

    .welcome-title {
      font-size: 2.1rem;
      font-weight: 800;
      color: var(--dark-green);
      margin-bottom: 6px;
      letter-spacing: -0.5px;
    }

    .welcome-tagline {
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--primary-green);
      margin-bottom: 10px;
    }

    .welcome-desc {
      font-size: 0.98rem;
      color: var(--text-muted);
      max-width: 680px;
      margin: 0 auto 16px auto;
      line-height: 1.6;
    }

    /* 3 Step Cards */
    .steps-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }

    .step-card {
      background: white;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-md);
      padding: 18px 16px;
      text-align: left;
      box-shadow: var(--shadow-sm);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .step-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
      border-color: var(--border-green);
    }

    .step-icon {
      font-size: 1.8rem;
      margin-bottom: 8px;
      display: inline-block;
    }

    .step-title {
      font-size: 1rem;
      font-weight: 700;
      color: var(--dark-green);
      margin-bottom: 6px;
    }

    .step-desc {
      font-size: 0.88rem;
      color: var(--text-muted);
      line-height: 1.5;
    }

    /* Crop Selection Card */
    .crop-select-card {
      background: white;
      border: 2px solid var(--border-green);
      border-radius: var(--radius-lg);
      padding: 24px;
      box-shadow: var(--shadow-md);
      margin-bottom: 22px;
    }

    .crop-select-title {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--dark-green);
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .crop-select-help {
      font-size: 0.92rem;
      color: var(--text-muted);
      margin-bottom: 16px;
    }

    /* Helpline Banner */
    .helpline-banner {
      background: var(--helpline-bg);
      border: 1px solid var(--helpline-border);
      border-radius: var(--radius-md);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      box-shadow: var(--shadow-sm);
    }

    .helpline-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .helpline-icon {
      font-size: 1.6rem;
    }

    .helpline-text-title {
      font-weight: 700;
      color: var(--helpline-text);
      font-size: 1rem;
    }

    .helpline-text-sub {
      font-size: 0.86rem;
      color: #8D4004;
    }

    .helpline-phone-btn {
      background: #E65100;
      color: white !important;
      padding: 8px 18px;
      border-radius: 30px;
      font-weight: 700;
      font-size: 1.05rem;
      text-decoration: none !important;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 2px 8px rgba(230, 81, 0, 0.3);
    }

    /* Chat Session Header */
    .chat-session-header {
      background: white;
      border: 1px solid var(--border-light);
      border-left: 5px solid var(--primary-green);
      border-radius: var(--radius-md);
      padding: 14px 18px;
      margin-bottom: 18px;
      box-shadow: var(--shadow-sm);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .chat-crop-badge {
      font-size: 1.25rem;
      font-weight: 800;
      color: var(--dark-green);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .chat-crop-sub {
      font-size: 0.88rem;
      color: var(--text-muted);
      margin-top: 2px;
    }

    /* Chat Messages */
    [data-testid="stChatMessage"] {
      background: white !important;
      border: 1px solid var(--border-light) !important;
      border-radius: var(--radius-md) !important;
      padding: 16px !important;
      margin-bottom: 16px !important;
      box-shadow: var(--shadow-sm) !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:contains("👨‍🌾")) {
      background-color: #F3F9F4 !important;
      border-color: #CBE6D0 !important;
      margin-left: 1.5rem !important;
    }

    [data-testid="stChatMessageAvatar"] {
      background-color: var(--light-green) !important;
      border: 1px solid var(--border-green) !important;
    }

    /* Structured Results Styling */
    .crop-results-container {
      margin-top: 14px;
    }

    .result-card {
      background: white;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-md);
      padding: 16px;
      margin-bottom: 12px;
      box-shadow: var(--shadow-sm);
    }

    .diag-card {
      border-left: 5px solid var(--primary-green);
      background: #FAFCFA;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .card-title {
      font-size: 1rem;
      font-weight: 700;
      color: var(--dark-green);
    }

    .disease-name {
      font-size: 1.35rem;
      font-weight: 800;
      color: var(--text-main);
      margin-bottom: 8px;
    }

    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.82rem;
      font-weight: 700;
    }

    .conf-high {
      background: #E8F5E9;
      color: #1B5E20;
      border: 1px solid #A5D6A7;
    }

    .conf-med {
      background: #FFF8E1;
      color: #8D6E00;
      border: 1px solid #FFE082;
    }

    .conf-low {
      background: #FFEBEE;
      color: #C62828;
      border: 1px solid #FFCDD2;
    }

    .risk-high {
      background: #FFEBEE;
      color: #C62828;
      border: 1px solid #FFCDD2;
    }

    .risk-mod {
      background: #FFF8E1;
      color: #8D6E00;
      border: 1px solid #FFE082;
    }

    .risk-low {
      background: #E8F5E9;
      color: #1B5E20;
      border: 1px solid #A5D6A7;
    }

    .uncertainty-note {
      font-size: 0.88rem;
      color: #5D4037;
      background: #FBE9E7;
      border: 1px solid #FFCCBC;
      padding: 8px 12px;
      border-radius: var(--radius-sm);
      margin-top: 8px;
      line-height: 1.45;
    }

    .symptoms-card, .alt-card {
      background: #FAFCF9;
    }

    .section-label {
      font-size: 0.92rem;
      color: var(--dark-green);
      margin-bottom: 4px;
    }

    .section-content {
      font-size: 0.95rem;
      color: var(--text-main);
      line-height: 1.5;
    }

    .weather-card {
      border-left: 5px solid #0288D1;
      background: #F4FAFD;
    }

    .care-card {
      border-left: 5px solid #43A047;
      background: #F7FCF7;
    }

    .caution-box {
      background: var(--warning-amber);
      border: 1px solid var(--warning-border);
      border-radius: var(--radius-sm);
      padding: 12px 14px;
      margin-top: 10px;
    }

    .caution-title {
      font-weight: 700;
      color: var(--warning-text);
      font-size: 0.95rem;
      margin-bottom: 4px;
    }

    .caution-body {
      font-size: 0.9rem;
      color: #543E00;
      line-height: 1.5;
    }

    /* Upload Dropzone Container */
    .upload-card-wrapper {
      background: white;
      border: 2px dashed var(--border-green);
      border-radius: var(--radius-md);
      padding: 16px 18px;
      margin-bottom: 16px;
      box-shadow: var(--shadow-sm);
      transition: border-color 0.2s ease;
    }

    .upload-card-wrapper:hover {
      border-color: var(--primary-green);
    }

    .upload-card-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
    }

    .upload-card-icon {
      font-size: 1.7rem;
      background: var(--light-green);
      padding: 8px 10px;
      border-radius: 12px;
    }

    .upload-card-title {
      font-weight: 700;
      font-size: 1.02rem;
      color: var(--dark-green);
    }

    .upload-card-subtitle {
      font-size: 0.88rem;
      color: var(--text-muted);
    }

    .preview-badge {
      background: var(--light-green);
      color: var(--dark-green);
      font-size: 0.88rem;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      margin-top: 8px;
      margin-bottom: 8px;
      display: inline-block;
      border: 1px solid var(--border-green);
    }

    /* Metrics in weather */
    [data-testid="stMetric"] {
      background: white !important;
      border: 1px solid var(--border-light) !important;
      border-radius: var(--radius-sm) !important;
      padding: 10px 14px !important;
      box-shadow: var(--shadow-sm) !important;
    }

    [data-testid="stMetricLabel"] {
      font-size: 0.85rem !important;
      color: var(--text-muted) !important;
      font-weight: 600 !important;
    }

    [data-testid="stMetricValue"] {
      font-size: 1.25rem !important;
      font-weight: 800 !important;
      color: var(--dark-green) !important;
    }

    /* Mobile Responsiveness */
    @media (max-width: 768px) {
      .main .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
      }
      
      .steps-grid {
        grid-template-columns: 1fr !important;
      }
      
      .welcome-title {
        font-size: 1.55rem !important;
      }
      
      .welcome-hero {
        padding: 20px 14px !important;
      }
      
      .crop-select-card {
        padding: 16px !important;
      }
      
      .helpline-banner {
        flex-direction: column !important;
        gap: 12px !important;
        text-align: center !important;
      }
      
      .helpline-left {
        flex-direction: column !important;
      }
      
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:contains("👨‍🌾")) {
        margin-left: 0.5rem !important;
      }
      
      [data-testid="column"] {
        min-width: 48% !important;
        flex: 1 1 48% !important;
        margin-bottom: 8px !important;
      }
    }
    </style>
    """, unsafe_allow_html=True)

# Inject custom styling right after page config
inject_custom_css()

# ---------- storage ----------
def load_chats():
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_chats():
    try:
        STORE.write_text(json.dumps(st.session_state.chats, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    except Exception:
        pass

def new_chat(crop):
    cid = uuid.uuid4().hex[:8]
    created = time.time()
    when = time.strftime("%d %b %H:%M", time.localtime(created))
    st.session_state.chats[cid] = {
        "id": cid, "created": created, "crop": crop,
        "title": f"{crop} · {when}", "context": new_context(crop),
        "memory": [], "messages": [], "safety_version": 1,
        "legacy_results_notice": False}
    st.session_state.current = cid
    save_chats()

def nice_list(v):
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v).strip("[]").replace("'", "")

# ---------- state ----------
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
    chats0 = st.session_state.chats
    st.session_state.current = (max(chats0, key=lambda k: chats0[k]["created"])
                                if chats0 else None)
if "up_n" not in st.session_state:
    st.session_state.up_n = 0

lang = st.session_state.get("ui_lang", "en")

chats = st.session_state.chats
for saved_chat in chats.values():
    if saved_chat.get("safety_version") != 1:
        saved_chat.setdefault(
            "legacy_results_notice",
            bool(saved_chat.get("messages")),
        )
cid = st.session_state.current
chat = chats.get(cid) if cid else None

# ---------- sidebar ----------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand-card">
        <div class="sidebar-brand-title">🌿 CropGuard</div>
        <div class="sidebar-brand-tagline">🌾 Farmer Digital Assistant</div>
    </div>
    """, unsafe_allow_html=True)

    st.selectbox("🌐 Language / भाषा / ભાષા", list(LANGS),
                 format_func=lambda c: LANGS[c], key="ui_lang")
    lang = st.session_state.get("ui_lang", "en")

    if st.button(tr("new_chat", lang), use_container_width=True, type="primary"):
        st.session_state.current = None
        st.rerun()

    st.caption(f"📁 {tr('your_chats', lang)}")
    for k, c in sorted(chats.items(), key=lambda kv: kv[1]["created"], reverse=True):
        label = ("▶ " if k == cid else "") + c["title"]
        if st.button(label, key=f"open_{k}", use_container_width=True):
            st.session_state.current = k
            st.rerun()

    if chat:
        st.divider()
        st.markdown(f"""
        <div class="sidebar-card">
            <div class="sidebar-card-title">{tr("location_title", lang)}</div>
            <div style="font-size: 0.85rem; color: #536B58; margin-bottom: 8px;">
                {tr("location_help", lang)}
            </div>
        </div>
        """, unsafe_allow_html=True)

        ctx = chat["context"]
        city = st.text_input(tr("city", lang), value=ctx.get("city", ""), key=f"city_{cid}")
        use_coords = st.checkbox(tr("use_coords", lang), key=f"uc_{cid}")
        if use_coords:
            old_lat, old_lon = ctx.get("lat"), ctx.get("lon")
            lat = st.text_input("Latitude", value=str(old_lat if old_lat is not None else ""),
                                placeholder="For example: 20.0000", key=f"lat_{cid}")
            lon = st.text_input("Longitude", value=str(old_lon if old_lon is not None else ""),
                                placeholder="For example: 73.7800", key=f"lon_{cid}")
            ctx["city"] = ""
            ctx["lat"], ctx["lon"] = None, None
            if lat.strip() and lon.strip():
                try:
                    lat_value, lon_value = float(lat), float(lon)
                    if -90 <= lat_value <= 90 and -180 <= lon_value <= 180:
                        ctx["lat"], ctx["lon"], ctx["city"] = lat_value, lon_value, ""
                    else:
                        st.error("Enter valid coordinates, or leave both blank.")
                except ValueError:
                    st.error("Coordinates must be numbers.")
            elif not lat.strip() and not lon.strip():
                ctx["lat"], ctx["lon"], ctx["city"] = None, None, ""
            else:
                st.info("Enter both coordinates to use location-based weather.")

        elif city.strip() != ctx.get("city", ""):
            ctx["city"] = city.strip()
            ctx["lat"], ctx["lon"], ctx["place"] = None, None, ""   # look it up again
        if not ctx.get("city") and (ctx.get("lat") is None or ctx.get("lon") is None):
            st.info(tr("no_location", lang))
        if st.button(tr("delete_chat", lang), use_container_width=True):
            del chats[cid]
            st.session_state.current = None
            save_chats()
            st.rerun()

    st.divider()
    st.markdown(f"""
    <div class="sidebar-card">
        <div class="sidebar-card-title">💡 {tr("photo_tips", lang).splitlines()[0].replace('**', '')}</div>
        <div style="font-size: 0.88rem; color: #1D3124; line-height: 1.5;">
            📸 Close-up of <b>one</b> leaf<br>
            ☀️ Daylight, avoid shadows<br>
            📱 Keep phone camera steady
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background: #FFF3E0; border: 1px solid #FFB74D; border-radius: 12px; padding: 12px; text-align: center;">
        <div style="font-size: 0.85rem; font-weight: 700; color: #E65100;">📞 {tr("helpline", lang).replace('**', '')}</div>
        <div style="font-size: 1.15rem; font-weight: 800; color: #B73E00; margin: 4px 0;">1800-180-1551</div>
        <div style="font-size: 0.78rem; color: #8D4004;">Toll-free 24x7 Gov support</div>
    </div>
    """, unsafe_allow_html=True)

# ---------- message & structured results rendering ----------
def format_message_content(text):
    if not text:
        return ""
    lines = text.split("\n")
    formatted_lines = []
    for line in lines:
        line_s = line.strip()
        if "1800-180-1551" in line_s:
            formatted_lines.append(f"> 📞 **{line_s}**")
        elif ":" in line_s and not line_s.startswith("http") and len(line_s.split(":")[0]) < 35:
            prefix, rest = line_s.split(":", 1)
            formatted_lines.append(f"**{prefix.strip()}:** {rest.strip()}")
        else:
            formatted_lines.append(line)
    return "  \n".join(formatted_lines)

def render_cards(m, lang):
    d, w = m.get("diagnosis"), m.get("weather")
    treatment = m.get("treatment")

    if not d and not w and not treatment:
        return

    st.markdown('<div class="crop-results-container">', unsafe_allow_html=True)

    # 1, 2, 3: Possible crop problem, Observed symptoms, Confidence/Uncertainty info
    if d and "error" not in d:
        disease = str(d.get("disease", "-")).title()
        conf = str(d.get("confidence", "")).lower()
        conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
        conf_class = "conf-high" if conf == "high" else ("conf-med" if conf == "medium" else "conf-low")
        conf_text = conf_label(conf, lang)

        st.markdown(f"""
        <div class="result-card diag-card">
            <div class="card-header">
                <span class="card-title">🔍 {tr("possible_problem", lang)}</span>
                <span class="badge {conf_class}">{conf_icon} {tr("confidence", lang)}: {conf_text}</span>
            </div>
            <div class="disease-name">{disease}</div>
            <div class="uncertainty-note">⚠️ {tr("unverified_notice", lang)}</div>
        </div>
        """, unsafe_allow_html=True)

        sym = nice_list(d.get("symptoms", ""))
        what_i_see = d.get("what_i_see", "")
        display_sym = sym or what_i_see
        if display_sym:
            st.markdown(f"""
            <div class="result-card symptoms-card">
                <div class="section-label">📋 <b>{tr("noticed", lang)}</b>:</div>
                <div class="section-content">{display_sym}</div>
            </div>
            """, unsafe_allow_html=True)

        alts = d.get("alternatives")
        if alts:
            st.markdown(f"""
            <div class="result-card alt-card">
                <div class="section-label">🔄 <b>{tr("others", lang)}</b>:</div>
                <div class="section-content">{nice_list(alts)}</div>
            </div>
            """, unsafe_allow_html=True)

        if d.get("note"):
            st.warning(f"⚠️ {d['note']}")

    # 4: Relevant Weather Information & Fungal Risk
    if w and "error" not in w:
        risk = w.get("fungal_risk", "-")
        risk_icon = {"HIGH": "🔴", "MODERATE": "🟡", "LOW": "🟢"}.get(risk, "⚪")
        risk_class = "risk-high" if risk == "HIGH" else ("risk-mod" if risk == "MODERATE" else "risk-low")
        risk_text = risk_label(risk, lang)
        loc = w.get("location", "-")

        st.markdown(f"""
        <div class="result-card weather-card">
            <div class="card-header">
                <span class="card-title">🌦️ {tr("weather_for", lang)}: <b>{loc}</b></span>
                <span class="badge {risk_class}">{risk_icon} {tr("fungal", lang)}: {risk_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"🌡️ {tr('temp', lang)}", f"{w.get('temperature_2m', '-')} °C")
        c2.metric(f"💧 {tr('humidity', lang)}", f"{w.get('relative_humidity_2m', '-')} %")
        c3.metric(f"🌧️ {tr('rain3', lang)}", f"{w.get('rain_last_3_days_mm', '-')} mm")
        c4.metric(f"🍄 {tr('fungal', lang)}", f"{risk_icon} {risk_text}")

    # 5 & 6: Crop Care Guidance & Next Steps
    if treatment:
        if treatment.get("error"):
            st.markdown(f"""
            <div class="result-card" style="background: #FFFDE7; border-left: 5px solid #FBC02D;">
                <div class="section-label">ℹ️ <b>{tr("no_entry", lang)}</b></div>
                <div class="section-content" style="margin-top: 4px;">
                    {tr("helpline_desc", lang)}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            org = treatment.get("organic_control", [])
            chem = treatment.get("chemical_control")
            prev = treatment.get("prevention", [])

            st.markdown(f"""
            <div class="result-card care-card">
                <div class="card-header">
                    <span class="card-title">🌱 {tr("crop_care_title", lang)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if org:
                st.markdown(f"**🌱 {tr('organic_title', lang)}:**")
                for item in org:
                    st.markdown(f"- {item}")

            if prev:
                with st.expander("🛡️ Field Prevention & Monitoring Tips"):
                    for p_item in prev:
                        st.markdown(f"- {p_item}")

            if chem:
                st.markdown(f"""
                <div class="caution-box">
                    <div class="caution-title">⚠️ {tr("precaution_title", lang)}</div>
                    <div class="caution-body">{chem}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- start screen ----------
if chat is None:
    # 1. Welcoming Hero Banner
    st.markdown(f"""
    <div class="welcome-hero">
        <div class="welcome-badge">🌱 Farmer Crop Health Assistant</div>
        <div class="welcome-title">CropGuard</div>
        <div class="welcome-tagline">{tr("tagline", lang)}</div>
        <div class="welcome-desc">
            Quick, reliable, and practical agricultural help. Take a photo of an affected plant or leaf, or describe what you see in the field to receive instant disease checks, weather risk analysis, and safe care recommendations.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. 3 Visual Step Cards
    st.markdown(f"""
    <div class="steps-grid">
        <div class="step-card">
            <div class="step-icon">📸</div>
            <div class="step-title">{tr("step1_title", lang)}</div>
            <div class="step-desc">{tr("step1_desc", lang)}</div>
        </div>
        <div class="step-card">
            <div class="step-icon">🔍</div>
            <div class="step-title">{tr("step2_title", lang)}</div>
            <div class="step-desc">{tr("step2_desc", lang)}</div>
        </div>
        <div class="step-card">
            <div class="step-icon">🌿</div>
            <div class="step-title">{tr("step3_title", lang)}</div>
            <div class="step-desc">{tr("step3_desc", lang)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Prominent Crop Selection Card
    st.markdown(f"""
    <div class="crop-select-card">
        <div class="crop-select-title">🌾 {tr("which_crop", lang)}</div>
        <div class="crop-select-help">{tr("start_help", lang)}</div>
    </div>
    """, unsafe_allow_html=True)

    crop = st.selectbox(
        tr("which_crop", lang),
        CROPS,
        format_func=lambda c: crop_label(c, lang),
        key="start_crop",
        label_visibility="collapsed"
    )

    if st.button(f"🌱 {tr('start_btn', lang)}", type="primary", use_container_width=True):
        new_chat(crop)
        st.rerun()

    # 4. Emergency Helpline Banner
    st.markdown(f"""
    <div class="helpline-banner" style="margin-top: 24px;">
        <div class="helpline-left">
            <div class="helpline-icon">📞</div>
            <div>
                <div class="helpline-text-title">{tr("helpline", lang).replace('**', '')}</div>
                <div class="helpline-text-sub">Free 24x7 expert agricultural advice from Government of India</div>
            </div>
        </div>
        <a class="helpline-phone-btn" href="tel:18001801551">
            📞 1800-180-1551
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ---------- chat screen ----------
# Clean Active Session Header
st.markdown(f"""
<div class="chat-session-header">
    <div>
        <div class="chat-crop-badge">🌿 {crop_label(chat["crop"], lang)}</div>
        <div class="chat-crop-sub">{chat.get("title", "")} · {tr("chat_title", lang).format(crop=crop_label(chat["crop"], lang))}</div>
    </div>
    <div style="font-size: 0.85rem; color: #536B58; background: #E8F5E9; padding: 6px 12px; border-radius: 20px; font-weight: 600;">
        🌾 {tr("active_crop_badge", lang)}
    </div>
</div>
""", unsafe_allow_html=True)

if chat.get("legacy_results_notice"):
    st.info(
        "This saved conversation predates the current evidence checks. Earlier results remain "
        "visible for reference, but Crop Guard will not rely on them as verified facts. "
        "Add a new photo for an updated assessment."
    )

if not chat["messages"]:
    with st.chat_message("assistant", avatar="🌿"):
        st.markdown(tr("hello", lang))

for m in chat["messages"]:
    avatar = "👨‍🌾" if m["role"] == "user" else "🌿"
    with st.chat_message(m["role"], avatar=avatar):
        if m.get("image") and Path(m["image"]).exists():
            st.image(m["image"], width=240)
        st.markdown(format_message_content(m["content"]))
        if m["role"] == "assistant":
            if lang != "en" and m.get("reply_en"):
                with st.expander("🌐 English Translation"):
                    st.markdown(format_message_content(m["reply_en"]))
            render_cards(m, lang)
            if m.get("steps"):
                with st.expander(f"🔍 {tr('view_steps', lang)}"):
                    for s in m["steps"]:
                        st.write("•", step_label(s, lang))

# Large, Clear Photo Upload Dropzone
st.markdown(f"""
<div class="upload-card-wrapper">
    <div class="upload-card-header">
        <div class="upload-card-icon">📷</div>
        <div>
            <div class="upload-card-title">{tr("attach", lang)}</div>
            <div class="upload-card-subtitle">{tr("photo_instructions", lang)}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

photo = st.file_uploader(
    tr("attach", lang),
    type=["jpg", "jpeg", "png", "webp"],
    key=f"up_{cid}_{st.session_state.up_n}",
    label_visibility="collapsed"
)

if photo:
    st.markdown(f'<div class="preview-badge">✅ {tr("photo_ready", lang)}</div>', unsafe_allow_html=True)
    st.image(photo, width=240)

prompt = st.chat_input(tr("chat_input", lang))

if prompt:
    img_path = None
    if photo:
        img = Image.open(photo).convert("RGB")
        img.thumbnail((1024, 1024))                      # smaller = faster, saves quota
        p = UPLOADS / f"chat_{cid}_{int(time.time())}.jpg"
        img.save(p, "JPEG", quality=90)
        img_path = str(p)

    chat["messages"].append({"role": "user", "content": prompt, "image": img_path})
    with st.chat_message("user", avatar="👨‍🌾"):
        if img_path:
            st.image(img_path, width=240)
        st.markdown(prompt)

    chat["lang"] = lang
    with st.chat_message("assistant", avatar="🌿"):
        try:
            with st.status(f"🌱 {tr('thinking', lang)}", expanded=True) as status:
                res = asyncio.run(chat_turn_multilingual(
                    chat, prompt, img_path,
                    on_step=lambda s: st.write(step_label(s, lang))))
                status.update(label=f"✅ {tr('done', lang)}", state="complete", expanded=False)
        except Exception as e:
            chat["messages"].pop()
            st.error("Something went wrong. Check that Ollama is running, then try again.")
            st.exception(e)
            st.stop()

    chat["messages"].append({"role": "assistant", "content": res["reply"],
                             "diagnosis": res["diagnosis"], "weather": res["weather"],
                             "treatment": res.get("treatment"),
                             "steps": res["steps"], "reply_en": res.get("reply_en")})
    st.session_state.up_n += 1                           # clears the photo box
    save_chats()
    st.rerun()