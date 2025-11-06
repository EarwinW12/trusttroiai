
"""
RAG Backend - VOLLSTÄNDIGE VERSION MIT ALLEN DOKUMENTEN
"""

import warnings
warnings.filterwarnings("ignore")

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import time
import re

from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationalRetrievalChain  
from langchain_core.prompts import PromptTemplate

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import Qdrant


# ==============================================================================
# PIPELINE TYPES
# ==============================================================================

class PipelineType(Enum):
    SEMANTIC = "semantic"
    KEYWORD_METADATA = "keyword_metadata"
    DEFINITIONS_KI_VO = "definitions_ki_vo"
    DEFINITIONS_DSGVO = "definitions_dsgvo"
    DEFINITIONS_GENERIC = "definitions_generic"


@dataclass
class QueryAnalysis:
    pipeline_type: PipelineType
    confidence: float
    detected_patterns: List[str]
    extracted_references: Dict[str, Any]


# ==============================================================================
# QUERY ROUTER
# ==============================================================================

class AdvancedQueryRouter:
    def __init__(self, defined_terms_ki_vo: List[str], defined_terms_dsgvo: List[str]):
        self.defined_terms_ki_vo = [t.lower() for t in defined_terms_ki_vo]
        self.defined_terms_dsgvo = [t.lower() for t in defined_terms_dsgvo]

        self.definition_keywords = [
            'definiert', 'definition', 'begriff', 'bedeutung', 'bedeutet',
            'meint', 'versteht man unter', 'bezeichnet', 'ist gemeint',
            'was ist', 'was sind', 'erklärung', 'erkläre',
        ]

        self.keyword_patterns = {
            'artikel': [r'artikel\s+(\d+)', r'art\.?\s*(\d+)'],
            'kapitel': [r'kapitel\s+([ivxIVX]+)', r'kapitel\s+(\d+)'],
            'anhang': [r'anhang\s+([ivxIVX]+)', r'anhang\s+(\d+)'],
            'erwägungsgrund': [
                r'erwägungsgrund\s+(\d+)',
                r'erwägungsgründe?\s+(\d+)',
                r'ewg\.?\s*(\d+)',
                r'ewg\s+(\d+)',
                r'erw\.?\s*(\d+)',
                r'\(ewg\s+(\d+)\)',
                r'recital\s+(\d+)',
            ],
        }

    def analyze_query(self, query: str) -> QueryAnalysis:
        query_lower = query.lower()

        # Definition-Query?
        is_definition_query = any(kw in query_lower for kw in self.definition_keywords)

        if is_definition_query:
            extracted_term = self._extract_term(query)

            if extracted_term:
                detected_law = self._detect_law(query)

                if self._term_in_list(extracted_term, self.defined_terms_ki_vo):
                    return QueryAnalysis(
                        pipeline_type=PipelineType.DEFINITIONS_KI_VO,
                        confidence=0.95,
                        detected_patterns=[f"def_{extracted_term}"],
                        extracted_references={'term': extracted_term, 'law': 'KI-Verordnung'}
                    )

                elif self._term_in_list(extracted_term, self.defined_terms_dsgvo):
                    return QueryAnalysis(
                        pipeline_type=PipelineType.DEFINITIONS_DSGVO,
                        confidence=0.95,
                        detected_patterns=[f"def_{extracted_term}"],
                        extracted_references={'term': extracted_term, 'law': 'DSGVO'}
                    )

                elif detected_law:
                    if detected_law == 'KI-Verordnung':
                        return QueryAnalysis(
                            pipeline_type=PipelineType.DEFINITIONS_KI_VO,
                            confidence=0.8,
                            detected_patterns=[f"def_{extracted_term}"],
                            extracted_references={'term': extracted_term, 'law': 'KI-Verordnung'}
                        )
                    else:
                        return QueryAnalysis(
                            pipeline_type=PipelineType.DEFINITIONS_DSGVO,
                            confidence=0.8,
                            detected_patterns=[f"def_{extracted_term}"],
                            extracted_references={'term': extracted_term, 'law': 'DSGVO'}
                        )

                else:
                    return QueryAnalysis(
                        pipeline_type=PipelineType.DEFINITIONS_GENERIC,
                        confidence=0.7,
                        detected_patterns=[f"def_{extracted_term}"],
                        extracted_references={'term': extracted_term, 'law': None}
                    )

        # Keyword/Metadata?
        detected_patterns = []
        extracted_references = {}

        for pattern_type, patterns in self.keyword_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, query_lower, re.IGNORECASE)
                for match in matches:
                    reference = match.group(1)
                    if pattern_type in ['anhang', 'kapitel']:
                        reference = self._normalize_number(reference)

                    detected_patterns.append(f"{pattern_type}_{reference}")
                    if pattern_type not in extracted_references:
                        extracted_references[pattern_type] = []
                    extracted_references[pattern_type].append(reference)

        if detected_patterns:
            return QueryAnalysis(
                pipeline_type=PipelineType.KEYWORD_METADATA,
                confidence=min(0.9, len(detected_patterns) * 0.3 + 0.6),
                detected_patterns=detected_patterns,
                extracted_references=extracted_references
            )

        return QueryAnalysis(
            pipeline_type=PipelineType.SEMANTIC,
            confidence=0.8,
            detected_patterns=['semantic'],
            extracted_references={}
        )

    def _extract_term(self, query: str) -> Optional[str]:
        query_lower = query.lower()
        query_clean = re.sub(r'\b(?:laut|gemäß|nach|der|des)\s+(?:ki-verordnung|ki-vo|dsgvo|art\.?\s*\d+)\b', '', query_lower)
        query_clean = re.sub(r'\b(?:ki-verordnung|ki-vo|dsgvo)\b', '', query_clean)

        match = re.search(r'wie\s+(?:wird|werden)\s+(.+?)\s+(?:definiert|bezeichnet)', query_clean)
        if match:
            return self._clean_term(match.group(1))

        match = re.search(r'was\s+(?:bedeutet|ist|sind)\s+(?:ein|eine|der|die|das)?\s*(.+?)(?:\?|$)', query_clean)
        if match:
            return self._clean_term(match.group(1))

        match = re.search(r'definition\s+(?:von|für|des|der)\s+(.+?)(?:\?|$)', query_clean)
        if match:
            return self._clean_term(match.group(1))

        return None

    def _detect_law(self, query: str) -> Optional[str]:
        query_lower = query.lower()
        if 'ki-verordnung' in query_lower or 'ki-vo' in query_lower:
            return 'KI-Verordnung'
        elif 'dsgvo' in query_lower:
            return 'DSGVO'
        return None

    def _clean_term(self, term: str) -> str:
        term = re.sub(r'[?.,!]', '', term)
        term = re.sub(r'^(?:ein|eine|der|die|das|den|dem|laut|gemäß|nach)\s+', '', term)
        term = re.sub(r'\s+(?:laut|gemäß|nach|der|des)$', '', term)
        return term.strip()

    def _term_in_list(self, term: str, term_list: List[str]) -> bool:
        term_clean = term.lower().strip()

        if term_clean in term_list:
            return True

        term_variants = [
            term_clean,
            term_clean.replace('-', ' '),
            term_clean.replace(' ', '-'),
            term_clean.replace('-', ''),
            term_clean.replace(' ', ''),
        ]

        for variant in term_variants:
            if variant in term_list:
                return True

        if len(term_clean) >= 4:
            for defined_term in term_list:
                if term_clean in defined_term or (defined_term in term_clean and len(defined_term) >= 4):
                    return True

        return False

    def _normalize_number(self, num_str: str) -> str:
        roman_to_arabic = {
            'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5',
            'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'
        }
        return roman_to_arabic.get(num_str.strip().lower(), num_str)


