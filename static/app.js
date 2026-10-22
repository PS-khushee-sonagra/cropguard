/**
 * CropGuard Web UI Client Application
 * Clean, Simple & Elegant AI Crop Health Advisor
 * Backed by MCP Tools, Ollama Vision (qwen2.5vl:7b), and LLM (llama3.2:3b)
 */

// ---------------------------------------------------------------------------
// Translations & Localized Strings (Farmer Friendly)
// ---------------------------------------------------------------------------
const I18N = {
  en: {
    tagline: "Crop Pest & Disease Assistant • फसल रक्षक",
    weatherChecking: "Checking weather...",
    weatherFavorable: "✓ Low Pest Risk",
    weatherRisk: "⚠️ Elevated Pest Risk",
    weatherOffline: "Weather offline",
    welcome: "Namaste! I am your <strong>CropGuard AI Advisor</strong>. You can ask me any question about pests, diseases, or damage on your <strong>Cotton, Tomato, or Wheat</strong> crops.<br><br>💡 <strong>New:</strong> You can now <strong>attach or drag-and-drop a crop photo (📷)</strong> for instant AI visual diagnosis! You can also speak using the <strong>Microphone</strong>.",
    quickPrompts: "💡 Common farmer questions:",
    placeholder: "Describe symptoms or upload a crop photo for visual diagnosis...",
    disclaimer: "<strong>Advisory Notice:</strong> CropGuard provides risk assessments grounded in ICAR & FAO agricultural records. It is not an absolute laboratory diagnosis. For severe infestations, consult your local <strong>Krishi Vigyan Kendra (KVK)</strong> or call Kisan Call Centre at <strong>1800-180-1551</strong>.",
    thinking: "Consulting agricultural knowledge base & checking local weather...",
    thinkingVision: "Analyzing crop photo with AI Vision & verifying knowledge base...",
    clear: "Clear conversation",
    listen: "🔊 Listen",
    stopAudio: "⏹ Stop",
    viewTrace: "🔍 View Agent Tool Trace",
    farmer: "Farmer",
    advisor: "CropGuard AI Advisor",
    speechLang: "en-IN",
    photoReady: "🌿 Photo attached • Visual AI ready",
    visObsTitle: "📸 AI Visual Observation"
  },
  hi: {
    tagline: "कृषि कीट एवं रोग जोखिम सलाहकार • फसल रक्षक",
    weatherChecking: "मौसम की जांच हो रही है...",
    weatherFavorable: "✓ अनुकूल मौसम • कम कीट खतरा",
    weatherRisk: "⚠️ बढ़ा हुआ कीट/रोग खतरा",
    weatherOffline: "मौसम अनुपलब्ध",
    welcome: "नमस्ते किसान भाई! मैं आपका <strong>CropGuard AI सलाहकार</strong> हूँ। आप कपास, टमाटर या गेहूं की फसल में किसी भी कीट या रोग के बारे में पूछ सकते हैं।<br><br>💡 <strong>नया फीचर:</strong> अब आप सटीक जांच के लिए <strong>पौधे की फोटो (📷) अपलोड</strong> कर सकते हैं! आप <strong>माइक</strong> दबाकर बोल भी सकते हैं।",
    quickPrompts: "💡 किसानों के सामान्य प्रश्न:",
    placeholder: "लक्षण बताएं या पौधे की फोटो अपलोड करें...",
    disclaimer: "<strong>सलाह सूचना:</strong> CropGuard की जानकारी ICAR और FAO के कृषि रिकॉर्ड पर आधारित है। गंभीर समस्या होने पर अपने नजदीकी <strong>कृषि विज्ञान केंद्र (KVK)</strong> से संपर्क करें या <strong>1800-180-1551</strong> पर कॉल करें।",
    thinking: "कृषि ज्ञानकोष और स्थानीय मौसम का विश्लेषण किया जा रहा है...",
    thinkingVision: "AI विजन द्वारा फोटो का विश्लेषण और ज्ञानकोष की जांच हो रही है...",
    clear: "बातचीत साफ करें",
    listen: "🔊 सुनें",
    stopAudio: "⏹ रोकें",
    viewTrace: "🔍 टूल ट्रेस देखें",
    farmer: "किसान",
    advisor: "CropGuard AI सलाहकार",
    speechLang: "hi-IN",
    photoReady: "🌿 फोटो संलग्न • AI दृष्टि विश्लेषण तैयार",
    visObsTitle: "📸 AI दृश्य अवलोकन"
  },
  mr: {
    tagline: "पीक कीड व रोग सल्लागार • शेतकरी मित्र",
    weatherChecking: "हवामान तपासत आहे...",
    weatherFavorable: "✓ अनुकूल हवामान • कमी धोका",
    weatherRisk: "⚠️ वाढलेला कीड/रोग धोका",
    weatherOffline: "हवामान उपलब्ध नाही",
    welcome: "नमस्कार शेतकरी बंधूंनो! मी तुमचा <strong>CropGuard AI सल्लागार</strong> आहे. तुम्ही कापूस, टोमॅटो किंवा गहू पिकावरील रोगांविषयी विचारू शकता.<br><br>💡 <strong>नवीन:</strong> आता अचूक निदानासाठी <strong>पिकाचा फोटो (📷) अपलोड</strong> करू शकता किंवा <strong>माईक</strong> वापरून बोलू शकता!",
    quickPrompts: "💡 शेतकऱ्यांचे नेहमीचे प्रश्न:",
    placeholder: "लक्षणे सांगा किंवा पिकाचा फोटो अपलोड करा...",
    disclaimer: "<strong>सूचना:</strong> CropGuard चा सल्ला ICAR व कृषी मार्गदर्शक तत्त्वांवर आधारित आहे. मोठ्या प्रादुर्भावासाठी स्थानिक <strong>कृषी विज्ञान केंद्र (KVK)</strong> शी संपर्क साधा.",
    thinking: "कृषी माहिती व स्थानिक हवामानाचे विश्लेषण सुरू आहे...",
    thinkingVision: "AI व्हिजनद्वारे फोटोचे विश्लेषण सुरू आहे...",
    clear: "संभाषण पुसा",
    listen: "🔊 ऐका",
    stopAudio: "⏹ थांबवा",
    viewTrace: "🔍 टूल ट्रेस तपासा",
    farmer: "शेतकरी",
    advisor: "CropGuard AI सल्लागार",
    speechLang: "mr-IN",
    photoReady: "🌿 फोटो जोडला • AI विश्लेषण सज्ज",
    visObsTitle: "📸 AI दृश्य निरीक्षण"
  },
  gu: {
    tagline: "પાક જીવાત અને રોગ સલાહકાર • ખેડૂત રક્ષક",
    weatherChecking: "હવામાન તપાસી રહ્યા છીએ...",
    weatherFavorable: "✓ અનુકૂળ હવામાન",
    weatherRisk: "⚠️ વધેલું જીવાત જોખમ",
    weatherOffline: "હવામાન ઉપલબ્ધ નથી",
    welcome: "નમસ્તે ખેડૂત મિત્ર! હું તમારો <strong>CropGuard AI સલાહકાર</strong> છું. કપાસ, ટામેટા કે ઘઉંના પાક પર જીવાત અથવા રોગ વિશે પૂછો.<br><br>💡 <strong>નવું:</strong> તમે હવે પાકનો <strong>ફોટો (📷) અપલોડ</strong> કરીને પણ વિશ્લેષણ મેળવી શકો છો!",
    quickPrompts: "💡 સામાન્ય પ્રશ્નો:",
    placeholder: "લક્ષણો વર્ણવો અથવા પાકનો ફોટો અપલોડ કરો...",
    disclaimer: "<strong>સલાહ:</strong> CropGuard ની માહિતી કૃષિ રેકોર્ડ આધારિત છે. વધુ સલાહ માટે સ્થાનિક <strong>KVK</strong> નો સંપર્ક કરો.",
    thinking: "કૃષિ ડેટાબેઝ અને હવામાનનું વિશ્લેષણ ચાલુ છે...",
    thinkingVision: "AI વિઝન દ્વારા ફોટો તપાસવામાં આવી રહ્યો છે...",
    clear: "વાતચીત સાફ કરો",
    listen: "🔊 સાંભળો",
    stopAudio: "⏹ બંધ કરો",
    viewTrace: "🔍 ટ્રેસ જુઓ",
    farmer: "ખેડૂત",
    advisor: "CropGuard AI સલાહકાર",
    speechLang: "gu-IN",
    photoReady: "🌿 ફોટો જોડાયો • AI વિશ્લેષણ તૈયાર",
    visObsTitle: "📸 AI વિઝ્યુઅલ અવલોકન"
  },
  pa: {
    tagline: "ਫਸਲ ਕੀੜੇ ਅਤੇ ਬਿਮਾਰੀ ਸਲਾਹਕਾਰ • ਕਿਸਾਨ ਰੱਖਿਅਕ",
    weatherChecking: "ਮੌਸਮ ਜਾਂਚਿਆ ਜਾ ਰਿਹਾ ਹੈ...",
    weatherFavorable: "✓ ਅਨੁਕੂਲ ਮੌਸਮ",
    weatherRisk: "⚠️ ਵਧਿਆ ਹੋਇਆ ਖਤਰਾ",
    weatherOffline: "ਮੌਸਮ ਉਪਲਬਧ ਨਹੀਂ",
    welcome: "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ ਕਿਸਾਨ ਵੀਰੋ! ਮੈਂ ਤੁਹਾਡਾ <strong>CropGuard AI ਸਲਾਹਕਾਰ</strong> ਹਾਂ। ਨਰਮਾ, ਟਮਾਟਰ ਜਾਂ ਕਣਕ ਦੀ ਫਸਲ ਬਾਰੇ ਕੋਈ ਵੀ ਸਵਾਲ ਪੁੱਛੋ। ਤੁਸੀਂ ਫਸਲ ਦੀ <strong>ਫੋਟੋ (📷)</strong> ਵੀ ਅੱਪਲੋਡ ਕਰ ਸਕਦੇ ਹੋ!",
    quickPrompts: "💡 ਆਮ ਸਵਾਲ:",
    placeholder: "ਫਸਲ ਦੇ ਲੱਛਣ ਦੱਸੋ ਜਾਂ ਫੋਟੋ ਅੱਪਲੋਡ ਕਰੋ...",
    disclaimer: "<strong>ਸੂਚਨਾ:</strong> ਵਧੇਰੇ ਜਾਣਕਾਰੀ ਲਈ ਆਪਣੇ ਨਜ਼ਦੀਕੀ <strong>ਕ੍ਰਿਸ਼ੀ ਵਿਗਿਆਨ ਕੇਂਦਰ (KVK)</strong> ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",
    thinking: "ਮੌਸਮ ਅਤੇ ਖੇਤੀਬਾੜੀ ਰਿਕਾਰਡ ਦੀ ਜਾਂਚ ਕੀਤੀ ਜਾ ਰਹੀ ਹੈ...",
    thinkingVision: "AI ਵਿਜ਼ਨ ਦੁਆਰਾ ਫੋਟੋ ਦੀ ਜਾਂਚ ਕੀਤੀ ਜਾ ਰਹੀ ਹੈ...",
    clear: "ਗੱਲਬਾਤ ਸਾਫ਼ ਕਰੋ",
    listen: "🔊 ਸੁਣੋ",
    stopAudio: "⏹ ਰੋਕੋ",
    viewTrace: "🔍 ਟ੍ਰੇਸ ਦੇਖੋ",
    farmer: "ਕਿਸਾਨ",
    advisor: "CropGuard AI ਸਲਾਹਕਾਰ",
    speechLang: "pa-IN",
    photoReady: "🌿 ਫੋਟੋ ਨੱਥੀ ਕੀਤੀ • AI ਜਾਂਚ ਤਿਆਰ",
    visObsTitle: "📸 AI ਦ੍ਰਿਸ਼ਟੀ ਜਾਂਚ"
  },
  te: {
    tagline: "పంట తెగుళ్లు & వ్యాధుల సలహాదారు • రైతు రక్షకుడు",
    weatherChecking: "వాతావరణ సమాచారం...",
    weatherFavorable: "✓ అనుకూల వాతావరణం",
    weatherRisk: "⚠️ తెగులు ప్రమాదం",
    weatherOffline: "వాతావరణం అందుబాటులో లేదు",
    welcome: "నమస్కారం రైతు సోదరులారా! నేను మీ <strong>CropGuard AI సలహాదారుని</strong>. పంటల తెగుళ్లు లేదా వ్యాధుల ఫోటోను (📷) అప్‌లోడ్ చేసి తక్షణ సలహా పొందండి!",
    quickPrompts: "💡 సాధారణ ప్రశ్నలు:",
    placeholder: "లక్షణాలను వివరించండి లేదా పంట ఫోటోను అప్‌లోడ్ చేయండి...",
    disclaimer: "<strong>గమనిక:</strong> మరింత సమాచారం కొరకు సమీప <strong>కృషి విజ్ఞాన కేంద్రం (KVK)</strong> ను సంప్రదించండి.",
    thinking: "వ్యవసాయ డేటాబేస్ విశ్లేషించబడుతోంది...",
    thinkingVision: "AI విజన్ ద్వారా ఫోటో విశ్లేషణ జరుగుతోంది...",
    clear: "సంభాషణను క్లియర్ చేయండి",
    listen: "🔊 వినండి",
    stopAudio: "⏹ ఆపండి",
    viewTrace: "🔍 ట్రేస్ చూడండి",
    farmer: "రైతు",
    advisor: "CropGuard AI సలహాదారు",
    speechLang: "te-IN",
    photoReady: "🌿 ఫోటో జోడించబడింది • AI విశ్లేషణ సిద్ధంగా ఉంది",
    visObsTitle: "📸 AI విజువల్ పరిశీలన"
  }
};

