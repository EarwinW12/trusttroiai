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
# CSS (MUSS VOR AUTHENTICATION KOMMEN!)
# ============================================================================

# Legal Theme Colors
bg_color = "#FFFAF2"
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
    
    /* Legal Theme */
    * {{
        font-family: 'Times New Roman', 'Crimson Text', serif;
    }}
    
    .main {{
        background-color: {bg_color};
        color: {text_primary};
    }}
    
    /* Legal Header */
    .legal-header {{
        text-align: center;
        padding: 2rem 0 1.5rem 0;
        border-bottom: 2px solid {border_color};
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
    
    /* Login Box Styling */
    .stTextInput > div > div > input {{
        background-color: {input_bg};
        border: 2px solid {border_color};
        border-radius: 4px;
        font-family: 'Times New Roman', serif;
    }}
    
    .stButton > button {{
        background: {trust_color} !important;
        color: white !important;
        border: 2px solid {trust_color} !important;
        border-radius: 4px !important;
        padding: 0.5rem 2rem !important;
        font-family: 'Times New Roman', serif !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }}
    
    .stButton > button:hover {{
        background: {troiai_color} !important;
        border-color: {troiai_color} !important;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# AUTHENTICATION SYSTEM
# ============================================================================

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        username = st.session_state["username"].strip()
        password = st.session_state["password"]
        
        if "users" in st.secrets and username in st.secrets["users"]:
            if st.secrets["users"][username] == password:
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = username
                st.session_state["user_role"] = st.secrets.get("roles", {}).get(username, "user")
                del st.session_state["password"]  # Passwort nicht speichern
                
            else:
                st.session_state["password_correct"] = False
        else:
            st.session_state["password_correct"] = False

    # Wenn bereits eingeloggt
    if st.session_state.get("password_correct", False):
        return True

    # Login-Seite anzeigen
    st.markdown(f"""
    <style>
        {st.session_state.get('custom_css', '')}
    </style>
    """, unsafe_allow_html=True)
    
    # Login Header
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
    
    # Login-Box
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="
            background: #FFFFFF;
            padding: 2rem;
            border-radius: 8px;
            border: 2px solid #D4C5B9;
            box-shadow: 0 2px 8px rgba(1, 23, 52, 0.1);
        ">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔐 Anmeldung erforderlich")
        st.markdown("Bitte geben Sie Ihre Zugangsdaten ein, um fortzufahren.")
        
        st.text_input(
            "Benutzername", 
            key="username",
            placeholder="Ihr Benutzername"
        )
        st.text_input(
            "Passwort", 
            type="password", 
            key="password",
            placeholder="Ihr Passwort"
        )
        
        st.button("🔓 Anmelden", on_click=password_entered, use_container_width=True)
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Benutzername oder Passwort falsch")
        
        st.markdown("---")
        st.caption("💡 **Test-User?** Kontaktieren Sie den Administrator für Zugangsdaten.")
    
    return False

# ============================================================================
# AUTHENTICATION CHECK
# ============================================================================

if not check_password():
    st.stop()

# ============================================================================
# AB HIER: HAUPTAPP (NUR FÜR EINGELOGGTE USER)
# ============================================================================

# Header mit Logo / HTML Block

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

with st.sidebar:
    # User-Info oben
    st.markdown("### 👤 Angemeldet")
    
    user = st.session_state.get("current_user", "Unbekannt")
    role = st.session_state.get("user_role", "user")
    
    role_icon = "👑" if role == "admin" else "👤"
    
    st.info(f"{role_icon} **{user}**")
    
    if st.button("🚪 Abmelden", use_container_width=True):
        # Session State zurücksetzen
        st.session_state["password_correct"] = False
        st.session_state.pop("current_user", None)
        st.session_state.pop("user_role", None)
        if 'backend' in st.session_state:
            st.session_state.backend.clear_memory()
        st.session_state.messages = []
        st.session_state.clear()  # Komplett zurücksetzen
        
        st.rerun()
    
    st.divider()
    
    st.markdown("### ⚙️ Konfiguration")
    
    # API Key aus Secrets (nicht mehr vom User eingegeben)
    if "MISTRAL_API_KEY" in st.secrets:
        api_key = st.secrets["MISTRAL_API_KEY"]
        st.success("✅ API verbunden")
    else:
        st.error("❌ Kein API Key in Secrets gefunden")
        st.stop()
    
    st.divider()
    
    st.markdown("### 🔍 Filter")
    law_filter = st.selectbox(
        "Gesetz",
        ["Alle", "KI-Verordnung", "DSGVO"],
        index=0
    )
    
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

# Dokumente prüfen
doc_paths, missing_docs = check_documents()

if missing_docs:
    st.error("❌ Folgende Dokumente fehlen:")
    for key, filename in missing_docs:
        st.error(f"  • {filename}")
    st.stop()

# ============================================================================
# BACKEND INITIALISIERUNG (LAZY LOADING)
# ============================================================================

@st.cache_resource(show_spinner=False)
def init_backend(_api_key, _doc_paths):
    """Initialisiert das RAG Backend. Cached für Performance."""
    backend = get_rag_backend(_api_key)
    backend.setup(_doc_paths)
    return backend

# Backend nur laden wenn noch nicht vorhanden
if 'backend' not in st.session_state:
    with st.spinner("🔄 Initialisiere KI-Backend... Bitte warten (ca. 10-30 Sekunden)"):
        try:
            backend = init_backend(api_key, doc_paths)
            st.session_state.backend = backend
            st.success("✅ Backend erfolgreich geladen!", icon="✅")
        except Exception as e:
            st.error(f"❌ Backend-Initialisierung fehlgeschlagen: {str(e)}")
            st.info("💡 Bitte laden Sie die Seite neu oder kontaktieren Sie den Support.")
            st.stop()
else:
    backend = st.session_state.backend

if "messages" not in st.session_state:
    st.session_state.messages = []

if len(st.session_state.messages) == 0:
    
    st.markdown('<div class="suggestion-section-title">Beginnen Sie Ihre Recherche</div>', unsafe_allow_html=True)
    st.markdown('<div class="suggestion-subtitle">Wählen Sie eine Frage oder stellen Sie Ihre eigene</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3, gap="medium")
    
    suggestions = [
        {
            "icon": "§",
            "title": "DEFINITIONEN",
            "question": "Wie wird KI-System nach der KI-Verordnung definiert?"
        },
        {
            "icon": "⚖",
            "title": "PFLICHTEN",
            "question": "Welche Pflichten hat ein Anbieter eines Hochrisiko-KI-Systems?"
        },
        {
            "icon": "⚡",
            "title": "ZUSAMMENSPIEL",
            "question": "Wie ergänzen sich KI-Verordnung und DSGVO bei der Verarbeitung personenbezogener Daten?"
        }
    ]
    
    for col, suggestion in zip([col1, col2, col3], suggestions):
        with col:
            st.markdown(f'<div class="category-header"><span>{suggestion["icon"]}</span> {suggestion["title"]}</div>', unsafe_allow_html=True)
            
            if st.button(
                suggestion["question"],
                key=f"card_{hash(suggestion['question'])}",
                use_container_width=True
            ):
                st.session_state.messages.append({"role": "user", "content": suggestion["question"]})
                
                with st.spinner("Recherchiere..."):
                    try:
                        response = backend.query(
                            question=suggestion["question"],
                            filter_law=filter_law,
                            show_sources=show_sources
                        )
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response['answer'],
                            "sources": response.get('sources', [])
                        })
                        
                    except Exception as e:
                        st.error(f"❌ {e}")
                
                st.rerun()
    
    st.divider()

st.markdown("### 💬 Konversation")

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
                response = backend.query(
                    question=prompt,
                    filter_law=filter_law,
                    show_sources=show_sources
                )
                
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

st.markdown('<div class="disclaimer">⚠️ TrustTroiAI dient ausschließlich Informationszwecken und ersetzt keine Rechtsberatung.</div>', unsafe_allow_html=True)
