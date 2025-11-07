import streamlit as st
from rag_backend import get_rag_backend
import os

st.set_page_config(
    page_title="TrustTroiAI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Legal Theme Colors
bg_color = "#FFFAF2"              # Cremeweiß
trust_color = "#011734"           # Dunkelblau
troiai_color = "#84352C"          # Rostrot
beta_color = "#011734"            # Dunkelblau
text_primary = "#011734"          # Dunkelblau
text_secondary = "#5A5A5A"        # Grau
border_color = "#D4C5B9"          # Beige
card_bg = "#FFFFFF"               # Weiß
input_bg = "#FFFFFF"              # Weiß
suggestion_card_bg = "#FAF7F2"    # Helles Beige
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
    
    /* Header mit Logo */
    .legal-header {{
        text-align: center;
        padding: 2rem 0 1.5rem 0;
        border-bottom: 2px solid {border_color};
        margin-bottom: 2rem;
    }}
    
    .logo-title {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        margin-bottom: 0.5rem;
    }}
    
    .title-text {{
    font-family: 'Arial', sans-serif;
    font-size: 3.5rem;
    font-weight: 700;
    letter-spacing: 0.15em;  /* Abstand zwischen Buchstaben */
    line-height: 1;
    }}
    
    .title-trust {{
        color: {trust_color};
        letter-spacing: inherit;  /* Erbt letter-spacing */
    }}
    
    .title-troiai {{
        color: {troiai_color};
        letter-spacing: inherit;  /* Erbt letter-spacing */
    }}
    
    .beta-badge {{
        display: inline-block;
        background: transparent;
        color: {beta_color};
        border: 2px solid {beta_color};
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 700;
        font-family: 'Arial', sans-serif;
        margin-left: 0.5rem;
        vertical-align: middle;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}
    
    .subtitle {{
    font-family: 'Times New Roman', serif;
    font-size: 0.95rem;  /* ← GEÄNDERT: von 1.125rem auf 0.95rem (kleiner) */
    color: {text_secondary};
    margin-top: 0.5rem;
    font-style: italic;
    text-align: center;  /* ← NEU: Zentriert den Text */
    }}
    
    .suggestion-section-title {{
        font-family: 'Times New Roman', serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: {text_primary};
        margin-bottom: 0.5rem;
        margin-top: 2rem;
        border-bottom: 1px solid {border_color};
        padding-bottom: 0.5rem;
    }}
    
    .suggestion-subtitle {{
        font-family: 'Times New Roman', serif;
        font-size: 0.95rem;
        color: {text_secondary};
        margin-bottom: 1.5rem;
        font-style: italic;
    }}
    
    .category-header {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-family: 'Times New Roman', serif;
        font-size: 0.8rem;
        font-weight: 600;
        color: {text_secondary};
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
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
        padding: 1.25rem !important;
        min-height: 160px !important;
        max-height: 160px !important;
        height: 160px !important;
        width: 100% !important;
        font-family: 'Times New Roman', serif !important;
        font-weight: 400 !important;
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
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
    
    [data-testid="stSidebar"] {{
        background-color: {suggestion_card_bg};
        border-right: 2px solid {border_color};
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
    
    /* Chat Input */
    .stChatInput {{
        font-family: 'Times New Roman', serif;
    }}
    
    /* Headers in Chat */
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3 {{
        font-family: 'Times New Roman', serif;
        color: {text_primary};
    }}
    
    /* Disclaimer */
    .disclaimer {{
        text-align: center;
        padding: 1.5rem 0;
        border-top: 1px solid {border_color};
        margin-top: 2rem;
        font-family: 'Times New Roman', serif;
        font-size: 0.85rem;
        color: {text_secondary};
        font-style: italic;
    }}
</style>
""", unsafe_allow_html=True)

# Header mit Logo
logo_exists = os.path.exists('assets/trusttroiai_logo.png')

if logo_exists:
    # Mit Logo
    st.markdown(f"""
    <div class="legal-header">
        <div class="logo-title">
            <img src="app/static/trusttroiai_logo.png" width="60" height="60" style="vertical-align: middle;">
            <span class="title-text">
                <span class="title-trust">trust</span><span class="title-troiai">troiai</span>
            </span>
            <span class="beta-badge">Beta</span>
        </div>
        <div class="subtitle">
            Dein KI-Verordnung und DSGVO Assistant
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Ohne Logo (Fallback)
    st.markdown(f"""
    <div class="legal-header">
        <div>
            <span class="title-text">
                <span class="title-trust">trust</span><span class="title-troiai">troiai</span>
            </span>
            <span class="beta-badge">Beta</span>
        </div>
        <div class="subtitle">
            Dein KI-Verordnung und DSGVO Assistant
        </div>
    </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Konfiguration")
    
    api_key = st.text_input(
        "Mistral API Key",
        type="password",
        placeholder="sk-..."
    )
    
    if not api_key:
        st.warning("⚠️ API Key erforderlich")
        st.stop()
    else:
        st.success("✅ Verbunden")
    
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

doc_paths, missing_docs = check_documents()

if missing_docs:
    st.error("❌ Dokumente fehlen")
    st.stop()

@st.cache_resource
def init_backend(api_key):
    backend = get_rag_backend(api_key)
    backend.setup(doc_paths)
    return backend

with st.spinner("🔄 Initialisiere Backend..."):
    try:
        backend = init_backend(api_key)
        st.session_state.backend = backend
    except Exception as e:
        st.error(f"❌ {e}")
        st.stop()

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
