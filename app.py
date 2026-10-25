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

st.set_page_config(page_title="Crop Guard", page_icon="🌿", layout="wide")

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
    st.title("🌿 Crop Guard")
    st.selectbox("🌐 Language / भाषा / ભાષા", list(LANGS),
                 format_func=lambda c: LANGS[c], key="ui_lang")
    lang = st.session_state.get("ui_lang", "en")
    if st.button(t("new_chat", lang), use_container_width=True, type="primary"):
        st.session_state.current = None
        st.rerun()

    st.caption(t("your_chats", lang))
    for k, c in sorted(chats.items(), key=lambda kv: kv[1]["created"], reverse=True):
        label = ("▶ " if k == cid else "") + c["title"]
        if st.button(label, key=f"open_{k}", use_container_width=True):
            st.session_state.current = k
            st.rerun()

    if chat:
        st.divider()
        st.subheader(t("location_title", lang))
        ctx = chat["context"]
        city = st.text_input(t("city", lang), value=ctx.get("city", ""), key=f"city_{cid}")
        use_coords = st.checkbox(t("use_coords", lang), key=f"uc_{cid}")
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
            st.info(t("no_location", lang))
        if st.button(t("delete_chat", lang), use_container_width=True):
            del chats[cid]
            st.session_state.current = None
            save_chats()
            st.rerun()

    st.divider()
    st.markdown(t("photo_tips", lang))
    st.markdown(t("helpline", lang) + "  \n📞 1800-180-1551")

def render_cards(m):
    d, w = m.get("diagnosis"), m.get("weather")
    if d and "error" not in d:
        conf = str(d.get("confidence", "")).lower()
        icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
        st.markdown(f"**{str(d.get('disease', '-')).title()}**  ·  {icon} "
                    f"{t('confidence', lang)}: {conf_label(conf, lang)}")
        sym = nice_list(d.get("symptoms", ""))
        if sym and lang == "en":
            st.caption(f"{t('noticed', lang)}: {sym}")
        alts = d.get("alternatives")
        if alts and lang == "en":
            st.caption(f"{t('others', lang)}: {nice_list(alts)}")
        if d.get("note") and lang == "en":
            st.warning(d["note"])
    if w and "error" not in w:
        risk = w.get("fungal_risk", "-")
        icon = {"HIGH": "🔴", "MODERATE": "🟡", "LOW": "🟢"}.get(risk, "⚪")
        st.caption(f"📍 {t('weather_for', lang)}: {w.get('location', '-')}")
        c1, c2 = st.columns(2)
        c1.metric(t("temp", lang), f"{w.get('temperature_2m', '-')} °C")
        c2.metric(t("humidity", lang), f"{w.get('relative_humidity_2m', '-')} %")
        c3, c4 = st.columns(2)
        c3.metric(t("rain3", lang), f"{w.get('rain_last_3_days_mm', '-')} mm")
        c4.metric(t("fungal", lang), f"{icon} {risk_label(risk, lang)}")
    treatment = m.get("treatment")
    if treatment:
        if treatment.get("error"):
            st.warning(t("no_entry", lang))
        else:
            for item in treatment.get("organic_control", []):
                st.markdown(f"- {item}")
            if treatment.get("chemical_control"):
                st.caption(treatment["chemical_control"])

# ---------- start screen ----------
if chat is None:
    st.header(t("start_title", lang))
    st.write(t("start_help", lang))
    crop = st.selectbox(t("which_crop", lang), CROPS,
                        format_func=lambda c: crop_label(c, lang), key="start_crop")
    if st.button(t("start_btn", lang), type="primary"):
        new_chat(crop)
        st.rerun()
    st.stop()

# ---------- chat screen ----------
st.header("💬 " + t("chat_title", lang).format(crop=crop_label(chat["crop"], lang)))
if chat.get("legacy_results_notice"):
    st.info(
        "This saved conversation predates the current evidence checks. Earlier results remain "
        "visible for reference, but Crop Guard will not rely on them as verified facts. "
        "Add a new photo for an updated assessment."
    )

if not chat["messages"]:
    with st.chat_message("assistant"):
        st.markdown(t("hello", lang))

for m in chat["messages"]:
    with st.chat_message(m["role"]):
        if m.get("image") and Path(m["image"]).exists():
            st.image(m["image"], width=220)
        st.markdown(m["content"].replace("\n", "  \n"))
        if m["role"] == "assistant":
            if lang != "en" and m.get("reply_en"):
                with st.expander("English"):
                    st.markdown(m["reply_en"].replace("\n", "  \n"))
            render_cards(m)
            if m.get("steps"):
                with st.expander(t("how_decided", lang)):
                    for s in m["steps"]:
                        st.write("•", step_label(s, lang))

with st.expander(t("attach", lang),
                 expanded=not chat["messages"]):
    photo = st.file_uploader("Leaf photo", type=["jpg", "jpeg", "png", "webp"],
                             key=f"up_{cid}_{st.session_state.up_n}",
                             label_visibility="collapsed")
    if photo:
        st.image(photo, width=220)

prompt = st.chat_input(t("chat_input", lang))

if prompt:
    img_path = None
    if photo:
        img = Image.open(photo).convert("RGB")
        img.thumbnail((1024, 1024))                      # smaller = faster, saves quota
        p = UPLOADS / f"chat_{cid}_{int(time.time())}.jpg"
        img.save(p, "JPEG", quality=90)
        img_path = str(p)

    chat["messages"].append({"role": "user", "content": prompt, "image": img_path})
    with st.chat_message("user"):
        if img_path:
            st.image(img_path, width=220)
        st.markdown(prompt)

    chat["lang"] = lang
    with st.chat_message("assistant"):
        try:
            with st.status(t("thinking", lang), expanded=True) as status:
                res = asyncio.run(chat_turn_multilingual(
                    chat, prompt, img_path,
                    on_step=lambda s: st.write(step_label(s, lang))))
                status.update(label=t("done", lang), state="complete", expanded=False)
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