# ==============================================================================
# KEYWORD RETRIEVER
# ==============================================================================

class KeywordMetadataRetriever:
    def __init__(self, vectorstore, all_chunks: List[Document]):
        self.vectorstore = vectorstore
        self.all_chunks = all_chunks
        self.metadata_index = self._build_metadata_index()

    def _build_metadata_index(self) -> Dict[str, Dict[str, List[Document]]]:
        index = {
            'artikel': {},
            'erwägungsgrund': {}
        }
        
        for chunk in self.all_chunks:
            metadata = chunk.metadata
            source_type = metadata.get('source_type', '').lower()
            
            # Index für Artikel
            for key in ['Artikel', 'artikel']:
                if key in metadata:
                    artikel_value = str(metadata[key]).lower()
                    match = re.search(r'artikel\s+(\d+)', artikel_value)
                    
                    if match:
                        artikel_num = match.group(1)
                        if artikel_num not in index['artikel']:
                            index['artikel'][artikel_num] = []
                        index['artikel'][artikel_num].append(chunk)
                    break
            
            # Index für Erwägungsgründe
            if 'erwägung' in source_type:
                # Versuche EWG-Nummer aus Content zu extrahieren
                ewg_patterns = [
                    r'erwägungsgrund\s+(\d+)',
                    r'ewg\s+(\d+)',
                    r'\((\d+)\)',  # Nummer in Klammern
                    r'^(\d+)\.',   # Nummer am Anfang mit Punkt
                ]
                
                for pattern in ewg_patterns:
                    match = re.search(pattern, chunk.page_content.lower())
                    if match:
                        ewg_num = match.group(1)
                        if ewg_num not in index['erwägungsgrund']:
                            index['erwägungsgrund'][ewg_num] = []
                        index['erwägungsgrund'][ewg_num].append(chunk)
                        break
        
        return index

    def retrieve_by_metadata(self, extracted_references: Dict[str, Any], k: int = 5) -> List[Document]:
        results = []
    
        # Artikel suchen
        if 'artikel' in extracted_references:
            for artikel_num in extracted_references['artikel']:
                if str(artikel_num) in self.metadata_index['artikel']:
                    results.extend(self.metadata_index['artikel'][str(artikel_num)])
        
        # Erwägungsgründe suchen
        if 'erwägungsgrund' in extracted_references:
            for ewg_num in extracted_references['erwägungsgrund']:
                if str(ewg_num) in self.metadata_index['erwägungsgrund']:
                    results.extend(self.metadata_index['erwägungsgrund'][str(ewg_num)])
                else:
                    # Fallback: Semantische Suche
                    ewg_query = f"Erwägungsgrund {ewg_num}"
                    semantic_results = self.vectorstore.similarity_search(
                        ewg_query, 
                        k=3,
                        filter={'source_type': 'Erwägungsgründe'} if hasattr(self.vectorstore, 'filter') else None
                    )
                    results.extend(semantic_results)

        unique_results = []
        seen = set()

        for doc in results:
            h = hash(doc.page_content[:100])
            if h not in seen:
                unique_results.append(doc)
                seen.add(h)
                if len(unique_results) >= k:
                    break

        return unique_results


