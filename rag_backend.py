"""
RAG Backend - VERBESSERTE VERSION MIT FIXES
TrustTroiAI - KI-VO & DSGVO Compliance Assistant

ÄNDERUNGEN:
- ✅ FIX 1: Verbesserte EWG-Erkennung mit Multi-Strategie-Ansatz
- ✅ FIX 2: Validierung der gefundenen Dokumente
- ✅ FIX 3: Fallback zu Semantic Search bei Keyword-Fehlern
- ✅ Logging für besseres Debugging
"""

import warnings
warnings.filterwarnings("ignore")

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import time
import re
import logging

from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import Qdrant

# ✅ NEU: Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
# KEYWORD RETRIEVER - ✅ FIX 1 & 2
# ==============================================================================

class KeywordMetadataRetriever:
    def __init__(self, vectorstore, all_chunks: List[Document]):
        self.vectorstore = vectorstore
        self.all_chunks = all_chunks
        self.metadata_index = self._build_metadata_index()
        logger.info(f"📊 Metadata-Index erstellt: {self._get_index_stats()}")
    
    def _build_metadata_index(self) -> Dict[str, Dict[str, List[Document]]]:
        """✅ FIX 1: VERBESSERTE EWG-Erkennung mit Multi-Strategie-Ansatz"""
        index = {
            'artikel': {},
            'erwägungsgrund': {},
            'anhang': {}
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
            
            # ✅ FIX 1: VERBESSERTE Index für Erwägungsgründe
            if 'erwägung' in source_type:
                ewg_num = None
                
                # Strategie 1: Aus Metadata holen (höchste Priorität)
                if 'ewg_nummer' in metadata:
                    ewg_num = str(metadata['ewg_nummer'])
                    logger.debug(f"   EWG aus Metadata: {ewg_num}")
                
                # Strategie 2: Aus Markdown-Header extrahieren
                elif 'Erwägungsgrund' in metadata:
                    header_value = str(metadata['Erwägungsgrund'])
                    match = re.search(r'(\d+)', header_value)
                    if match:
                        ewg_num = match.group(1)
                        logger.debug(f"   EWG aus Header: {ewg_num}")
                
                # Strategie 3: Aus Content (erste 300 Zeichen) extrahieren
                if not ewg_num:
                    first_lines = chunk.page_content[:300]
                    
                    # Verbesserte Pattern-Liste (in Priorität)
                    patterns = [
                        r'#\s*Erwägungsgrund\s+(\d+)',      # "# Erwägungsgrund 15"
                        r'#\s*\((\d+)\)',                    # "# (15)"
                        r'^Erwägungsgrund\s+(\d+)',          # "Erwägungsgrund 15" am Anfang
                        r'^\((\d+)\)',                       # "(15)" am Zeilenanfang
                        r'EWG\s+(\d+)',                      # "EWG 15"
                        r'Recital\s+(\d+)',                  # "Recital 15"
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, first_lines, re.MULTILINE | re.IGNORECASE)
                        if match:
                            ewg_num = match.group(1)
                            logger.debug(f"   EWG aus Content (Pattern: {pattern}): {ewg_num}")
                            break
                
                # Indexiere wenn gefunden
                if ewg_num:
                    if ewg_num not in index['erwägungsgrund']:
                        index['erwägungsgrund'][ewg_num] = []
                    index['erwägungsgrund'][ewg_num].append(chunk)
                    logger.debug(f"   ✅ EWG {ewg_num} indexiert ({metadata.get('source_law')})")
                else:
                    logger.warning(f"   ⚠️ EWG-Nummer nicht gefunden in Chunk: {chunk.page_content[:100]}...")
            
            # Index für Anhänge
            if 'anhang' in source_type:
                for key in ['Anhang', 'anhang']:
                    if key in metadata:
                        anhang_value = str(metadata[key]).lower()
                        match = re.search(r'anhang\s+([ivxIVX]+|\d+)', anhang_value)
                        
                        if match:
                            anhang_num = self._normalize_number(match.group(1))
                            if anhang_num not in index['anhang']:
                                index['anhang'][anhang_num] = []
                            index['anhang'][anhang_num].append(chunk)
                        break
        
        return index
    
    def _get_index_stats(self) -> str:
        """Statistik über den Index für Logging"""
        stats = []
        for key, sub_index in self.metadata_index.items():
            count = len(sub_index)
            if count > 0:
                stats.append(f"{key}={count}")
        return ", ".join(stats)
    
    def _normalize_number(self, num_str: str) -> str:
        """Konvertiere römische zu arabischen Zahlen"""
        roman_to_arabic = {
            'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5',
            'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'
        }
        return roman_to_arabic.get(num_str.strip().lower(), num_str)
    
    def retrieve_by_metadata(self, extracted_references: Dict[str, Any], k: int = 5) -> List[Document]:
        """✅ FIX 2: Mit Validierung der gefundenen Dokumente"""
        logger.info(f"🔍 Keyword-Suche: {extracted_references}")
        results = []
        
        # Artikel suchen
        if 'artikel' in extracted_references:
            for artikel_num in extracted_references['artikel']:
                logger.info(f"   📌 Suche Artikel {artikel_num}...")
                if str(artikel_num) in self.metadata_index['artikel']:
                    found_docs = self.metadata_index['artikel'][str(artikel_num)]
                    logger.info(f"   ✅ {len(found_docs)} Chunks gefunden")
                    results.extend(found_docs)
                else:
                    logger.warning(f"   ❌ Artikel {artikel_num} NICHT im Index!")
        
        # ✅ FIX 2: Erwägungsgründe suchen MIT VALIDIERUNG
        if 'erwägungsgrund' in extracted_references:
            for ewg_num in extracted_references['erwägungsgrund']:
                logger.info(f"   📌 Suche EWG {ewg_num}...")
                
                if str(ewg_num) in self.metadata_index['erwägungsgrund']:
                    found_docs = self.metadata_index['erwägungsgrund'][str(ewg_num)]
                    logger.info(f"   ✅ {len(found_docs)} Chunks im Index gefunden")
                    
                    # ✅ NEU: Validiere dass EWG wirklich im Content ist
                    validated_docs = []
                    for doc in found_docs:
                        if self._validate_ewg_in_content(doc, ewg_num):
                            validated_docs.append(doc)
                            logger.debug(f"      ✓ EWG {ewg_num} validiert in Chunk")
                        else:
                            logger.warning(f"      ⚠️ EWG {ewg_num} im Index, aber NICHT im Content!")
                    
                    if validated_docs:
                        results.extend(validated_docs)
                        logger.info(f"   ✅ {len(validated_docs)} validierte Chunks")
                    else:
                        logger.error(f"   ❌ EWG {ewg_num} im Index, aber keine validierten Chunks!")
                else:
                    logger.warning(f"   ❌ EWG {ewg_num} NICHT im Index!")
        
        # Anhänge suchen
        if 'anhang' in extracted_references:
            for anhang_num in extracted_references['anhang']:
                logger.info(f"   📌 Suche Anhang {anhang_num}...")
                normalized = self._normalize_number(anhang_num)
                if normalized in self.metadata_index['anhang']:
                    found_docs = self.metadata_index['anhang'][normalized]
                    logger.info(f"   ✅ {len(found_docs)} Chunks gefunden")
                    results.extend(found_docs)
                else:
                    logger.warning(f"   ❌ Anhang {anhang_num} NICHT im Index!")
        
        # Deduplizieren
        unique_results = []
        seen = set()
        
        for doc in results:
            h = hash(doc.page_content[:100])
            if h not in seen:
                unique_results.append(doc)
                seen.add(h)
                if len(unique_results) >= k:
                    break
        
        logger.info(f"🎯 Keyword-Retrieval: {len(unique_results)} eindeutige Dokumente")
        return unique_results
    
    def _validate_ewg_in_content(self, doc: Document, ewg_num: str) -> bool:
        """✅ FIX 2: Validiere dass EWG-Nummer wirklich im Content steht"""
        content = doc.page_content.lower()
        
        # Validierungs-Patterns (müssen im Content vorkommen)
        patterns = [
            rf'erwägungsgrund\s+{ewg_num}\b',
            rf'\({ewg_num}\)',
            rf'ewg\s+{ewg_num}\b',
            rf'recital\s+{ewg_num}\b',
            rf'#\s*erwägungsgrund\s+{ewg_num}',
            rf'#\s*\({ewg_num}\)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False


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
# TRIPLE PIPELINE MANAGER - ✅ FIX 3
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
        logger.info(f"\n{'='*70}")
        logger.info(f"📥 NEUE ANFRAGE: {query}")
        logger.info(f"{'='*70}")
        
        needs_context = self._needs_conversation_context(query)
        
        if needs_context:
            logger.info("🔵 Pipeline: SEMANTIC (Kontext benötigt)")
            return self._handle_semantic(query, filter_law)
        
        analysis = self.router.analyze_query(query)
        logger.info(f"🎯 Query-Analyse: {analysis.pipeline_type.value} (Confidence: {analysis.confidence:.2f})")
        logger.info(f"   Erkannte Referenzen: {analysis.extracted_references}")
        
        if analysis.pipeline_type in [
            PipelineType.DEFINITIONS_KI_VO,
            PipelineType.DEFINITIONS_DSGVO,
            PipelineType.DEFINITIONS_GENERIC
        ]:
            logger.info("🟡 Pipeline: DEFINITIONS")
            return self._handle_definitions(query, analysis)
        
        elif analysis.pipeline_type == PipelineType.KEYWORD_METADATA:
            logger.info("🟢 Pipeline: KEYWORD/METADATA")
            return self._handle_keyword_metadata(query, analysis, filter_law)
        
        else:
            logger.info("🔵 Pipeline: SEMANTIC (Default)")
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
        
        logger.info(f"🔍 Definitions-Suche: Term='{term}', Law='{law}'")
        
        docs = self.definitions_retriever.retrieve_definition(term, law, k=2)
        
        if not docs:
            logger.warning(f"⚠️ Keine Definition gefunden für '{term}' - Fallback zu Semantic")
            return self._handle_semantic(query, law)
        
        logger.info(f"✅ {len(docs)} Definitions-Chunks gefunden")
        
        context = "\n\n".join([
            f"📖 DEFINITION aus {doc.metadata.get('source_law')} {doc.metadata.get('artikel')}:\n{doc.page_content}"
            for doc in docs
        ])
        
        chat_history = self._get_chat_history_text()
        
        prompt = f"""Du bist ein erfahrener Rechtsexperte für EU-Regulierungen. Beantworte die Frage natürlich und verständlich.

ANTWORTSTRUKTUR (ohne explizite Labels):

Beginne mit dem vollständigen Originaltext aus dem Dokument in Anführungszeichen. Nenne dabei die genaue Quelle in Klammern.

Erkläre dann in 2-4 Sätzen die praktische Bedeutung und Anwendung. Nutze wenn möglich ein konkretes Beispiel zur Veranschaulichung.

Schließe mit einer natürlichen weiterführenden Frage ab, die das Gespräch fortsetzt.

Am Ende liste die verwendeten Quellen auf.

BEISPIEL:

"'Betreiber' bezeichnet eine natürliche oder juristische Person, Behörde, Einrichtung oder sonstige Stelle, die ein KI-System unter ihrer Autorität nutzt, außer wenn das KI-System im Rahmen einer persönlichen nichtberuflichen Tätigkeit genutzt wird." (KI-VO Art. 3 Nr. 4)

Der Betreiber ist also die Organisation oder Person, die das KI-System tatsächlich im Arbeitsalltag einsetzt - nicht die Firma, die es entwickelt hat. Ein praktisches Beispiel: Wenn ein Krankenhaus ein KI-gestütztes Diagnose-Tool nutzt, ist das Krankenhaus der Betreiber, auch wenn die Software von einem externen Unternehmen stammt. Diese Unterscheidung ist wichtig, weil Betreiber und Anbieter unterschiedliche rechtliche Pflichten haben.

Interessiert Sie, welche konkreten Pflichten ein Betreiber eines Hochrisiko-KI-Systems erfüllen muss?

---
§ Verwendete Quellen:
- KI-VO Art. 3 Nr. 4

WICHTIG:
- Zitiere immer den kompletten Originaltext
- Keine erfundenen Informationen
- Wenn der Text nicht im Kontext ist, sage das ehrlich
- Schreibe natürlich und gesprächsartig, nicht wie ein Formular

{chat_history}

VERFÜGBARE DEFINITIONEN:
{context}

FRAGE DES NUTZERS: {query}

DEINE ANTWORT:"""
        
        response = self.llm.invoke(prompt)
        self._save_to_memory(query, response.content)
        
        return {
            'result': response.content,
            'source_documents': docs,
            'pipeline_used': f'definitions_{analysis.pipeline_type.value}'
        }
    
    def _handle_keyword_metadata(self, query: str, analysis: QueryAnalysis, filter_law: Optional[str]) -> Dict[str, Any]:
        """✅ FIX 3: Mit Fallback zu Semantic Search"""
        
        docs = self.keyword_retriever.retrieve_by_metadata(
            analysis.extracted_references,
            k=5
        )
        
        if filter_law and docs:
            docs = [d for d in docs if d.metadata.get('source_law') == filter_law]
            logger.info(f"   Filter '{filter_law}' angewendet: {len(docs)} Docs übrig")
        
        # ✅ FIX 3: Prüfe ob wir wirklich etwas gefunden haben
        if not docs:
            logger.warning("❌ Keyword-Retrieval fand NICHTS - Fallback zu Semantic Search")
            
            # Generiere hilfreiche Fehlermeldung
            missing_refs = []
            if 'artikel' in analysis.extracted_references:
                missing_refs.append(f"Artikel {', '.join(analysis.extracted_references['artikel'])}")
            if 'erwägungsgrund' in analysis.extracted_references:
                missing_refs.append(f"EWG {', '.join(analysis.extracted_references['erwägungsgrund'])}")
            if 'anhang' in analysis.extracted_references:
                missing_refs.append(f"Anhang {', '.join(analysis.extracted_references['anhang'])}")
            
            missing_str = " & ".join(missing_refs)
            
            # Semantic Search als Fallback
            semantic_result = self._handle_semantic(query, filter_law)
            
            # Füge Info hinzu, dass Keyword fehlschlug
            semantic_result['result'] = (
                f"ℹ️ *Hinweis: {missing_str} konnte nicht direkt gefunden werden. "
                f"Hier ist eine semantische Suche zum Thema:*\n\n" +
                semantic_result['result']
            )
            semantic_result['pipeline_used'] = 'keyword_metadata_fallback_to_semantic'
            
            return semantic_result
        
        # ✅ FIX 3: Validiere bei EWG-Suche, dass wir die richtigen gefunden haben
        if 'erwägungsgrund' in analysis.extracted_references:
            requested_ewgs = set(analysis.extracted_references['erwägungsgrund'])
            found_ewgs = set()
            
            for doc in docs:
                for ewg_num in requested_ewgs:
                    if self.keyword_retriever._validate_ewg_in_content(doc, str(ewg_num)):
                        found_ewgs.add(str(ewg_num))
            
            missing_ewgs = requested_ewgs - found_ewgs
            
            if missing_ewgs:
                logger.warning(f"⚠️ Nicht alle EWGs gefunden. Fehlt: {missing_ewgs}")
                
                # Teilweise gefunden - gib Info und nutze Semantic als Ergänzung
                if found_ewgs:
                    logger.info(f"✅ Gefunden: {found_ewgs} - Ergänze mit Semantic")
                    
                    # Nutze gefundene Docs + Semantic
                    semantic_result = self._handle_semantic(query, filter_law)
                    
                    # Kombiniere Ergebnisse
                    context_keyword = "\n\n".join([doc.page_content for doc in docs])
                    context_semantic = "\n\n".join([doc.page_content for doc in semantic_result.get('source_documents', [])])
                    
                    combined_context = f"**GEFUNDENE ERWÄGUNGSGRÜNDE:**\n{context_keyword}\n\n**WEITERE RELEVANTE INFORMATIONEN:**\n{context_semantic}"
                    
                    # Generiere kombinierte Antwort
                    chat_history = self._get_chat_history_text()
                    
                    prompt = f"""{chat_history}

Du bist Rechtsexperte. Der Nutzer fragt nach Erwägungsgründen.

WICHTIG:
- Wir haben nur TEILWEISE die gesuchten EWGs gefunden: {found_ewgs}
- FEHLEN: {missing_ewgs}
- Gib ZUERST die gefundenen EWGs vollständig wieder
- Erwähne dann transparent, welche fehlen
- Nutze die zusätzlichen Informationen um zu helfen

GEFUNDENER KONTEXT:
{combined_context}

FRAGE: {query}

ANTWORT:"""
                    
                    response = self.llm.invoke(prompt)
                    self._save_to_memory(query, response.content)
                    
                    return {
                        'result': response.content,
                        'source_documents': docs + semantic_result.get('source_documents', [])[:2],
                        'pipeline_used': 'keyword_metadata_partial_with_semantic'
                    }
                
                else:
                    # NICHTS gefunden - kompletter Fallback
                    logger.warning("❌ Keine EWGs validiert - kompletter Fallback zu Semantic")
                    semantic_result = self._handle_semantic(query, filter_law)
                    semantic_result['pipeline_used'] = 'keyword_metadata_failed_semantic_fallback'
                    return semantic_result
        
        # Alles gut gefunden - normale Verarbeitung
        context = "\n\n".join([doc.page_content for doc in docs])
        chat_history = self._get_chat_history_text()
        
        # ERWÄGUNGSGRÜNDE
        if 'erwägungsgrund' in analysis.extracted_references:
            ewg_nums = ', '.join(map(str, analysis.extracted_references['erwägungsgrund']))
            prompt = f"""{chat_history}
    
Du bist Rechtsexperte. Der Nutzer möchte den Erwägungsgrund {ewg_nums} sehen.

WICHTIG - STRUKTUR BEFOLGEN:

1. ZUERST: Gib den VOLLSTÄNDIGEN Originaltext in Anführungszeichen wieder:
   "Erwägungsgrund {ewg_nums}
   
   [KOMPLETTER ORIGINALTEXT]"
   
   (Quelle: [Gesetz] EWG {ewg_nums})

2. DANN: Erkläre in 3-5 Sätzen:
   - Was ist der Hintergrund?
   - Warum wurde dieser Erwägungsgrund aufgenommen?
   - Nutze ein praktisches Beispiel

3. Stelle eine weiterführende Frage

4. Liste Quellen auf

GEFUNDENER KONTEXT:
{context}

REGEL:
- Wenn EWG {ewg_nums} im Kontext → Gib ihn VOLLSTÄNDIG wieder
- Wenn nicht → Sage: "Ich finde den Erwägungsgrund {ewg_nums} nicht."

FRAGE: {query}

ANTWORT:"""

            response = self.llm.invoke(prompt)
            
        # ANHÄNGE
        elif 'anhang' in analysis.extracted_references:
            anhang_nums = ', '.join(map(str, analysis.extracted_references['anhang']))
            prompt = f"""{chat_history}
    
Du bist Rechtsexperte. Der Nutzer möchte Anhang {anhang_nums} sehen.

WICHTIG - STRUKTUR BEFOLGEN:

1. ZUERST: Gib den VOLLSTÄNDIGEN Originaltext in Anführungszeichen wieder:
   "Anhang {anhang_nums} der KI-Verordnung
   
   [KOMPLETTER ORIGINALTEXT MIT ALLEN PUNKTEN]"
   
   (Quelle: KI-VO Anhang {anhang_nums})

2. DANN: Erkläre in 3-5 Sätzen:
   - Wofür ist dieser Anhang gedacht?
   - Welche praktische Bedeutung hat er?
   - Für wen ist er relevant?
   - Nutze ein konkretes Beispiel

3. Stelle eine weiterführende Frage

4. Liste Quellen auf

GEFUNDENER KONTEXT:
{context}

REGEL:
- VOLLSTÄNDIGER Originaltext mit allen Unterpunkten
- Keine Kürzung, keine Zusammenfassung beim Originaltext
- Wenn nicht gefunden → Sage: "Ich finde Anhang {anhang_nums} nicht."

FRAGE: {query}

ANTWORT:"""
            response = self.llm.invoke(prompt)
            
        # ARTIKEL
        elif 'artikel' in analysis.extracted_references:
            artikel_nums = ', '.join(map(str, analysis.extracted_references['artikel']))
            prompt = f"""{chat_history}
    
Du bist Rechtsexperte. Der Nutzer möchte Artikel {artikel_nums} sehen.

WICHTIG - STRUKTUR BEFOLGEN:

1. ZUERST: Gib den VOLLSTÄNDIGEN Originaltext in Anführungszeichen wieder:
   "Artikel {artikel_nums}
   
   [KOMPLETTER ORIGINALTEXT MIT ALLEN ABSÄTZEN]"
   
   (Quelle: [Gesetz] Art. {artikel_nums})

2. DANN: Erkläre in 3-5 Sätzen:
   - Was regelt dieser Artikel?
   - Für wen gilt er?
   - Was sind die praktischen Konsequenzen?
   - Nutze ein konkretes Beispiel

3. Stelle eine weiterführende Frage

4. Liste Quellen auf

BEISPIEL-FORMAT:

"Artikel 10 - Datenqualität und Datenverwaltung

(1) Hochrisiko-KI-Systeme, die Techniken für Modelle einsetzen, die mit Daten trainiert werden, werden auf der Grundlage von Trainings-, Validierungs- und Testdatensätzen entwickelt, die den Qualitätskriterien der Absätze 2 bis 5 genügen.

(2) [...]"

(KI-VO Art. 10)

Dieser Artikel legt fest, dass Hochrisiko-KI-Systeme mit qualitativ hochwertigen Daten trainiert werden müssen. Praktisch bedeutet das: Ein KI-System zur Kreditwürdigkeitsprüfung muss mit repräsentativen Daten trainiert werden.

Möchten Sie wissen, welche konkreten Qualitätskriterien gelten?

---
§ Verwendete Quellen:
- KI-VO Art. 10

GEFUNDENER KONTEXT:
{context}

REGEL:
- VOLLSTÄNDIGER Originaltext mit allen Absätzen
- Keine Kürzung beim Originaltext
- Wenn nicht gefunden → Sage: "Ich finde Artikel {artikel_nums} nicht."

FRAGE: {query}

ANTWORT:"""
            response = self.llm.invoke(prompt)
            
        else:
            # Fallback
            prompt = f"""{chat_history}
    
Du bist Rechtsexperte. Der Nutzer fragt nach einem Rechtstext.

1. Gib den relevanten Originaltext vollständig in Anführungszeichen wieder
2. Erkläre die Bedeutung
3. Stelle eine Frage
4. Liste Quellen auf

GEFUNDENER KONTEXT:
{context}

FRAGE: {query}

ANTWORT:"""
        
            response = self.llm.invoke(prompt)
            
        self._save_to_memory(query, response.content)
        
        logger.info("✅ Keyword-Metadata Pipeline erfolgreich")
        
        return {
            'result': response.content,
            'source_documents': docs,
            'pipeline_used': 'keyword_metadata'
        }
    
    def _handle_semantic(self, query: str, filter_law: Optional[str]) -> Dict[str, Any]:
        """Semantic Search Pipeline - nutzt den QA Chain"""
        logger.info("🔵 Semantic Pipeline gestartet")
        
        try:
            result = self.qa_chain({"question": query})
            
            docs = result.get('source_documents', [])
            
            if filter_law and docs:
                docs = [d for d in docs if d.metadata.get('source_law') == filter_law]
                logger.info(f"   Filter '{filter_law}' angewendet: {len(docs)} Docs")
            
            logger.info(f"✅ Semantic Pipeline: {len(docs)} Quellen verwendet")
            
            return {
                'result': result.get('answer', ''),
                'source_documents': docs,
                'pipeline_used': 'semantic'
            }
        except Exception as e:
            logger.error(f"❌ Semantic Pipeline Fehler: {str(e)}")
            return {
                'result': f"Entschuldigung, bei der Verarbeitung ist ein Fehler aufgetreten: {str(e)}",
                'source_documents': [],
                'pipeline_used': 'semantic_error'
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
        print("🔧 VOLLSTÄNDIGES SETUP MIT TRIPLE PIPELINE + FIXES")
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
            print("   🟢 Pipeline 2: Keyword/Metadata (✅ VERBESSERT)")
            print("   🟡 Pipeline 3: Definitions")
            print("   📊 Logging: AKTIV")
            
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
                
                # ✅ FIX: Extrahiere EWG-Nummer und speichere in Metadata
                ewg_match = re.search(r'Erwägungsgrund\s+(\d+)', chunk.page_content, re.IGNORECASE)
                if not ewg_match:
                    ewg_match = re.search(r'#\s*\((\d+)\)', chunk.page_content)
                
                if ewg_match:
                    chunk.metadata['ewg_nummer'] = ewg_match.group(1)
                    chunk.metadata['artikel'] = f"EWG {ewg_match.group(1)}"
            
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
                
                # ✅ FIX: Extrahiere EWG-Nummer und speichere in Metadata
                ewg_match = re.search(r'Erwägungsgrund\s+(\d+)', chunk.page_content, re.IGNORECASE)
                if not ewg_match:
                    ewg_match = re.search(r'#\s*\((\d+)\)', chunk.page_content)
                if not ewg_match:
                    ewg_match = re.search(r'^\((\d+)\)', chunk.page_content, re.MULTILINE)
                
                if ewg_match:
                    chunk.metadata['ewg_nummer'] = ewg_match.group(1)
                    chunk.metadata['artikel'] = f"EWG {ewg_match.group(1)}"
            
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
            model="mistral-small-latest",
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
        
        semantic_template = """Du bist ein Compliance-Assistent für die EU KI-Verordnung und DSGVO.

Beantworte die Frage natürlich und verständlich. Nutze die bereitgestellten Dokumente und beziehe dich bei Bedarf auf vorherige Fragen aus der Konversation.

ANTWORTWEISE:
Wenn möglich, beginne mit einem relevanten Originalzitat in Anführungszeichen mit Quellenangabe. Erkläre dann in eigenen Worten was das bedeutet. Nutze praktische Beispiele zur Veranschaulichung. Schließe mit einer passenden Folgefrage ab.

Am Ende liste die verwendeten Quellen auf.

WICHTIG:
- Bleibe nah am Originaltext der Dokumente
- Erkläre verständlich ohne zu vereinfachen
- Wenn die Information nicht in den Dokumenten steht: "Diese Information finde ich in den verfügbaren Dokumenten nicht."
- Schreibe natürlich und gesprächsorientiert
- Bei Bezug auf frühere Fragen: "Wie Sie zuvor fragten..." oder "Ergänzend zu Ihrer vorherigen Frage..."

BEISPIEL EINER GUTEN ANTWORT:

"Ein Hochrisiko-KI-System muss einer Konformitätsbewertung unterzogen werden, bevor es in Verkehr gebracht wird" (KI-VO Art. 43 Abs. 1). 

Das bedeutet konkret: Bevor ein Unternehmen ein KI-System als Hochrisiko-Produkt auf den Markt bringt, muss nachgewiesen werden, dass alle Anforderungen der KI-Verordnung erfüllt sind. Ein Beispiel wäre ein KI-System zur automatischen Bewertung von Kreditanträgen - hier müsste die Bank vor dem Einsatz belegen, dass das System transparent, sicher und diskriminierungsfrei arbeitet.

Möchten Sie wissen, wie dieser Konformitätsbewertungsprozess konkret abläuft?

---
§ Verwendete Quellen:
- KI-VO Art. 43 Abs. 1
- KI-VO Anhang VII

VERFÜGBARE DOKUMENTE:
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
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=conversation_memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": QA_PROMPT},
            verbose=False
        )
        
        # Router
        advanced_router = AdvancedQueryRouter(DEFINED_TERMS_KI_VO, DEFINED_TERMS_DSGVO)
        
        # Keyword Retriever - ✅ MIT FIXES
        keyword_retriever = KeywordMetadataRetriever(self.vectorstore, self.all_chunks)
        
        # Definitions Retriever
        definitions_retriever = DefinitionsRetriever(
            self.vectorstore,
            self.qdrant_client,
            self.COLLECTION_NAME,
            self.all_chunks,
            self.embeddings
        )
        
        # Triple Pipeline Manager - ✅ MIT FIXES
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
        
        print("   ✅ Triple Pipeline bereit (mit Fixes 1, 2, 3)")
    
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