// ---------------------------------------------------------------------------
// App State
// ---------------------------------------------------------------------------
const State = {
  lang: "en",
  theme: "dark",
  location: "Nashik, Maharashtra",
  weatherData: null,
  chatHistory: [],
  isRecording: false,
  recognition: null,
  selectedImageBase64: null,
  selectedImageName: "",
};

// ---------------------------------------------------------------------------
// DOM Elements Cache
// ---------------------------------------------------------------------------
const DOM = {
  // Header
  langSelect: document.getElementById("langSelect"),
  themeToggleBtn: document.getElementById("themeToggleBtn"),
  themeEmoji: document.getElementById("themeEmoji"),
  lblTagline: document.getElementById("lblTagline"),

  // Weather Ribbon
  farmLocation: document.getElementById("farmLocation"),
  refreshWeatherBtn: document.getElementById("refreshWeatherBtn"),
  quickLocs: document.querySelectorAll(".quick-loc"),
  wTemp: document.getElementById("wTemp"),
  wHumidity: document.getElementById("wHumidity"),
  wRiskBadge: document.getElementById("wRiskBadge"),

  // Chat Area
  chatStream: document.getElementById("chatStream"),
  welcomeText: document.getElementById("welcomeText"),
  agentThinking: document.getElementById("agentThinking"),
  thinkingText: document.getElementById("thinkingText"),
  lblQuickPrompts: document.getElementById("lblQuickPrompts"),
  promptChips: document.querySelectorAll(".prompt-chip"),
  samplePhotoChip: document.getElementById("samplePhotoChip"),
  chatForm: document.getElementById("chatForm"),
  chatInput: document.getElementById("chatInput"),
  micBtn: document.getElementById("micBtn"),
  sendBtn: document.getElementById("sendBtn"),
  clearBtn: document.getElementById("clearBtn"),

  // Image Upload Controls
  imageFileInput: document.getElementById("imageFileInput"),
  attachImgBtn: document.getElementById("attachImgBtn"),
  imagePreviewStrip: document.getElementById("imagePreviewStrip"),
  previewImageThumb: document.getElementById("previewImageThumb"),
  previewImgName: document.getElementById("previewImgName"),
  removeImgBtn: document.getElementById("removeImgBtn"),
  clearPreviewBtn: document.getElementById("clearPreviewBtn"),

  // Lightbox Modal
  lightboxModal: document.getElementById("lightboxModal"),
  closeLightboxBtn: document.getElementById("closeLightboxBtn"),
  lightboxImg: document.getElementById("lightboxImg"),
  lightboxCaption: document.getElementById("lightboxCaption"),

  // Disclaimer
  lblDisclaimerText: document.getElementById("lblDisclaimerText"),

  // Trace Modal
  traceModal: document.getElementById("traceModal"),
  closeTraceBtn: document.getElementById("closeTraceBtn"),
  traceModalBody: document.getElementById("traceModalBody"),
};