# ==============================================================================
# DEFINITIONS RETRIEVER
# ==============================================================================

class DefinitionsRetriever:
    def __init__(self, vectorstore, qdrant_client, collection_name, all_chunks, embeddings):
        self.vectorstore = vectorstore
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.all_chunks = all_chunks
        self.embeddings = embeddings
        self.definitions_index = self._build_index()

    def _build_index(self) -> Dict[str, List[Document]]:
        index = {}
        definition_chunks = [
            c for c in self.all_chunks
            if c.metadata.get('source_type') == 'Begriffsbestimmungen'
        ]

        for chunk in definition_chunks:
            match = re.search(r'###\s*(\d+)\.\s*([^\n]+)', chunk.page_content)

            if match:
                term_raw = match.group(2).strip()
                term_clean = term_raw.strip('"\'„""')
                term_lower = term_clean.lower()
                variants = self._generate_variants(term_lower)

                for variant in variants:
                    if variant not in index:
                        index[variant] = []
                    if chunk not in index[variant]:
                        index[variant].append(chunk)

        return index

    def _generate_variants(self, term: str) -> List[str]:
        variants = set()
        variants.add(term)

        if '-' in term:
            variants.add(term.replace('-', ' '))
            variants.add(term.replace('-', ''))

        if ' ' in term:
            variants.add(term.replace(' ', '-'))
            variants.add(term.replace(' ', ''))

        term_stripped = term.rstrip('.,;:')
        if term_stripped != term:
            variants.add(term_stripped)

        return list(variants)

    def retrieve_definition(self, term: str, law: Optional[str] = None, k: int = 2) -> List[Document]:
        search_variants = self._generate_variants(term.lower())

        found_docs = []

        for variant in search_variants:
            if variant in self.definitions_index:
                docs = self.definitions_index[variant]

                if law:
                    docs = [d for d in docs if d.metadata.get('source_law') == law]

                found_docs.extend(docs)
                break

        if not found_docs:
            found_docs = self._fuzzy_search_in_index(term.lower(), law)

        unique_docs = []
        seen_hashes = set()

        for doc in found_docs:
            doc_hash = hash(doc.page_content[:200])
            if doc_hash not in seen_hashes:
                unique_docs.append(doc)
                seen_hashes.add(doc_hash)

        if unique_docs:
            return unique_docs[:k]

        return []

    def _fuzzy_search_in_index(self, term: str, law: Optional[str]) -> List[Document]:
        term_clean = term.lower().strip()
        found_docs = []

        for index_key, docs in self.definitions_index.items():
            if term_clean in index_key or index_key in term_clean:
                if len(term_clean) >= 4 and len(index_key) >= 4:
                    if law:
                        docs = [d for d in docs if d.metadata.get('source_law') == law]

                    found_docs.extend(docs)
                    break

        return found_docs


