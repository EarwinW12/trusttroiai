import streamlit as st
from rag_backend import get_rag_backend
import os

st.set_page_config(
    page_title="TrustTroiAI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS - LEGAL THEME - ✅ ANGEPASSTE FARBEN
# ============================================================================

# ✅ NEUE Farben (Claude.ai Style - harmonisch)
bg_color = "#fff6e6"  # ✅ NEU: Haupthintergrund
sidebar_bg = "#fff6e8"  # ✅ NEU: Sidebar (nur minimal dunkler als Hauptbereich)

# Bestehende Farben
trust_color = "#011734"
troiai_color = "#84352C"
beta_color = "#011734"
text_primary = "#011734"
text_secondary = "#5A5A5A"
border_color = "#D4C5B9"
card_bg = "#FFFFFF"
input_bg = "#FFFFFF"
suggestion_card_bg = "#FAF7F2"
suggestion_card_border = "#D4C5B9"
suggestion_card_text = "#011734"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:wght@400;600;700&display=swap');
    
    * {{
        font-family: 'Times New Roman', 'Crimson Text', serif;
    }}
    
    /* ✅ NEU: Haupthintergrund */
    .main {{
        background-color: {bg_color} !important;
        color: {text_primary};
    }}
    
    /* ✅ NEU: Sidebar-Hintergrund */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 2px solid {border_color};
    }}
    
    /* ✅ NEU: Sidebar-Content auch mit neuem Hintergrund */
    [data-testid="stSidebar"] > div:first-child {{
        background-color: {sidebar_bg} !important;
    }}
    
    .legal-header {{
        text-align: center;
        padding: 2rem 0 1.5rem 0;
        border-bottom: none;
        margin-bottom: 2rem;
    }}
    
    .title-text {{
        font-family: 'Arial', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        line-height: 1;
    }}
    
    .title-trust {{
        color: {trust_color};
    }}
    
    .title-troiai {{
        color: {troiai_color};
    }}
    
    .beta-badge {{
        display: inline-block;
        background: transparent;
        color: {beta_color};
        border: 2px solid {beta_color};
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.6rem;
        font-weight: 700;
        font-family: 'Arial', sans-serif;
        margin-left: 0.2rem;
        vertical-align: super;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}
    
    .subtitle {{
        font-family: 'Times New Roman', serif;
        font-size: 0.9rem;
        color: {text_secondary};
        margin-top: 0.5rem;
        font-style: italic;
        text-align: center;
    }}
    
    .suggestion-section-title {{
        font-family: 'Times New Roman', serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: {text_primary};
        margin-bottom: 0.5rem;
        margin-top: 2rem;
        border-bottom: none;
        padding-bottom: 0.5rem;
    }}
    
    .suggestion-subtitle {{
        font-family: 'Times New Roman', serif;
        font-size: 0.95rem;
        color: {text_secondary};
        margin-bottom: 1.5rem;
        font-style: italic;
    }}
    
    div[data-testid="column"] {{
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }}
    
    div[data-testid="column"] .stButton > button {{
        background-color: {suggestion_card_bg} !important;
        color: {suggestion_card_text} !important;
        border: 2px solid {suggestion_card_border} !important;
        border-radius: 4px !important;
        padding: 1rem !important;
        min-height: 200px !important;
        max-height: 200px !important;
        height: 200px !important;
        width: 100% !important;
        font-family: 'Times New Roman', serif !important;
        font-weight: 400 !important;
        font-size: 0.9rem !important;
        line-height: 1.5 !important;
        text-align: center !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        overflow: hidden !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(1, 23, 52, 0.1) !important;
    }}
    
    div[data-testid="column"] .stButton > button:hover {{
        border-color: {troiai_color} !important;
        box-shadow: 0 4px 12px rgba(132, 53, 44, 0.2) !important;
        transform: translateY(-2px) !important;
        background-color: {card_bg} !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button {{
        background: {trust_color} !important;
        color: white !important;
        border: 2px solid {trust_color} !important;
        border-radius: 4px !important;
        padding: 0.5rem 0.75rem !important;
        font-family: 'Times New Roman', serif !important;
        font-size: 0.9rem !important;
        height: auto !important;
        min-height: auto !important;
        max-height: none !important;
        font-weight: 600 !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: {troiai_color} !important;
        border-color: {troiai_color} !important;
    }}
    
    .stTextInput > div > div > input {{
        background-color: {input_bg};
        color: {text_primary};
        border: 2px solid {border_color};
        border-radius: 4px;
        font-family: 'Times New Roman', serif;
    }}
    
    .stSelectbox > div > div {{
        background-color: {input_bg};
        color: {text_primary};
        border: 2px solid {border_color};
        font-family: 'Times New Roman', serif;
    }}
    
    [data-testid="stChatMessage"] {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 4px;
        padding: 1rem;
        margin: 0.5rem 0;
        font-family: 'Times New Roman', serif;
    }}
    
    .stChatInput {{
        font-family: 'Times New Roman', serif;
    }}
    
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3 {{
        font-family: 'Times New Roman', serif;
        color: {text_primary};
    }}
    
    .disclaimer {{
        text-align: center;
        padding: 1.5rem 0;
        border-top: none;
        margin-top: 4rem;
        font-family: 'Times New Roman', serif;
        font-size: 0.85rem;
        color: {text_secondary};
        font-style: italic;
    }}

    hr {{
        display: none !important;
    }}
    
    /* Dashboard Tool Cards */
    .tool-card {{
        background: {suggestion_card_bg};
        border: 2px solid {suggestion_card_border};
        border-radius: 8px;
        padding: 2rem;
        cursor: pointer;
        transition: all 0.3s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    
    .tool-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 8px 16px rgba(1, 23, 52, 0.15);
        border-color: {troiai_color};
    }}
    
    .tool-card-disabled {{
        background: #F5F5F5;
        border: 2px solid #E0E0E0;
        opacity: 0.6;
        cursor: not-allowed;
    }}
    
    .tool-card-disabled:hover {{
        transform: none;
        box-shadow: none;
    }}
    
    .tool-icon {{
        font-size: 3rem;
        text-align: center;
        margin-bottom: 1rem;
    }}
    
    .tool-title {{
        font-size: 1.5rem;
        font-weight: 700;
        text-align: center;
        color: {text_primary};
        margin-bottom: 1rem;
    }}
    
    .tool-description {{
        text-align: center;
        color: {text_secondary};
        font-style: italic;
        font-size: 0.95rem;
        line-height: 1.6;
    }}
    
    .coming-soon {{
        text-align: center;
        color: {troiai_color};
        font-weight: bold;
        margin-top: 1rem;
        font-size: 1rem;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# AUTHENTICATION SYSTEM
# ============================================================================

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        username = st.session_state["username"].strip()
        password = st.session_state["password"]
        
        if "users" in st.secrets and username in st.secrets["users"]:
            if st.secrets["users"][username] == password:
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = username
                st.session_state["user_role"] = st.secrets.get("roles", {}).get(username, "user")
                del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown(f"""
    <div class="legal-header">
        <div style="text-align: center; padding: 2rem 0 1rem 0;">
            <span class="title-text">
                <span class="title-trust">trust</span><span class="title-troiai">troiai</span>
            </span>
            <span class="beta-badge">Beta</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Anmeldung erforderlich")
        st.markdown("Bitte geben Sie Ihre Zugangsdaten ein, um fortzufahren.")
        
        st.text_input("Benutzername", key="username", placeholder="Ihr Benutzername")
        st.text_input("Passwort", type="password", key="password", placeholder="Ihr Passwort")
        
        st.button("🔓 Anmelden", on_click=password_entered, use_container_width=True)
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Benutzername oder Passwort falsch")
        
        st.caption("💡 **Test-User?** Kontaktieren Sie den Administrator für Zugangsdaten.")
    
    return False

if not check_password():
    st.stop()

# ============================================================================
# NAVIGATION SYSTEM
# ============================================================================

if "current_page" not in st.session_state:
    st.session_state.current_page = None

def switch_page(page_name):
    st.session_state.current_page = page_name
    st.rerun()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_documents():
    doc_paths = {
        'ki_vo_corpus': 'data/KI_Verordnung_07_2025_Corpus.docx',
        'ki_vo_anhaenge': 'data/KI_Verordnung_Stand_07_2025 Extract[124-144]_Anhänge conv_chunkready.docx',
        'ki_vo_ewg': 'data/KI_Verordnung_18_09_2025_EWG_chunk ready .docx',
        'ki_vo_begriffe': 'data/KI_Verordnung_Begriffbestimmung.docx',
        'dsgvo_corpus': 'data/DSGVO_Corpus_StandOktober2025_chunk ready.docx',
        'dsgvo_ewg': 'data/DSGVO_EWG_StandOktober2025_Chunkready.docx',
        'dsgvo_begriffe': 'data/DSGVO_Begriffbestimmung.docx'
    }
    
    missing = []
    for key, path in doc_paths.items():
        if not os.path.exists(path):
            missing.append((key, os.path.basename(path)))
    
    return doc_paths, missing

@st.cache_resource(show_spinner=False)
def init_backend(_api_key, _doc_paths):
    backend = get_rag_backend(_api_key)
    backend.setup(_doc_paths)
    return backend

# ============================================================================
# DASHBOARD - ✅ ENTFERNT: Dashboard und Assistant Kacheln
# ============================================================================

def show_dashboard():
    st.markdown(f"""
    <div class="legal-header">
        <div style="display: flex; flex-direction: column; align-items: center; width: 100%;">
            <div style="white-space: nowrap;">
                <span class="title-text">
                    <span class="title-trust">trust</span><span class="title-troiai">troiai</span>
                </span>
                <span class="beta-badge">Beta</span>
            </div>
            <div class="subtitle" style="margin-top: 0.5rem;">
                Dein KI-Verordnung und DSGVO Plattform
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    user = st.session_state.get("current_user", "User")
    st.markdown(f"### 👋 Willkommen, {user}!")
    
    # ✅ DIREKTE WEITERLEITUNG ZUM ASSISTANT
    # Statt Kacheln zu zeigen, gehe direkt zum Assistant
    st.info("🚀 Sie werden zum Assistant weitergeleitet...")
    switch_page("assistant")

# ============================================================================
# SIDEBAR - ✅ ENTFERNT: Dashboard und Assistant Buttons
# ============================================================================

def show_sidebar(current_page="assistant"):
    with st.sidebar:
        st.markdown("### 👤 Angemeldet")
        
        user = st.session_state.get("current_user", "Unbekannt")
        role = st.session_state.get("user_role", "user")
        role_icon = "👑" if role == "admin" else "👤"
        
        st.info(f"{role_icon} **{user}**")
        
        if st.button("🚪 Abmelden", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        st.divider()
        
        # ✅ ENTFERNT: Kein "Dashboard" oder "Assistant" Button mehr
        # ✅ ENTFERNT: Compliance Checker bleibt als "Coming Soon"
        
        st.markdown("### 🔍 Tools")
        st.button("🔍 Compliance Checker", use_container_width=True, key="nav_checker", disabled=True)
        st.caption("🚧 Coming Soon")
        
        if current_page == "assistant":
            st.divider()
            st.markdown("### ⚙️ Konfiguration")
            
            if "MISTRAL_API_KEY" in st.secrets:
                api_key = st.secrets["MISTRAL_API_KEY"]
                st.success("✅ API verbunden")
            else:
                st.error("❌ Kein API Key")
                st.stop()
            
            st.markdown("### 🔍 Filter")
            law_filter = st.selectbox("Gesetz", ["Alle", "KI-Verordnung", "DSGVO"], index=0)
            filter_law = None if law_filter == "Alle" else law_filter
            show_sources = st.checkbox("📚 Quellen anzeigen", value=True)
            
            st.divider()
            st.markdown("### 💭 Konversation")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🆕 Neu", use_container_width=True, key="new_conv"):
                    if 'backend' in st.session_state and st.session_state.backend:
                        st.session_state.backend.clear_memory()
                        st.session_state.messages = []
                        st.success("✅")
                        st.rerun()
            
            with col2:
                if st.button("📊 Stats", use_container_width=True, key="stats"):
                    if 'backend' in st.session_state and st.session_state.backend:
                        stats = st.session_state.backend.get_memory_stats()
                        st.json(stats)
            
            return api_key, filter_law, show_sources
        
        return None, None, None

# ============================================================================
# ASSISTANT PAGE
# ============================================================================

def show_assistant_page():
    api_key, filter_law, show_sources = show_sidebar("assistant")
    
    st.markdown(f"""
    <div class="legal-header">
        <div style="display: flex; flex-direction: column; align-items: center; width: 100%;">
            <div style="white-space: nowrap;">
                <span class="title-text">
                    <span class="title-trust">trust</span><span class="title-troiai">troiai</span>
                </span>
                <span class="beta-badge">Beta</span>
            </div>
            <div class="subtitle" style="margin-top: 0.5rem;">
                Dein KI-Verordnung und DSGVO Assistant
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    doc_paths, missing_docs = check_documents()
    
    if missing_docs:
        st.error("❌ Folgende Dokumente fehlen:")
        for key, filename in missing_docs:
            st.error(f"  • {filename}")
        st.stop()
    
    if 'backend' not in st.session_state:
        with st.spinner("🔄 Initialisiere KI-Backend... Bitte warten (ca. 10-30 Sekunden)"):
            try:
                import traceback
                backend = init_backend(api_key, doc_paths)
                st.session_state.backend = backend
                st.success("✅ Backend erfolgreich geladen!", icon="✅")
            except Exception as e:
                st.error(f"❌ Backend-Initialisierung fehlgeschlagen!")
                st.error(f"**Fehler:** {str(e)}")
                st.code(traceback.format_exc())
                st.stop()
    else:
        backend = st.session_state.backend
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if len(st.session_state.messages) == 0:
        st.markdown('<div class="suggestion-section-title">⚖️ Starte hier dein Compliance-Journey</div>', unsafe_allow_html=True)
        st.markdown('<div class="suggestion-subtitle">Wählen Sie eine Frage oder stellen Sie Ihre eigene</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3, gap="medium")
        
        suggestions = [
            {"question": "Wie wird KI-System nach der KI-Verordnung definiert?"},
            {"question": "Welche Pflichten hat ein Anbieter eines Hochrisiko-KI-Systems?"},
            {"question": "Wie ergänzen sich KI-Verordnung und DSGVO bei der Verarbeitung personenbezogener Daten?"}
        ]
        
        for col, suggestion in zip([col1, col2, col3], suggestions):
            with col:
                if st.button(suggestion["question"], key=f"card_{hash(suggestion['question'])}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": suggestion["question"]})
                    
                    with st.spinner("Recherchiere..."):
                        try:
                            response = backend.query(question=suggestion["question"], filter_law=filter_law, show_sources=show_sources)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": response['answer'],
                                "sources": response.get('sources', [])
                            })
                        except Exception as e:
                            st.error(f"❌ {e}")
                    
                    st.rerun()
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if "sources" in message and message["sources"] and show_sources:
                with st.expander("📚 Quellen"):
                    for i, source in enumerate(message["sources"][:3], 1):
                        law = source.metadata.get('source_law', 'N/A')
                        artikel = source.metadata.get('artikel', source.metadata.get('source_type', 'N/A'))
                        st.markdown(f"**{i}. {law} - {artikel}**")
                        st.caption(f"_{source.page_content[:200]}..._")
    
    if prompt := st.chat_input("Ihre Frage zur KI-VO oder DSGVO..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Recherchiere..."):
                try:
                    response = backend.query(question=prompt, filter_law=filter_law, show_sources=show_sources)
                    st.markdown(response['answer'])
                    
                    if response.get('sources') and show_sources:
                        with st.expander("📚 Quellen"):
                            for i, source in enumerate(response['sources'][:3], 1):
                                law = source.metadata.get('source_law', 'N/A')
                                artikel = source.metadata.get('artikel', source.metadata.get('source_type', 'N/A'))
                                st.markdown(f"**{i}. {law} - {artikel}**")
                                st.caption(f"_{source.page_content[:200]}..._")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response['answer'],
                        "sources": response.get('sources', [])
                    })
                except Exception as e:
                    st.error(f"❌ {e}")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="disclaimer">⚠️ TrustTroiAI dient ausschließlich Informationszwecken und ersetzt keine Rechtsberatung.</div>', unsafe_allow_html=True)

# ============================================================================
# ROUTING - ✅ DIREKT ZUM ASSISTANT
# ============================================================================

# ✅ VEREINFACHT: Keine Dashboard-Anzeige mehr, direkt zum Assistant
if st.session_state.current_page is None:
    # Setze direkt auf Assistant statt Dashboard zu zeigen
    st.session_state.current_page = "assistant"
    st.rerun()
elif st.session_state.current_page == "assistant":
    show_assistant_page()