// ---------------------------------------------------------------------------
// Theme Controller
// ---------------------------------------------------------------------------
function initTheme() {
  try {
    const saved = localStorage.getItem("cropguard_theme");
    if (saved) State.theme = saved;
  } catch (e) {}

  applyTheme(State.theme);

  if (DOM.themeToggleBtn) {
    DOM.themeToggleBtn.addEventListener("click", () => {
      State.theme = State.theme === "dark" ? "light" : "dark";
      applyTheme(State.theme);
      try {
        localStorage.setItem("cropguard_theme", State.theme);
      } catch (e) {}
    });
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  if (DOM.themeEmoji) {
    DOM.themeEmoji.textContent = theme === "dark" ? "☀️" : "🌙";
  }
}

// ---------------------------------------------------------------------------
// Language & Localization Controller
// ---------------------------------------------------------------------------
function updateLanguage(langKey) {
  State.lang = langKey;
  const t = I18N[langKey] || I18N.en;

  if (DOM.lblTagline) DOM.lblTagline.textContent = t.tagline;
  if (DOM.welcomeText) DOM.welcomeText.innerHTML = t.welcome;
  if (DOM.lblQuickPrompts) DOM.lblQuickPrompts.textContent = t.quickPrompts;
  if (DOM.chatInput) DOM.chatInput.placeholder = t.placeholder;
  if (DOM.lblDisclaimerText) DOM.lblDisclaimerText.innerHTML = t.disclaimer;
  if (DOM.thinkingText) DOM.thinkingText.textContent = t.thinking;
  if (DOM.clearBtn) DOM.clearBtn.textContent = t.clear;

  renderWeather();
}

// ---------------------------------------------------------------------------
// Agricultural Weather Service
// ---------------------------------------------------------------------------
async function fetchWeather(locationName) {
  if (!locationName) return;
  State.location = locationName;
  const t = I18N[State.lang] || I18N.en;

  if (DOM.wRiskBadge) {
    DOM.wRiskBadge.textContent = t.weatherChecking;
    DOM.wRiskBadge.style.background = "var(--primary-soft)";
    DOM.wRiskBadge.style.color = "var(--primary)";
    DOM.wRiskBadge.style.borderColor = "var(--primary)";
  }

  try {
    const res = await fetch(`/api/weather?location=${encodeURIComponent(locationName)}&days=3`);
    const data = await res.json();
    if (data.status === "ok") {
      State.weatherData = data;
      renderWeather();
    } else {
      if (DOM.wRiskBadge) DOM.wRiskBadge.textContent = t.weatherOffline;
    }
  } catch (err) {
    console.warn("Weather fetch error:", err);
    if (DOM.wRiskBadge) DOM.wRiskBadge.textContent = t.weatherOffline;
  }
}

function renderWeather() {
  if (!State.weatherData) return;
  const t = I18N[State.lang] || I18N.en;
  const cur = State.weatherData.current || {};

  if (DOM.wTemp) {
    DOM.wTemp.textContent = cur.temperature_c !== undefined ? `🌡️ ${cur.temperature_c}°C` : "🌡️ --°C";
  }
  if (DOM.wHumidity) {
    DOM.wHumidity.textContent = cur.humidity_pct !== undefined ? `💧 ${cur.humidity_pct}% Humidity` : "💧 --% Humidity";
  }

  const alerts = State.weatherData.risk_alerts || [];
  if (DOM.wRiskBadge) {
    if (alerts.length > 0) {
      const topAlert = alerts[0];
      const issueShort = (topAlert.issue_name || "").split("(")[0].trim();
      DOM.wRiskBadge.textContent = `⚠️ High Risk: ${issueShort}`;
      DOM.wRiskBadge.style.background = "rgba(239, 68, 68, 0.15)";
      DOM.wRiskBadge.style.color = "#ef4444";
      DOM.wRiskBadge.style.borderColor = "#ef4444";
    } else {
      DOM.wRiskBadge.textContent = t.weatherFavorable;
      DOM.wRiskBadge.style.background = "var(--primary-soft)";
      DOM.wRiskBadge.style.color = "var(--primary)";
      DOM.wRiskBadge.style.borderColor = "var(--primary)";
    }
  }
}

// ---------------------------------------------------------------------------
// Image Upload & Vision Helper
// ---------------------------------------------------------------------------
function handleImageFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    alert("Please select a valid image file (JPEG, PNG, WEBP).");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    const rawDataUrl = e.target.result;
    
    // Resize image on client canvas to max 800px for speedy transmission
    const img = new Image();
    img.onload = () => {
      const maxSide = 800;
      let w = img.width;
      let h = img.height;
      if (w > maxSide || h > maxSide) {
        if (w > h) {
          h = Math.round((h * maxSide) / w);
          w = maxSide;
        } else {
          w = Math.round((w * maxSide) / h);
          h = maxSide;
        }
      }
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, w, h);
      const compressedDataUrl = canvas.toDataURL("image/jpeg", 0.82);

      State.selectedImageBase64 = compressedDataUrl;
      State.selectedImageName = file.name || "plant_photo.jpg";

      // Update Preview UI
      if (DOM.previewImageThumb) DOM.previewImageThumb.src = compressedDataUrl;
      if (DOM.previewImgName) DOM.previewImgName.textContent = State.selectedImageName;
      if (DOM.imagePreviewStrip) DOM.imagePreviewStrip.style.display = "flex";
      if (DOM.attachImgBtn) DOM.attachImgBtn.classList.add("has-image");

      if (DOM.chatInput && !DOM.chatInput.value.trim()) {
        DOM.chatInput.placeholder = "Optional: Add any details or press Send to analyze photo...";
      }
    };
    img.src = rawDataUrl;
  };
  reader.readAsDataURL(file);
}