# ==============================================================================
# TRIPLE PIPELINE MANAGER
# ==============================================================================

class TriplePipelineManager:
    def __init__(
        self,
        vectorstore,
        qdrant_client,
        collection_name,
        llm,
        qa_chain,
        advanced_router,
        keyword_retriever,
        definitions_retriever
    ):
        self.vectorstore = vectorstore
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.llm = llm
        self.qa_chain = qa_chain
        self.router = advanced_router
        self.keyword_retriever = keyword_retriever
        self.definitions_retriever = definitions_retriever

    def process_query(self, query: str, filter_law: Optional[str] = None) -> Dict[str, Any]:
        needs_context = self._needs_conversation_context(query)

        if needs_context:
            return self._handle_semantic(query, filter_law)

        analysis = self.router.analyze_query(query)

        if analysis.pipeline_type in [
            PipelineType.DEFINITIONS_KI_VO,
            PipelineType.DEFINITIONS_DSGVO,
            PipelineType.DEFINITIONS_GENERIC
        ]:
            return self._handle_definitions(query, analysis)

        elif analysis.pipeline_type == PipelineType.KEYWORD_METADATA:
            return self._handle_keyword_metadata(query, analysis, filter_law)

        else:
            return self._handle_semantic(query, filter_law)

    def _needs_conversation_context(self, query: str) -> bool:
        query_lower = query.lower()

        context_indicators = [
            'das', 'dies', 'diese', 'dieser', 'unterschied', 'vergleich',
            'auch', 'zusätzlich', 'und was', 'wie ist',
        ]

        has_indicator = any(indicator in query_lower for indicator in context_indicators)
        word_count = len(query.split())
        is_short = word_count < 5
        has_history = len(self.qa_chain.memory.chat_memory.messages) > 0

        return (has_indicator or is_short) and has_history

    def _handle_definitions(self, query: str, analysis: QueryAnalysis) -> Dict[str, Any]:
        term = analysis.extracted_references.get('term')
        law = analysis.extracted_references.get('law')

        docs = self.definitions_retriever.retrieve_definition(term, law, k=2)

        if not docs:
            return self._handle_semantic(query, law)

        context = "\n\n".join([
            f"📖 DEFINITION aus {doc.metadata.get('source_law')} {doc.metadata.get('artikel')}:\n{doc.page_content}"
            for doc in docs
        ])

        chat_history = self._get_chat_history_text()

        prompt = f"""Du bist Rechtsexperte. Beantworte die Frage PRÄZISE.

WICHTIGE REGELN:
1. **PRÜFE ZUERST:** Ist die Definition im bereitgestellten Kontext?
   - ✅ JA → Gib die offizielle Definition wieder
   - ❌ NEIN → Sage: "Diese Definition finde ich in den bereitgestellten Begriffsbestimmungen nicht."

2. Nenne die Quelle (z.B. "KI-VO Art. 3 Nr. 1")
3. KEINE Spekulationen oder zusätzliche Erklärungen außerhalb des Kontexts

{chat_history}

BEGRIFFSDEFINITIONEN:
{context}

AKTUELLE FRAGE: {query}

ANTWORT (kurz und präzise):"""

        response = self.llm.invoke(prompt)
        self._save_to_memory(query, response.content)

        return {
            'result': response.content,
            'source_documents': docs,
            'pipeline_used': f'definitions_{analysis.pipeline_type.value}'
        }

    def _handle_keyword_metadata(self, query: str, analysis: QueryAnalysis, filter_law: Optional[str]) -> Dict[str, Any]:
    docs = self.keyword_retriever.retrieve_by_metadata(
        analysis.extracted_references,
        k=5
    )
    
    if filter_law and docs:
        docs = [d for d in docs if d.metadata.get('source_law') == filter_law]
    
    if not docs:
        return self._handle_semantic(query, filter_law)
    
    context = "\n\n".join([doc.page_content for doc in docs])
    chat_history = self._get_chat_history_text()
    
    # Spezial-Prompt für Erwägungsgründe
    if 'erwägungsgrund' in analysis.extracted_references:
        ewg_nums = ', '.join(map(str, analysis.extracted_references['erwägungsgrund']))
        prompt = f"""{chat_history}

ERWÄGUNGSGRUND-SUCHE:
Der User fragt nach Erwägungsgrund(en): {ewg_nums}

GEFUNDENER KONTEXT:
{context}

WICHTIG:
1. Wenn der exakte Erwägungsgrund im Kontext ist → Fasse ihn zusammen
2. Wenn nur verwandte Erwägungsgründe da sind → Erkläre was gefunden wurde
3. Wenn gar nichts passt → Sage ehrlich: "Erwägungsgrund {ewg_nums} finde ich in den Dokumenten nicht explizit."

AKTUELLE FRAGE: {query}

ANTWORT:"""
    else:
        # Standard Prompt für Artikel etc.
        prompt = f"""{chat_history}

KONTEXT:
{context}

AKTUELLE FRAGE: {query}

ANTWORT:"""

        response = self.llm.invoke(prompt)
        self._save_to_memory(query, response.content)

        return {
            'result': response.content,
            'source_documents': docs,
            'pipeline_used': 'keyword_metadata'
        }

    def _handle_semantic(self, query: str, filter_law: Optional[str]) -> Dict[str, Any]:
        result = self.qa_chain({"question": query})

        return {
            'result': result['answer'],
            'source_documents': result.get('source_documents', []),
            'pipeline_used': 'semantic_with_memory'
        }

    def _get_chat_history_text(self) -> str:
        messages = self.qa_chain.memory.chat_memory.messages

        if not messages:
            return ""

        history_lines = []
        for msg in messages[-6:]:
            if msg.type == "human":
                history_lines.append(f"User: {msg.content}")
            else:
                history_lines.append(f"Assistant: {msg.content}")

        if history_lines:
            return "BISHERIGE KONVERSATION:\n" + "\n".join(history_lines) + "\n"

        return ""

    def _save_to_memory(self, query: str, response: str):
        self.qa_chain.memory.chat_memory.add_message(HumanMessage(content=query))
        self.qa_chain.memory.chat_memory.add_message(AIMessage(content=response))

    def clear_memory(self):
        self.qa_chain.memory.clear()

    def get_memory_stats(self) -> Dict[str, Any]:
        messages = self.qa_chain.memory.chat_memory.messages
        return {
            'total_messages': len(messages),
            'capacity': self.qa_chain.memory.k
        }


