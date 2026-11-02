# cards.py - Pure card logic and UI rendering components without top-level Streamlit script execution.
import html
import streamlit as st
from agent_core import is_expert_verified
from lang import conf_label, risk_label, t

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
        "hi": "अपनी फसल चुनें और प्रभावित पत्ते, तने या फल की साफ पास से फोटो जोड़ें।",
        "gu": "તમારો પાક પસંદ કરો અને અસરગ્રસ્ત પાંદડા, દાંડી કે ફળનો સ્પષ્ટ નજીકથી ફોટો જોડો.",
    },
    "step2_title": {
        "en": "2. Disease & Weather Check",
        "hi": "2. रोग और मौसम की जाँच",
        "gu": "2. રોગ અને હવામાન તપાસ",
    },
    "step2_desc": {
        "en": "Checks visible symptoms, spots, and analyzes local weather for fungal disease risk.",
        "hi": "लक्षणों और धब्बों की जाँच करता है तथा फफूंद के खतरे के लिए स्थानीय मौसम देखता है।",
        "gu": "લક્ષણો અને ડાઘાઓ તપાસે છે અને ફૂગના જોખમ માટે સ્થાનિક હવામાન ચકાસે છે.",
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

def tr(key: str, lang: str) -> str:
    if key in UI_EXTRA:
        d = UI_EXTRA[key]
        return d.get(lang) or d.get("en", key)
    return t(key, lang)

def nice_list(v):
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v).strip("[]").replace("'", "")

def treatment_card_status(treatment: dict | None) -> str:
    if treatment is None or treatment.get("withheld"):
        return "withheld"
    if not is_expert_verified(treatment):
        return "draft"
    return "verified"

def render_cards(m, lang):
    d, w = m.get("diagnosis"), m.get("weather")
    treatment = m.get("treatment")

    if not d and not w and not treatment:
        return

    st.markdown('<div class="crop-results-container">', unsafe_allow_html=True)

    # 1, 2, 3: Possible crop problem, Observed symptoms, Confidence/Uncertainty info
    if d and "error" not in d:
        disease = html.escape(str(d.get("disease", "-")).title())
        conf = str(d.get("confidence", "")).lower()
        conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
        conf_class = "conf-high" if conf == "high" else ("conf-med" if conf == "medium" else "conf-low")
        conf_text = html.escape(conf_label(conf, lang))

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
            escaped_sym = html.escape(str(display_sym))
            st.markdown(f"""
            <div class="result-card symptoms-card">
                <div class="section-label">📋 <b>{tr("noticed", lang)}</b>:</div>
                <div class="section-content">{escaped_sym}</div>
            </div>
            """, unsafe_allow_html=True)

        alts = d.get("alternatives")
        if alts:
            escaped_alts = html.escape(str(nice_list(alts)))
            st.markdown(f"""
            <div class="result-card alt-card">
                <div class="section-label">🔄 <b>{tr("others", lang)}</b>:</div>
                <div class="section-content">{escaped_alts}</div>
            </div>
            """, unsafe_allow_html=True)

        if d.get("note"):
            st.warning(f"⚠️ {d['note']}")

    # 4: Relevant Weather Information & Fungal Risk
    if w and "error" not in w:
        risk = w.get("fungal_risk", "-")
        risk_icon = {"HIGH": "🔴", "MODERATE": "🟡", "LOW": "🟢"}.get(risk, "⚪")
        risk_class = "risk-high" if risk == "HIGH" else ("risk-mod" if risk == "MODERATE" else "risk-low")
        risk_text = html.escape(risk_label(risk, lang))
        loc = html.escape(str(w.get("location", "-")))

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
    status = treatment_card_status(treatment)
    if status == "withheld":
        st.info("Treatment guidance withheld pending review.")
    elif treatment.get("error"):
        st.markdown(f"""
        <div class="result-card" style="background: #FFFDE7; border-left: 5px solid #FBC02D;">
            <div class="section-label">ℹ️ <b>{tr("no_entry", lang)}</b></div>
            <div class="section-content" style="margin-top: 4px;">
                {tr("helpline_desc", lang)}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        if status == "draft":
            st.markdown(
                '<div class="badge conf-low" style="margin-bottom: 8px; display: inline-block;">⚠️ Draft, not expert-reviewed</div>',
                unsafe_allow_html=True,
            )

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
            escaped_chem = html.escape(str(chem))
            st.markdown(f"""
            <div class="caution-box">
                <div class="caution-title">⚠️ {tr("precaution_title", lang)}</div>
                <div class="caution-body">{escaped_chem}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