function clearImageAttachment() {
  State.selectedImageBase64 = null;
  State.selectedImageName = "";
  if (DOM.imagePreviewStrip) DOM.imagePreviewStrip.style.display = "none";
  if (DOM.attachImgBtn) DOM.attachImgBtn.classList.remove("has-image");
  if (DOM.imageFileInput) DOM.imageFileInput.value = "";
  const t = I18N[State.lang] || I18N.en;
  if (DOM.chatInput) DOM.chatInput.placeholder = t.placeholder;
}

function openLightbox(src, caption = "") {
  if (!DOM.lightboxModal || !DOM.lightboxImg) return;
  DOM.lightboxImg.src = src;
  if (DOM.lightboxCaption) DOM.lightboxCaption.textContent = caption;
  DOM.lightboxModal.style.display = "flex";
}

function closeLightbox() {
  if (DOM.lightboxModal) DOM.lightboxModal.style.display = "none";
}

// ---------------------------------------------------------------------------
// Text-to-Speech (Farmer Audio)
// ---------------------------------------------------------------------------
function speakAdvice(text, btnElement) {
  if (!("speechSynthesis" in window)) {
    alert("Speech playback is not supported on this browser.");
    return;
  }

  const t = I18N[State.lang] || I18N.en;

  if (window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    if (btnElement) btnElement.innerHTML = `🔊 ${t.listen}`;
    return;
  }

  const clean = text
    .replace(/[*#_`>]/g, "")
    .replace(/\[.*?\]/g, "")
    .replace(/•/g, " ");

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 0.92;
  utterance.pitch = 1.0;

  const voices = window.speechSynthesis.getVoices();
  const langTag = t.speechLang || "en-IN";
  const preferredVoice = voices.find(v => v.lang.startsWith(langTag.split("-")[0]) || v.lang.includes("IN"));
  if (preferredVoice) utterance.voice = preferredVoice;

  if (btnElement) btnElement.innerHTML = `⏹ ${t.stopAudio}`;

  utterance.onend = utterance.onerror = () => {
    if (btnElement) btnElement.innerHTML = `🔊 ${t.listen}`;
  };

  window.speechSynthesis.speak(utterance);
}

// ---------------------------------------------------------------------------
// Speech-to-Text (Microphone)
// ---------------------------------------------------------------------------
function initVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (DOM.micBtn) DOM.micBtn.style.display = "none";
    return;
  }

  State.recognition = new SpeechRecognition();
  State.recognition.continuous = false;
  State.recognition.interimResults = false;

  State.recognition.onstart = () => {
    State.isRecording = true;
    DOM.micBtn.classList.add("listening");
    DOM.chatInput.placeholder = "Listening... Speak your crop symptoms now.";
  };

  State.recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    if (transcript) {
      const cur = DOM.chatInput.value.trim();
      DOM.chatInput.value = cur ? `${cur} ${transcript}` : transcript;
      DOM.chatInput.focus();
    }
  };

  State.recognition.onerror = () => {
    State.isRecording = false;
    DOM.micBtn.classList.remove("listening");
    const t = I18N[State.lang] || I18N.en;
    DOM.chatInput.placeholder = t.placeholder;
  };

  State.recognition.onend = () => {
    State.isRecording = false;
    DOM.micBtn.classList.remove("listening");
    const t = I18N[State.lang] || I18N.en;
    DOM.chatInput.placeholder = t.placeholder;
  };

  DOM.micBtn.addEventListener("click", () => {
    const t = I18N[State.lang] || I18N.en;
    State.recognition.lang = t.speechLang || "en-IN";

    if (State.isRecording) {
      State.recognition.stop();
    } else {
      try {
        State.recognition.start();
      } catch (e) {
        State.recognition.stop();
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Conversational AI Assistant
// ---------------------------------------------------------------------------
async function sendQuery(queryText) {
  const text = (queryText !== undefined ? queryText : DOM.chatInput.value).trim();
  const attachedImage = State.selectedImageBase64;

  if (!text && !attachedImage) return;

  const t = I18N[State.lang] || I18N.en;

  // Clear input field and attachment preview
  DOM.chatInput.value = "";
  clearImageAttachment();

  // Render user bubble (with thumbnail if image was attached)
  const displayText = text || (attachedImage ? "📸 [Crop photo submitted for visual analysis]" : "");
  appendChatBubble("user", displayText, null, null, null, attachedImage);
  State.chatHistory.push({ role: "user", content: displayText });

  // Show thinking indicator with dynamic vision text
  if (DOM.agentThinking) {
    if (DOM.thinkingText) {
      DOM.thinkingText.textContent = attachedImage ? t.thinkingVision : t.thinking;
    }
    DOM.agentThinking.style.display = "flex";
  }
  DOM.chatStream.scrollTop = DOM.chatStream.scrollHeight;

  // Infer location context if not mentioned
  let fullMessage = text;
  const lower = text.toLowerCase();
  const knownLocations = ["nashik", "ahmedabad", "ludhiana", "pune", "guntur", "delhi", "mumbai", "rajkot", "nagpur"];
  const mentionsLoc = knownLocations.some(l => lower.includes(l));
  if (!mentionsLoc && State.location) {
    fullMessage = fullMessage ? `${fullMessage} (Farm Location: ${State.location})` : `Farm Location: ${State.location}`;
  }

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: fullMessage,
        history: State.chatHistory.slice(-6),
        crop: "",
        lang: State.lang,
        image: attachedImage
      })
    });

    if (!res.ok) {
      let errMsg = "An error occurred while contacting the AI Advisor. Please try again.";
      try {
        const errJson = await res.json();
        if (errJson && errJson.message) errMsg = errJson.message;
      } catch (e) {}
      if (DOM.agentThinking) DOM.agentThinking.style.display = "none";
      appendChatBubble("bot", errMsg);
      return;
    }

    const data = await res.json();
    if (DOM.agentThinking) DOM.agentThinking.style.display = "none";

    if (data.status === "ok") {
      const reply = data.reply || "No guidance available.";
      State.chatHistory.push({ role: "assistant", content: reply });
      appendChatBubble("bot", reply, data.trace, data.engine, data.vision_analysis);
    } else {
      appendChatBubble("bot", data.message || "I could not process this question right now. Please check your connection or contact your local KVK.");
    }
  } catch (err) {
    console.error("Chat error:", err);
    if (DOM.agentThinking) DOM.agentThinking.style.display = "none";
    appendChatBubble("bot", "Network error occurred while contacting the AI Advisor. Please check your local connection.");
  }
}