# ==============================================================================
# RAG BACKEND
# ==============================================================================

class RAGBackend:
    def __init__(self, mistral_api_key: str):
        self.mistral_api_key = mistral_api_key
        self.initialized = False

        self.vectorstore = None
        self.qdrant_client = None
        self.embeddings = None
        self.llm = None
        self.triple_pipeline = None
        self.all_chunks = []

        self.COLLECTION_NAME = "legal_compliance_v3"

    def setup(self, document_paths: Dict[str, str]):
        print("\n" + "="*70)
        print("🔧 VOLLSTÄNDIGES SETUP MIT TRIPLE PIPELINE")
        print("="*70)

        try:
            # 1. ALLE Dokumente laden
            print("\n📚 LADE ALLE DOKUMENTE...")
            self.all_chunks = self._load_all_documents(document_paths)

            if not self.all_chunks:
                raise ValueError("Keine Chunks erstellt!")

            print(f"\n✅ GESAMT: {len(self.all_chunks)} Chunks")

            # 2. Models
            print("\n🤖 INITIALISIERE MODELS...")
            self._initialize_models()

            # 3. Vectorstore
            print("\n💾 ERSTELLE VECTORSTORE...")
            self._create_vectorstore()

            # 4. Triple Pipeline
            print("\n🔧 ERSTELLE TRIPLE PIPELINE...")
            self._create_triple_pipeline()

            self.initialized = True
            print("\n✅ VOLLSTÄNDIGES SETUP ABGESCHLOSSEN!")
            print("   🔵 Pipeline 1: Semantic Search")
            print("   🟢 Pipeline 2: Keyword/Metadata")
            print("   🟡 Pipeline 3: Definitions")

        except Exception as e:
            print(f"\n❌ FEHLER: {e}")
            raise

    def _load_all_documents(self, paths: Dict[str, str]) -> List[Document]:
        all_chunks = []

        # KI-VO Corpus
        try:
            print("\n🔵 KI-VERORDNUNG:")
            print("   1/7 Corpus...")
            loader = Docx2txtLoader(paths['ki_vo_corpus'])
            pages = loader.load()
            headers = [("#", "Kapitel"), ("##", "Abschnitt"), ("###", "Artikel")]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, strip_headers=False)
            chunks = splitter.split_text(pages[0].page_content)

            for chunk in chunks:
                chunk.metadata['source_type'] = 'Corpus'
                chunk.metadata['source_law'] = 'KI-Verordnung'

            all_chunks.extend(chunks)
            print(f"      ✅ {len(chunks)} Chunks")
        except Exception as e:
            print(f"      ❌ Fehler: {e}")

        # KI-VO Anhänge
        try:
            print("   2/7 Anhänge...")
            loader = Docx2txtLoader(paths['ki_vo_anhaenge'])
            pages = loader.load()
            headers = [("#", "Anhang"), ("##", "Abschnitt")]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, strip_headers=False)
            chunks = splitter.split_text(pages[0].page_content)

            for chunk in chunks:
                chunk.metadata['source_type'] = 'Anhang'
                chunk.metadata['source_law'] = 'KI-Verordnung'

            all_chunks.extend(chunks)
            print(f"      ✅ {len(chunks)} Chunks")
        except Exception as e:
            print(f"      ❌ Fehler: {e}")

        # KI-VO EWG
        try:
            print("   3/7 Erwägungsgründe...")
            loader = Docx2txtLoader(paths['ki_vo_ewg'])
            pages = loader.load()
            headers = [("#", "Erwägungsgrund")]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, strip_headers=False)
            chunks = splitter.split_text(pages[0].page_content)

            for chunk in chunks:
                chunk.metadata['source_type'] = 'Erwägungsgründe'
                chunk.metadata['source_law'] = 'KI-Verordnung'

            all_chunks.extend(chunks)
            print(f"      ✅ {len(chunks)} Chunks")
        except Exception as e:
            print(f"      ❌ Fehler: {e}")

        # KI-VO Begriffe
        try:
            print("   4/7 Begriffsbestimmungen...")
            loader = Docx2txtLoader(paths['ki_vo_begriffe'])
            pages = loader.load()
            headers = [("###", "Begriff")]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, strip_headers=False)
            chunks = splitter.split_text(pages[0].page_content)

            for chunk in chunks:
                chunk.metadata['source_type'] = 'Begriffsbestimmungen'
                chunk.metadata['source_law'] = 'KI-Verordnung'
                chunk.metadata['artikel'] = 'Artikel 3'

            all_chunks.extend(chunks)
            print(f"      ✅ {len(chunks)} Chunks")
        except Exception as e:
            print(f"      ❌ Fehler: {e}")

        # DSGVO Corpus
        try:
            print("\n🟢 DSGVO:")
            print("   5/7 Corpus...")
            loader = Docx2txtLoader(paths['dsgvo_corpus'])
            pages = loader.load()
            headers = [("#", "Kapitel"), ("##", "Abschnitt"), ("###", "Artikel")]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, strip_headers=False)
            chunks = splitter.split_text(pages[0].page_content)

            for chunk in chunks:
                chunk.metadata['source_type'] = 'Corpus'
                chunk.metadata['source_law'] = 'DSGVO'

            all_chunks.extend(chunks)
            print(f"      ✅ {len(chunks)} Chunks")
        except Exception as e:
            print(f"      ❌ Fehler: {e}")

        # DSGVO EWG
        try:
            print("   6/7 Erwägungsgründe...")
            loader = Docx2txtLoader(paths['dsgvo_ewg'])
            pages = loader.load()
            headers = [("#", "Erwägungsgrund")]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, strip_headers=False)
            chunks = splitter.split_text(pages[0].page_content)

            for chunk in chunks:
                chunk.metadata['source_type'] = 'Erwägungsgründe'
                chunk.metadata['source_law'] = 'DSGVO'

            all_chunks.extend(chunks)
            print(f"      ✅ {len(chunks)} Chunks")
        except Exception as e:
            print(f"      ❌ Fehler: {e}")

        # DSGVO Begriffe
        try:
            print("   7/7 Begriffsbestimmungen...")
            loader = Docx2txtLoader(paths['dsgvo_begriffe'])
            pages = loader.load()
            headers = [("###", "Begriff")]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, strip_headers=False)
            chunks = splitter.split_text(pages[0].page_content)

            for chunk in chunks:
                chunk.metadata['source_type'] = 'Begriffsbestimmungen'
                chunk.metadata['source_law'] = 'DSGVO'
                chunk.metadata['artikel'] = 'Artikel 4'

            all_chunks.extend(chunks)
            print(f"      ✅ {len(chunks)} Chunks")
        except Exception as e:
            print(f"      ❌ Fehler: {e}")

        return all_chunks

    def _initialize_models(self):
        self.embeddings = MistralAIEmbeddings(
            model="mistral-embed",
            mistral_api_key=self.mistral_api_key
        )

        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            mistral_api_key=self.mistral_api_key,
            timeout=120,

        )

        print("   ✅ Models bereit")

    def _create_vectorstore(self):
        if not self.all_chunks:
            raise ValueError("all_chunks ist leer!")

        self.qdrant_client = QdrantClient(":memory:")

        self.qdrant_client.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )

        print(f"   📥 Indexiere {len(self.all_chunks)} Chunks...")

        start_time = time.time()

        self.vectorstore = Qdrant.from_documents(
            self.all_chunks,
            self.embeddings,
            location=":memory:",
            collection_name=self.COLLECTION_NAME
        )

        elapsed = time.time() - start_time
        print(f"   ✅ Indexierung in {elapsed:.1f}s")

    def _create_triple_pipeline(self):
        # Extrahiere Begriffe
        def extract_defined_terms(chunks: List[Document]) -> List[str]:
            terms = []
            for chunk in chunks:
                matches = re.finditer(r'###\s*(\d+)\.\s*(.+?)(?:\n|$)', chunk.page_content)
                for match in matches:
                    term = match.group(2).strip()
                    term = term.strip('"\'„"')
                    term = term.lower()
                    terms.append(term)
            return sorted(list(set(terms)))

        defs_ki_vo = [c for c in self.all_chunks if c.metadata.get('source_law') == 'KI-Verordnung'
                      and c.metadata.get('source_type') == 'Begriffsbestimmungen']
        defs_dsgvo = [c for c in self.all_chunks if c.metadata.get('source_law') == 'DSGVO'
                      and c.metadata.get('source_type') == 'Begriffsbestimmungen']

        DEFINED_TERMS_KI_VO = extract_defined_terms(defs_ki_vo)
        DEFINED_TERMS_DSGVO = extract_defined_terms(defs_dsgvo)

        print(f"   🔵 KI-VO: {len(DEFINED_TERMS_KI_VO)} Begriffe")
        print(f"   🟢 DSGVO: {len(DEFINED_TERMS_DSGVO)} Begriffe")

        # Memory
        conversation_memory = ConversationBufferWindowMemory(
            k=5,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )

        semantic_template = """Du bist ein Compliance-Assistent für KI-VO und DSGVO.

Beantworte basierend auf Chat-Historie und Kontext-Dokumenten.

WICHTIGE REGELN:
1. **PRÜFE ZUERST:** Steht die Antwort im bereitgestellten Kontext?
   - ✅ JA → Beantworte präzise mit Quellenangabe
   - ❌ NEIN → Sage GENAU: "Diese Information finde ich in den bereitgestellten Dokumenten nicht."

2. **Keine Spekulation:** Erfinde KEINE Informationen die nicht im Kontext stehen

3. **Bei vorherigen Fragen:** Beziehe dich auf Chat-Historie falls relevant

4. **Präzise & angemessen:** 3-7 Sätze reichen. User kann Folgefragen stellen

5. **Quellenangabe:** Nenne immer Artikel/Abschnitt (z.B. "KI-VO Art. 5" oder "DSGVO Art. 6")

Antwortstruktur:
- Direkte Antwort mit Artikelreferenz (KI-VO oder DSGVO)

§ **Primärquellen**
   - Liste relevante Artikel/Anhänge/Erwägungsgründe
   - z.B: "KI-VO Art. 11 Abs. 1" oder "DSGVO Art. 5"

- Im Anschluss Stelle nur eine weiterführende Frage zum Thema. Dieses sorgt um weitere Unterhaltung mit dem User.

KONTEXT:
{context}

FRAGE:
{question}

ANTWORT:
"""

        QA_PROMPT = PromptTemplate(
            input_variables=["context", "question"],
            template=semantic_template
        )

        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
            memory=conversation_memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": QA_PROMPT},
            verbose=False
        )

        # Router
        advanced_router = AdvancedQueryRouter(DEFINED_TERMS_KI_VO, DEFINED_TERMS_DSGVO)

        # Keyword Retriever
        keyword_retriever = KeywordMetadataRetriever(self.vectorstore, self.all_chunks)

        # Definitions Retriever
        definitions_retriever = DefinitionsRetriever(
            self.vectorstore,
            self.qdrant_client,
            self.COLLECTION_NAME,
            self.all_chunks,
            self.embeddings
        )

        # Triple Pipeline Manager
        self.triple_pipeline = TriplePipelineManager(
            vectorstore=self.vectorstore,
            qdrant_client=self.qdrant_client,
            collection_name=self.COLLECTION_NAME,
            llm=self.llm,
            qa_chain=qa_chain,
            advanced_router=advanced_router,
            keyword_retriever=keyword_retriever,
            definitions_retriever=definitions_retriever
        )

        print("   ✅ Triple Pipeline bereit")

    def query(
        self,
        question: str,
        filter_law: Optional[str] = None,
        show_sources: bool = False
    ) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Backend not initialized!")

        result = self.triple_pipeline.process_query(question, filter_law)

        return {
            'answer': result.get('result', ''),
            'sources': result.get('source_documents', []) if show_sources else [],
            'pipeline_used': result.get('pipeline_used', 'unknown'),
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def clear_memory(self):
        if self.triple_pipeline:
            self.triple_pipeline.clear_memory()

    def get_memory_stats(self) -> Dict[str, Any]:
        if self.triple_pipeline:
            return self.triple_pipeline.get_memory_stats()
        return {}

    def get_vectordb_stats(self) -> Dict[str, Any]:
        if self.qdrant_client:
            info = self.qdrant_client.get_collection(self.COLLECTION_NAME)
            return {
                'collection': self.COLLECTION_NAME,
                'vectors_count': info.vectors_count,
                'status': info.status
            }
        return {}


# ==============================================================================
# SINGLETON
# ==============================================================================

_backend_instance = None

def get_rag_backend(mistral_api_key: str) -> RAGBackend:
    global _backend_instance

    if _backend_instance is None:
        _backend_instance = RAGBackend(mistral_api_key)

    return _backend_instance


__all__ = ['RAGBackend', 'get_rag_backend']

print("✅ rag_backend.py - VOLLSTÄNDIG MIT TRIPLE PIPELINE")
