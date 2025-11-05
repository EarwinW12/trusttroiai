import streamlit as st
from rag_backend import get_rag_backend
import os

st.set_page_config(
    page_title="TrustTroiAI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Farben
bg_color = "#FFFFFF"
secondary_bg = "#F3F4F6"
text_primary = "#032D60"
text_secondary = "#6B7280"
border_color = "#E5E7EB"
card_bg = "#FFFFFF"
input_bg = "#FFFFFF"
suggestion_card_bg = "#FFFFFF"
suggestion_card_border = "#E0E0E0"
suggestion_card_text = "#1F2937"

st.markdown(f"""
<style>
    @font-face {{
        font-family: 'Salesforce Sans';
        src: url('https://www.sfdcstatic.com/system/shared/common/assets/fonts/SalesforceSans/SalesforceSans-Regular.woff2') format('woff2');
        font-weight: 400;
    }}
    
    * {{
        font-family: 'Salesforce Sans', -apple-system, sans-serif;
    }}
    
    .main {{
        background-color: {bg_color};
        color: {text_primary};
    }}
    
    .main-title {{
        font-size: 3.5rem;
        font-weight: 400;
        letter-spacing: -0.02em;
        line-height: 1.1;
        margin-bottom: 0;
    }}
    
    .title-trust {{
        color: #aacbfd;
    }}
    
    .title-troiai {{
        color: #f0cc89;
    }}
    
    .beta-badge {{
        display: inline-block;
        background: #0066CC;
        color: white;
        padding: 0.3rem 0.7rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 400;
        font-family: 'Salesforce Sans', sans-serif;
        margin-left: 1rem;
        vertical-align: middle;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    .subtitle {{
        font-size: 1.125rem;
        color: {text_secondary};
        margin-top: 0.75rem;
        font-weight: 400;
    }}
    
    .suggestion-section-title {{
        font-size: 1.5rem;
        font-weight: 600;
        color: {text_primary};
        margin-bottom: 0.5rem;
        margin-top: 2rem;
    }}
    
    .suggestion-subtitle {{
        font-size: 0.875rem;
        color: {text_secondary};
        margin-bottom: 1.5rem;
    }}
    
    .category-header {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: {text_secondary};
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    div[data-testid="column"] {{
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }}
    
    div[data-testid="column"] .stButton > button {{
        background-color: {suggestion_card_bg} !important;
        color: {suggestion_card_text} !important;
        border: 1px solid {suggestion_card_border} !important;
        border-radius: 8px !important;
        padding: 1.25rem !important;
        min-height: 160px !important;
        max-height: 160px !important;
        height: 160px !important;
        width: 100% !important;
        font-weight: 400 !important;
        font-size: 0.9375rem !important;
        line-height: 1.5 !important;
        text-align: center !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        overflow: hidden !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }}
    
    div[data-testid="column"] .stButton > button:hover {{
        border-color: #0176D3 !important;
        box-shadow: 0 4px 12px rgba(1, 118, 211, 0.15) !important;
        transform: translateY(-2px) !important;
    }}
    
    [data-testid="stSidebar"] {{
        background-color: {secondary_bg};
        border-right: 1px solid {border_color};
    }}
    
    [data-testid="stSidebar"] .stButton > button {{
        background: #0176D3 !important;
        color: white !important;
        border: 1px solid #0176D3 !important;
        border-radius: 4px !important;
        padding: 0.5rem 0.75rem !important;
        font-size: 0.875rem !important;
        height: auto !important;
        min-height: auto !important;
        max-height: none !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: #014486 !important;
        border-color: #014486 !important;
    }}
    
    .stTextInput > div > div > input {{
        background-color: {input_bg};
        color: {text_primary};
        border: 1px solid {border_color};
        border-radius: 4px;
    }}
    
    .stSelectbox > div > div {{
        background-color: {input_bg};
        color: {text_primary};
        border: 1px solid {border_color};
    }}
    
    [data-testid="stChatMessage"] {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align: center; padding: 2.5rem 0 2rem 0;">
    <div class="main-title">
        <span class="title-trust">Trust</span><span class="title-troiai">TroiAI</span>
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
    
    st.markdown('<div class="suggestion-section-title">💡 Starte hier deine Compliance Journey!</div>', unsafe_allow_html=True)
    st.markdown('<div class="suggestion-subtitle">Klicke auf eine Frage um zu beginnen</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3, gap="medium")
    
    suggestions = [
        {
            "icon": "📋",
            "title": "DEFINITIONEN",
            "question": "Wie wird KI-System nach der KI-Verordnung definiert?"
        },
        {
            "icon": "⚖️",
            "title": "PFLICHTEN",
            "question": "Welche Pflichten hat ein Anbieter eines Hochrisiko-KI-Systems?"
        },
        {
            "icon": "🔗",
            "title": "ÜBERSCHNEIDUNG KI-VO UND DSGVO",
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
                
                with st.spinner("🤔 Denke nach..."):
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

st.markdown("### 💬 Chat")

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

if prompt := st.chat_input("Frage zur KI-VO oder DSGVO..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("💭 Denke nach..."):
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

st.divider()
st.caption("⚠️ TrustTroiAI kann Fehler machen. Keine Rechtsberatung.")