function appendChatBubble(role, contentText, trace = null, engine = null, visionAnalysis = null, userImgSrc = null) {
  const t = I18N[State.lang] || I18N.en;
  const msgWrapper = document.createElement("div");
  msgWrapper.className = `chat-msg ${role}-msg`;

  // Avatar
  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "👨‍🌾" : "🌾";

  // Content Box
  const content = document.createElement("div");
  content.className = "msg-content";

  // Header
  const header = document.createElement("div");
  header.className = "msg-header";
  header.textContent = role === "user" ? t.farmer : `${t.advisor} ${engine ? `• ${engine}` : ""}`;
  content.appendChild(header);

  // If user attached an image, render photo thumbnail card inside bubble
  if (role === "user" && userImgSrc) {
    const imgWrap = document.createElement("div");
    imgWrap.className = "user-attached-img-wrap";
    imgWrap.innerHTML = `
      <img src="${userImgSrc}" class="user-attached-img" alt="Attached plant photo">
      <span class="img-zoom-hint">🔍 Expand</span>
    `;
    imgWrap.addEventListener("click", () => openLightbox(userImgSrc, "Crop photo submitted by farmer"));
    content.appendChild(imgWrap);
  }

  // If bot response has vision analysis, render the dedicated visual card
  if (role === "bot" && visionAnalysis) {
    const visCard = document.createElement("div");
    visCard.className = "vision-card";

    const partLabel = (visionAnalysis.plant_part && visionAnalysis.plant_part !== "unclear")
      ? visionAnalysis.plant_part.toUpperCase()
      : "PLANT TISSUE";

    const summaryText = visionAnalysis.summary || (visionAnalysis.symptoms || []).join(", ") || "Visual inspection recorded";

    let insectHtml = "";
    if (visionAnalysis.insects_visible) {
      insectHtml = `<div class="vision-insect-alert">🪲 <strong>Insects Observed:</strong> ${escapeHtml(visionAnalysis.insect_description || "Pests visible on plant")}</div>`;
    }

    let tagsHtml = "";
    if (visionAnalysis.crop_visible && visionAnalysis.crop_visible !== "unclear") {
      tagsHtml += `<span class="vision-tag">🌾 ${escapeHtml(visionAnalysis.crop_visible.toUpperCase())}</span>`;
    }
    if (visionAnalysis.spot_color) {
      tagsHtml += `<span class="vision-tag">🎨 Spot: ${escapeHtml(visionAnalysis.spot_color)}</span>`;
    }
    if (visionAnalysis.pattern) {
      tagsHtml += `<span class="vision-tag">📐 Pattern: ${escapeHtml(visionAnalysis.pattern)}</span>`;
    }

    visCard.innerHTML = `
      <div class="vision-card-header">
        <span class="vision-badge">📸 ${t.visObsTitle || "AI Visual Observation"}</span>
        <span class="vision-part-pill">🌱 ${escapeHtml(partLabel)}</span>
      </div>
      <div class="vision-card-body">
        <div class="vision-summary">${escapeHtml(summaryText)}</div>
        ${insectHtml}
        ${tagsHtml ? `<div class="vision-tags-row">${tagsHtml}</div>` : ""}
      </div>
    `;
    content.appendChild(visCard);
  }

  // Body with markdown formatting
  const body = document.createElement("div");
  body.className = "msg-body";

  const formatted = escapeHtml(contentText)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\* (.*$)/gim, '• $1')
    .replace(/^- (.*$)/gim, '• $1');

  body.innerHTML = formatted;
  content.appendChild(body);

  // Bot Actions (TTS Listen + Trace)
  if (role === "bot") {
    const actions = document.createElement("div");
    actions.className = "msg-actions";

    // Listen button
    const ttsBtn = document.createElement("button");
    ttsBtn.type = "button";
    ttsBtn.className = "btn-tts";
    ttsBtn.innerHTML = `🔊 ${t.listen}`;
    ttsBtn.addEventListener("click", () => speakAdvice(contentText, ttsBtn));
    actions.appendChild(ttsBtn);

    // Trace button if MCP autonomous tools were invoked
    if (trace && trace.length > 0) {
      const traceBtn = document.createElement("button");
      traceBtn.type = "button";
      traceBtn.className = "btn-trace";
      traceBtn.innerHTML = `🔍 Trace (${trace.length})`;
      traceBtn.addEventListener("click", () => showTraceModal(trace));
      actions.appendChild(traceBtn);
    }

    content.appendChild(actions);
  }

  // Timestamp
  const time = document.createElement("div");
  time.className = "msg-time";
  time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  content.appendChild(time);

  msgWrapper.appendChild(avatar);
  msgWrapper.appendChild(content);

  DOM.chatStream.appendChild(msgWrapper);
  DOM.chatStream.scrollTop = DOM.chatStream.scrollHeight;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ---------------------------------------------------------------------------
