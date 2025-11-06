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
        letter-spacing: -0.02em;
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
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 700;
        font-family: 'Arial', sans-serif;
        margin-left: 0.75rem;
        vertical-align: middle;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}
    
    .subtitle {{
        font-family: 'Times New Roman', serif;
        font-size: 1.125rem;
        color: {text_secondary};
        margin-top: 0.5rem;
        font-style: italic;
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

# Base64-kodiertes Logo
logo_base64 = """iVBORw0KGgoAAAANSUhEUgAAAmoAAACgCAYAAAC8PkCEAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAAEnQAABJ0Ad5mH3gAADNPSURBVHhe7d0HXJXlHwfwHyACMkUEXOAAd+6dI3Nr2lLTtmbWtXI01HJX3kpblqO91ExNM8tKcy/ce+MAxcWSvcd9/w9vZSpwkHMO7+H+vvfy6TzvOSDwnpfzO8/4P3a5GQm5ICIiIiLDsdf/S0REREQGw6BGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGxaBGREREZFAMakREREQGZZebkZCr3yYiIjKknOxsJMZEIykqGplpqcjNyYV9mTJwci0Hdx9flPPyhJ09+x6o9GFQIyIiQ8vKSMfJzZtx9M+1iDwdiuRr11RQK+NUVgtpFeFXOxi127dH3bs6w97BQf8sotKBQY2IiAzt5OZN+OO995CWkIgaLVuiWqNGcHJzRUJkJE5t3Yqos2fh4umBht26o8vzL8ChTBn9M4lsH4MaEREZ1vlDB7FQC1/eAdXQe9yrqHZHQ/2ePBkpqdi1ZDF2Lv4BmWlp6PzsCLQaOAB2dnb6I4hsG4MaEREZUmZqGhaMekHNS+s7cSICmzW7dQDLzcW5vXux6dNPkJOTg3unTEWFgAD9TiLbxpmXRERkSGH79yEmPAzBHdujWuPG+feSacdrtGiBu59/AbERF3D5xHEtu7EPgkoHBjUiIjKczPR0nA7ZjozkVNRs2dqkeWdelfxVQDu8ejWyMzP1o0S2jUGNiIgMR3rSwnbv0YJXDg799htyc3L0e/IXHX5eC3YpOL9vP1LiYvWjRLaNQY2IiIwlNxfnDxxC/JUrqule0cekGmmJUVGqPEdOdhZ2/rBEP0pk2xjUiIjIULLS07Fn6WLVmybzz9KSkkyac5aTlQknNzc4e3rgwC8rce3SRf0eItvFoEZERIayY+kSxF2+DBdPz78L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"""

st.markdown(f"""
<div class="legal-header">
    <div style="text-align: center; margin-bottom: 1rem;">
        <img src="data:image/png;base64,{logo_base64}" 
             width="80" 
             height="80">
    </div>
    <div style="text-align: center;">
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