// Tool Trace Modal Inspector
// ---------------------------------------------------------------------------
function showTraceModal(trace) {
  if (!DOM.traceModal || !DOM.traceModalBody) return;
  DOM.traceModalBody.innerHTML = "";

  trace.forEach((step, idx) => {
    const item = document.createElement("div");
    item.className = "trace-step-item";
    item.style.marginBottom = "1rem";
    item.style.padding = "0.75rem";
    item.style.background = "var(--bg-surface)";
    item.style.border = "1px solid var(--border-color)";
    item.style.borderRadius = "8px";

    let parsedResult = step.result;
    try {
      parsedResult = JSON.stringify(JSON.parse(step.result), null, 2);
    } catch (e) {}

    item.innerHTML = `
      <div style="color:var(--primary); font-weight:700; margin-bottom:0.35rem;">
        ${idx + 1}. Tool Executed: <code>${escapeHtml(step.tool)}()</code>
      </div>
      <div style="font-size:0.78rem; color:var(--text-muted); margin-bottom:0.25rem;">Arguments:</div>
      <pre style="background:var(--bg-page); padding:0.5rem; border-radius:4px; font-size:0.75rem; overflow-x:auto;">${escapeHtml(JSON.stringify(step.arguments, null, 2))}</pre>
      <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.4rem; margin-bottom:0.25rem;">Result Payload:</div>
      <pre style="background:var(--bg-page); padding:0.5rem; border-radius:4px; font-size:0.75rem; max-height:160px; overflow-y:auto;">${escapeHtml(parsedResult)}</pre>
    `;
    DOM.traceModalBody.appendChild(item);
  });

  DOM.traceModal.style.display = "flex";
}

// ---------------------------------------------------------------------------
// Event Listeners & Wiring
// ---------------------------------------------------------------------------
function initEvents() {
  // Language Change
  if (DOM.langSelect) {
    DOM.langSelect.addEventListener("change", (e) => updateLanguage(e.target.value));
  }

  // Location input & enter key
  if (DOM.farmLocation) {
    DOM.farmLocation.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        fetchWeather(DOM.farmLocation.value.trim());
      }
    });
  }

  if (DOM.refreshWeatherBtn) {
    DOM.refreshWeatherBtn.addEventListener("click", () => {
      fetchWeather(DOM.farmLocation.value.trim());
    });
  }

  // Quick Location Chips
  DOM.quickLocs.forEach(btn => {
    btn.addEventListener("click", () => {
      DOM.quickLocs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const loc = btn.dataset.loc;
      DOM.farmLocation.value = loc;
      fetchWeather(loc);
    });
  });

  // Prompt Chips
  DOM.promptChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const q = chip.dataset.query;
      if (q) sendQuery(q);
    });
  });

  // Sample Leaf Photo Demo Chip
  if (DOM.samplePhotoChip) {
    DOM.samplePhotoChip.addEventListener("click", async () => {
      try {
        const res = await fetch("/static/images/tomato.jpg");
        const blob = await res.blob();
        const file = new File([blob], "sample_blighted_tomato_leaf.jpg", { type: "image/jpeg" });
        handleImageFile(file);
        DOM.chatInput.value = "What disease are these dark concentric spots on my tomato leaves?";
        DOM.chatInput.focus();
      } catch (err) {
        console.warn("Could not load sample demo image:", err);
        sendQuery("Tomato leaves have dark brown spots with concentric target-like rings on lower leaves.");
      }
    });
  }

  // Image Attach Button & File Input
  if (DOM.attachImgBtn && DOM.imageFileInput) {
    DOM.attachImgBtn.addEventListener("click", () => {
      DOM.imageFileInput.click();
    });
    DOM.imageFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleImageFile(e.target.files[0]);
      }
    });
  }

  // Remove Attachment
  if (DOM.removeImgBtn) {
    DOM.removeImgBtn.addEventListener("click", clearImageAttachment);
  }
  if (DOM.clearPreviewBtn) {
    DOM.clearPreviewBtn.addEventListener("click", clearImageAttachment);
  }

  // Drag & Drop on Chat Workspace
  const dropZone = document.querySelector(".chat-workspace");
  if (dropZone) {
    ["dragenter", "dragover"].forEach(evt => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.style.outline = "2px dashed var(--primary)";
      });
    });
    ["dragleave", "drop"].forEach(evt => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.style.outline = "none";
      });
    });
    dropZone.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleImageFile(e.dataTransfer.files[0]);
      }
    });
  }

  // Clipboard Paste Support (Ctrl+V with image)
  window.addEventListener("paste", (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (let item of items) {
      if (item.kind === "file" && item.type.startsWith("image/")) {
        const file = item.getAsFile();
        handleImageFile(file);
        break;
      }
    }
  });

  // Lightbox Modal Close
  if (DOM.closeLightboxBtn) {
    DOM.closeLightboxBtn.addEventListener("click", closeLightbox);
  }
  if (DOM.lightboxModal) {
    DOM.lightboxModal.addEventListener("click", (e) => {
      if (e.target === DOM.lightboxModal) closeLightbox();
    });
  }

  // Chat Form Submit
  if (DOM.chatForm) {
    DOM.chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      sendQuery();
    });
  }

  // Clear Chat Button
  if (DOM.clearBtn) {
    DOM.clearBtn.addEventListener("click", () => {
      DOM.chatStream.innerHTML = "";
      State.chatHistory = [];
      clearImageAttachment();
      const t = I18N[State.lang] || I18N.en;

      const welcomeWrapper = document.createElement("div");
      welcomeWrapper.className = "chat-msg bot-msg";
      welcomeWrapper.innerHTML = `
        <div class="msg-avatar">🌾</div>
        <div class="msg-content">
          <div class="msg-header">${t.advisor}</div>
          <div class="msg-body">${t.welcome}</div>
          <div class="msg-time">Just now</div>
        </div>
      `;
      DOM.chatStream.appendChild(welcomeWrapper);
    });
  }

  // Close Trace Modal
  if (DOM.closeTraceBtn) {
    DOM.closeTraceBtn.addEventListener("click", () => {
      DOM.traceModal.style.display = "none";
    });
  }

  if (DOM.traceModal) {
    DOM.traceModal.addEventListener("click", (e) => {
      if (e.target === DOM.traceModal) DOM.traceModal.style.display = "none";
    });
  }

  // Voice Mic
  initVoiceInput();
}

// ---------------------------------------------------------------------------
// Bootstrap App
// ---------------------------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initEvents();
  fetchWeather("Nashik, Maharashtra");
  updateLanguage("en");
});
