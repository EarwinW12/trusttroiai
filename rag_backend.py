"""
RAG Backend - VERSION 3.0 MIT QUERY PREPROCESSING
TrustTroiAI - KI-VO & DSGVO Compliance Assistant

NEUE FEATURES v3.0:
- ✅ Query Preprocessing Layer (Normalisierung + Intent Detection)
- ✅ Enhanced Pattern Matching für alle 3 Pipelines
- ✅ Confidence Scoring für Pipeline-Auswahl
- ✅ Bessere Fuzzy-Erkennung
- ✅ Harmonische Integration mit bestehenden Pipelines

ÄNDERUNGEN von v2.0:
- NEU: QueryPreprocessor Klasse
- NEU: Enhanced Pattern in AdvancedQueryRouter
- NEU: Confidence-basiertes Routing
- VERBESSERT: Alle 3 Pipelines profitieren vom Preprocessing
"""

import warnings
warnings.filterwarnings("ignore")

from typing import List, Dict, Any, Optional, Tuple
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

# ✅ Logging Setup
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
    normalized_query: str = ""  # ✅ NEU
    original_query: str = ""     # ✅ NEU


# ==============================================================================
# QUERY PREPROCESSOR - ✅ NEU IN V3.0
# ==============================================================================

class QueryPreprocessor:
    """
    Preprocessing-Layer für Queries
    - Normalisierung (Füllwörter entfernen)
    - Intent Detection (was will der User?)
    - Query Enrichment (Synonyme, Varianten)
    """
    
    def __init__(self):
        # Füllwörter die Pattern-Matching stören
        self.filler_patterns = [
            r'\b(zeig|zeige|gib|nenn|nenne|finde|such|suche)\s+(mir|mal)?\s*',
            r'\b(möchte|will|würde)\s+(gerne)?\s*',
            r'\b(bitte)\s*',
            r'\b(kannst du|können sie)\s*',
        ]
        
        # Präpositionen die entfernt werden können
        self.preposition_patterns = [
            r'\s+(der|die|das|den|dem|des)\s+(?=dsgvo|ki-verordnung|ki-vo)',
            r'\s+(in|aus|von|zu|bei|mit|für|über)\s+(?=dsgvo|ki-verordnung|ki-vo)',
        ]
        
        # Varianten für "laut/gemäß" können bleiben, aber markieren
        self.indicator_words = [
            'laut', 'gemäß', 'nach', 'entsprechend', 'aufgrund'
        ]
    
    def preprocess(self, query: str) -> Dict[str, Any]:
        """
        Hauptmethode: Preprocesse Query
        
        Returns:
            {
                'original': Original-Query,
                'normalized': Normalisierte Query,
                'cleaned': Gereinigte Query (ohne Füllwörter),
                'indicators': Gefundene Indicator-Words,
                'has_law_reference': DSGVO oder KI-VO erwähnt?
            }
        """
        original = query
        normalized = query.lower()
        
        # Sammle Indicators
        found_indicators = [word for word in self.indicator_words if word in normalized]
        
        # Entferne Füllwörter
        cleaned = normalized
        for pattern in self.filler_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Entferne störende Präpositionen VOR Gesetzes-Namen
        for pattern in self.preposition_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
        
        # Normalize Whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Detect Law Reference
        has_dsgvo = bool(re.search(r'\bdsgvo\b', cleaned))
        has_ki_vo = bool(re.search(r'\b(ki-verordnung|ki-vo|kivo)\b', cleaned))
        
        result = {
            'original': original,
            'normalized': normalized,
            'cleaned': cleaned,
            'indicators': found_indicators,
            'has_law_reference': has_dsgvo or has_ki_vo,
            'law': 'DSGVO' if has_dsgvo else ('KI-Verordnung' if has_ki_vo else None)
        }
        
        logger.debug(f"🔄 Preprocessing: '{original}' → '{cleaned}'")
        logger.debug(f"   Indicators: {found_indicators}, Law: {result['law']}")
        
        return result


# ==============================================================================
# QUERY ROUTER - ✅ ENHANCED IN V3.0
# ==============================================================================

class AdvancedQueryRouter:
    def __init__(self, defined_terms_ki_vo: List[str], defined_terms_dsgvo: List[str]):
        self.defined_terms_ki_vo = [t.lower() for t in defined_terms_ki_vo]
        self.defined_terms_dsgvo = [t.lower() for t in defined_terms_dsgvo]
        
        # ✅ NEU: Preprocessor integriert
        self.preprocessor = QueryPreprocessor()
        
        self.definition_keywords = [
            'definiert', 'definition', 'begriff', 'bedeutung', 'bedeutet',
            'meint', 'versteht man unter', 'bezeichnet', 'ist gemeint',
            'was ist', 'was sind', 'erklärung', 'erkläre',
        ]
        
        # ✅ ERWEITERT: Mehr Pattern-Varianten
        self.keyword_patterns = {
            'artikel': [
                r'artikel\s+(\d+)',
                r'art\.?\s*(\d+)',
                r'\bart\s+(\d+)',           # "art 5"
                r'a\.\s*(\d+)',              # "a. 5"
            ],
            'kapitel': [
                r'kapitel\s+([ivxIVX]+)',
                r'kapitel\s+(\d+)',
                r'kap\.?\s*(\d+)',
            ],
            'anhang': [
                r'anhang\s+([ivxIVX]+)',
                r'anhang\s+(\d+)',
                r'anh\.?\s*([ivxIVX]+)',
            ],
            'erwägungsgrund': [
                r'erwägungsgrund\s+(\d+)',
                r'erwägungsgründe?\s+(\d+)',
                r'ewg\.?\s*(\d+)',
                r'ewg\s+(\d+)',
                r'erw\.?\s*(\d+)',
                r'\bewg\s+(\d+)',            # "EWG 15" (word boundary)
                r'recital\s+(\d+)',
                # ✅ NEU: Auch ohne direkten Zusammenhang
                r'\b(\d+)\s+ewg\b',          # "15 EWG"
                r'nummer\s+(\d+)',           # "Nummer 15" (im Kontext)
            ],
        }
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        ✅ ENHANCED: Nutzt jetzt Preprocessing
        """
        # ✅ SCHRITT 1: Preprocessing
        preprocessed = self.preprocessor.preprocess(query)
        cleaned_query = preprocessed['cleaned']
        original_query = preprocessed['original']
        
        logger.debug(f"📊 Analyzing: '{cleaned_query}'")
        
        # ✅ SCHRITT 2: Definition-Query?
        is_definition_query = any(kw in cleaned_query for kw in self.definition_keywords)
        
        if is_definition_query:
            return self._analyze_definition_query(cleaned_query, preprocessed, original_query)
        
        # ✅ SCHRITT 3: Keyword/Metadata? (Artikel, EWG, Anhang)
        keyword_result = self._analyze_keyword_query(cleaned_query, preprocessed, original_query)
        if keyword_result:
            return keyword_result
        
        # ✅ SCHRITT 4: Default → Semantic
        return QueryAnalysis(
            pipeline_type=PipelineType.SEMANTIC,
            confidence=0.8,
            detected_patterns=['semantic'],
            extracted_references={},
            normalized_query=cleaned_query,
            original_query=original_query
        )
    
    def _analyze_definition_query(self, cleaned_query: str, preprocessed: Dict, original_query: str) -> QueryAnalysis:
        """Analysiere Definition-Queries"""
        extracted_term = self._extract_term(cleaned_query)
        
        if not extracted_term:
            # Fallback zu Semantic
            return QueryAnalysis(
                pipeline_type=PipelineType.SEMANTIC,
                confidence=0.6,
                detected_patterns=['definition_no_term'],
                extracted_references={},
                normalized_query=cleaned_query,
                original_query=original_query
            )
        
        detected_law = preprocessed.get('law')
        
        # Prüfe ob Term in Listen
        if self._term_in_list(extracted_term, self.defined_terms_ki_vo):
            return QueryAnalysis(
                pipeline_type=PipelineType.DEFINITIONS_KI_VO,
                confidence=0.95,
                detected_patterns=[f"def_{extracted_term}"],
                extracted_references={'term': extracted_term, 'law': 'KI-Verordnung'},
                normalized_query=cleaned_query,
                original_query=original_query
            )
        
        elif self._term_in_list(extracted_term, self.defined_terms_dsgvo):
            return QueryAnalysis(
                pipeline_type=PipelineType.DEFINITIONS_DSGVO,
                confidence=0.95,
                detected_patterns=[f"def_{extracted_term}"],
                extracted_references={'term': extracted_term, 'law': 'DSGVO'},
                normalized_query=cleaned_query,
                original_query=original_query
            )
        
        # Law im Query erwähnt → nutze diese Law
        elif detected_law:
            pipeline = PipelineType.DEFINITIONS_KI_VO if detected_law == 'KI-Verordnung' else PipelineType.DEFINITIONS_DSGVO
            return QueryAnalysis(
                pipeline_type=pipeline,
                confidence=0.8,
                detected_patterns=[f"def_{extracted_term}"],
                extracted_references={'term': extracted_term, 'law': detected_law},
                normalized_query=cleaned_query,
                original_query=original_query
            )
        
        # Generic Definition
        else:
            return QueryAnalysis(
                pipeline_type=PipelineType.DEFINITIONS_GENERIC,
                confidence=0.7,
                detected_patterns=[f"def_{extracted_term}"],
                extracted_references={'term': extracted_term, 'law': None},
                normalized_query=cleaned_query,
                original_query=original_query
            )
    
    def _analyze_keyword_query(self, cleaned_query: str, preprocessed: Dict, original_query: str) -> Optional[QueryAnalysis]:
        """
        ✅ ENHANCED: Analysiere Keyword-Queries mit besseren Patterns
        """
        detected_patterns = []
        extracted_references = {}
        
        # Durchsuche alle Pattern-Typen
        for pattern_type, patterns in self.keyword_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, cleaned_query, re.IGNORECASE)
                for match in matches:
                    reference = match.group(1)
                    
                    # Normalisiere Römische Zahlen
                    if pattern_type in ['anhang', 'kapitel']:
                        reference = self._normalize_number(reference)
                    
                    detected_patterns.append(f"{pattern_type}_{reference}")
                    if pattern_type not in extracted_references:
                        extracted_references[pattern_type] = []
                    if reference not in extracted_references[pattern_type]:
                        extracted_references[pattern_type].append(reference)
        
        # Wenn Patterns gefunden → Keyword Pipeline
        if detected_patterns:
            # ✅ Confidence basierend auf Klarheit
            confidence = min(0.95, len(detected_patterns) * 0.25 + 0.7)
            
            logger.debug(f"✅ Keyword-Patterns gefunden: {detected_patterns}")
            
            return QueryAnalysis(
                pipeline_type=PipelineType.KEYWORD_METADATA,
                confidence=confidence,
                detected_patterns=detected_patterns,
                extracted_references=extracted_references,
                normalized_query=cleaned_query,
                original_query=original_query
            )
        
        return None
    
    def _extract_term(self, query: str) -> Optional[str]:
        """Extrahiere Term aus Definition-Query"""
        query_lower = query.lower()
        query_clean = re.sub(r'\b(?:laut|gemäß|nach|der|des)\s+(?:ki-verordnung|ki-vo|dsgvo|art\.?\s*\d+)\b', '', query_lower)
        query_clean = re.sub(r'\b(?:ki-verordnung|ki-vo|dsgvo)\b', '', query_clean)
        
        # Pattern 1: "wie wird X definiert"
        match = re.search(r'wie\s+(?:wird|werden)\s+(.+?)\s+(?:definiert|bezeichnet)', query_clean)
        if match:
            return self._clean_term(match.group(1))
        
        # Pattern 2: "was bedeutet X"
        match = re.search(r'was\s+(?:bedeutet|ist|sind)\s+(?:ein|eine|der|die|das)?\s*(.+?)(?:\?|$)', query_clean)
        if match:
            return self._clean_term(match.group(1))
        
        # Pattern 3: "definition von X"
        match = re.search(r'definition\s+(?:von|für|des|der)\s+(.+?)(?:\?|$)', query_clean)
        if match:
            return self._clean_term(match.group(1))
        
        return None
    
    def _clean_term(self, term: str) -> str:
        """Säubere extrahierten Term"""
        term = re.sub(r'[?.,!]', '', term)
        term = re.sub(r'^(?:ein|eine|der|die|das|den|dem|laut|gemäß|nach)\s+', '', term)
        term = re.sub(r'\s+(?:laut|gemäß|nach|der|des)$', '', term)
        return term.strip()
    
    def _term_in_list(self, term: str, term_list: List[str]) -> bool:
        """Prüfe ob Term in Liste (mit Fuzzy-Matching)"""
        term_clean = term.lower().strip()
        
        if term_clean in term_list:
            return True
        
        # Varianten
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
        
        # Fuzzy (Substring)
        if len(term_clean) >= 4:
            for defined_term in term_list:
                if term_clean in defined_term or (defined_term in term_clean and len(defined_term) >= 4):
                    return True
        
        return False
    
    def _normalize_number(self, num_str: str) -> str:
        """Konvertiere römische zu arabischen Zahlen"""
        roman_to_arabic = {
            'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5',
            'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'
        }
        return roman_to_arabic.get(num_str.strip().lower(), num_str)


# ==============================================================================
# KEYWORD RETRIEVER - FROM V2.0 (unverändert, funktioniert gut)
# ==============================================================================

class KeywordMetadataRetriever:
    def __init__(self, vectorstore, all_chunks: List[Document]):
        self.vectorstore = vectorstore
        self.all_chunks = all_chunks
        self.metadata_index = self._build_metadata_index()
        logger.info(f"📊 Metadata-Index erstellt: {self._get_index_stats()}")
    
    def _build_metadata_index(self) -> Dict[str, Dict[str, List[Document]]]:
        """Baue Index aus Metadata"""
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
            
            # Index für Erwägungsgründe (Multi-Strategie aus v2.0)
            if 'erwägung' in source_type:
                ewg_num = None
                
                # Strategie 1: Metadata
                if 'ewg_nummer' in metadata:
                    ewg_num = str(metadata['ewg_nummer'])
                
                # Strategie 2: Header
                elif 'Erwägungsgrund' in metadata:
                    header_value = str(metadata['Erwägungsgrund'])
                    match = re.search(r'(\d+)', header_value)
                    if match:
                        ewg_num = match.group(1)
                
                # Strategie 3: Content
                if not ewg_num:
                    first_lines = chunk.page_content[:300]
                    patterns = [
                        r'#\s*Erwägungsgrund\s+(\d+)',
                        r'#\s*\((\d+)\)',
                        r'^Erwägungsgrund\s+(\d+)',
                        r'^\((\d+)\)',
                        r'EWG\s+(\d+)',
                        r'Recital\s+(\d+)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, first_lines, re.MULTILINE | re.IGNORECASE)
                        if match:
                            ewg_num = match.group(1)
                            break
                
                if ewg_num:
                    if ewg_num not in index['erwägungsgrund']:
                        index['erwägungsgrund'][ewg_num] = []
                    index['erwägungsgrund'][ewg_num].append(chunk)
            
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
        """Statistik für Logging"""
        stats = []
        for key, sub_index in self.metadata_index.items():
            count = len(sub_index)
            if count > 0:
                stats.append(f"{key}={count}")
        return ", ".join(stats)
    
    def _normalize_number(self, num_str: str) -> str:
        """Römisch → Arabisch"""
        roman_to_arabic = {
            'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5',
            'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'
        }
        return roman_to_arabic.get(num_str.strip().lower(), num_str)
    
    def retrieve_by_metadata(self, extracted_references: Dict[str, Any], k: int = 5) -> List[Document]:
        """Retrieve mit Validierung (aus v2.0)"""
        logger.info(f"🔍 Keyword-Suche: {extracted_references}")
        results = []
        
        # Artikel
        if 'artikel' in extracted_references:
            for artikel_num in extracted_references['artikel']:
                if str(artikel_num) in self.metadata_index['artikel']:
                    results.extend(self.metadata_index['artikel'][str(artikel_num)])
        
        # Erwägungsgründe mit Validierung
        if 'erwägungsgrund' in extracted_references:
            for ewg_num in extracted_references['erwägungsgrund']:
                if str(ewg_num) in self.metadata_index['erwägungsgrund']:
                    found_docs = self.metadata_index['erwägungsgrund'][str(ewg_num)]
                    
                    validated_docs = []
                    for doc in found_docs:
                        if self._validate_ewg_in_content(doc, ewg_num):
                            validated_docs.append(doc)
                    
                    results.extend(validated_docs)
        
        # Anhänge
        if 'anhang' in extracted_references:
            for anhang_num in extracted_references['anhang']:
                normalized = self._normalize_number(anhang_num)
                if normalized in self.metadata_index['anhang']:
                    results.extend(self.metadata_index['anhang'][normalized])
        
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
        
        logger.info(f"🎯 Keyword-Retrieval: {len(unique_results)} Dokumente")
        return unique_results
    
    def _validate_ewg_in_content(self, doc: Document, ewg_num: str) -> bool:
        """Validiere EWG im Content"""
        content = doc.page_content.lower()
        
        patterns = [
            rf'erwägungsgrund\s+{ewg_num}\b',
            rf'\({ewg_num}\)',
            rf'ewg\s+{ewg_num}\b',
            rf'recital\s+{ewg_num}\b',
            rf'#\s*erwägungsgrund\s+{ewg_num}',
            rf'#\s*\({ewg_num}\)',
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)


# ==============================================================================
# DEFINITIONS RETRIEVER - FROM V2.0 (unverändert)
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
        
        return unique_docs[:k] if unique_docs else []
    
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
# TRIPLE PIPELINE MANAGER - ✅ ENHANCED IN V3.0
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
        
        # Check if context needed
        needs_context = self._needs_conversation_context(query)
        
        if needs_context:
            logger.info("🔵 Pipeline: SEMANTIC (Kontext benötigt)")
            return self._handle_semantic(query, filter_law)
        
        # ✅ Routing mit Enhanced Router (inkl. Preprocessing)
        analysis = self.router.analyze_query(query)
        
        logger.info(f"🎯 Query-Analyse: {analysis.pipeline_type.value} (Confidence: {analysis.confidence:.2f})")
        logger.info(f"   Normalized: '{analysis.normalized_query}'")
        logger.info(f"   Referenzen: {analysis.extracted_references}")
        
        # Route zu Pipeline
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
        """Prüfe ob Kontext aus Historie benötigt wird"""
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
        """Handle Definition-Pipeline"""
        term = analysis.extracted_references.get('term')
        law = analysis.extracted_references.get('law')
        
        logger.info(f"🔍 Definitions-Suche: Term='{term}', Law='{law}'")
        
        docs = self.definitions_retriever.retrieve_definition(term, law, k=2)
        
        if not docs:
            logger.warning(f"⚠️ Keine Definition für '{term}' - Fallback zu Semantic")
            return self._handle_semantic(query, law)
        
        logger.info(f"✅ {len(docs)} Definitions-Chunks gefunden")
        
        context = "\n\n".join([
            f"📖 DEFINITION aus {doc.metadata.get('source_law')} {doc.metadata.get('artikel')}:\n{doc.page_content}"
            for doc in docs
        ])
        
        chat_history = self._get_chat_history_text()
        
        prompt = f"""Du bist ein erfahrener Rechtsexperte für EU-Regulierungen. Beantworte die Frage natürlich und verständlich.

ANTWORTSTRUKTUR:

1. Beginne mit dem vollständigen Originaltext in Anführungszeichen mit Quellenangabe in Klammern.

2. Erkläre dann in 2-4 Sätzen die praktische Bedeutung. Nutze wenn möglich ein konkretes Beispiel.

3. Schließe mit einer weiterführenden Frage ab.

4. Am Ende liste die Quellen auf.

{chat_history}

VERFÜGBARE DEFINITIONEN:
{context}

FRAGE: {query}

ANTWORT:"""
        
        response = self.llm.invoke(prompt)
        self._save_to_memory(query, response.content)
        
        return {
            'result': response.content,
            'source_documents': docs,
            'pipeline_used': f'definitions_{analysis.pipeline_type.value}'
        }
    
    def _handle_keyword_metadata(self, query: str, analysis: QueryAnalysis, filter_law: Optional[str]) -> Dict[str, Any]:
        """Handle Keyword/Metadata-Pipeline mit Fallbacks"""
        
        docs = self.keyword_retriever.retrieve_by_metadata(
            analysis.extracted_references,
            k=5
        )
        
        if filter_law and docs:
            docs = [d for d in docs if d.metadata.get('source_law') == filter_law]
        
        # Fallback wenn nichts gefunden
        if not docs:
            logger.warning("❌ Keyword fand NICHTS - Fallback zu Semantic")
            
            semantic_result = self._handle_semantic(query, filter_law)
            semantic_result['result'] = (
                f"ℹ️ *Ich konnte die angeforderten Rechtstexte nicht direkt finden. "
                f"Hier ist eine semantische Suche zum Thema:*\n\n" +
                semantic_result['result']
            )
            semantic_result['pipeline_used'] = 'keyword_fallback_to_semantic'
            
            return semantic_result
        
        # Validierung für EWGs
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
                
                if found_ewgs:
                    # Hybrid: Keyword + Semantic
                    semantic_result = self._handle_semantic(query, filter_law)
                    
                    combined_prompt = f"""Du bist Rechtsexperte. 

GEFUNDENE ERWÄGUNGSGRÜNDE:
{chr(10).join([doc.page_content for doc in docs])}

ZUSÄTZLICHE INFORMATIONEN:
{chr(10).join([doc.page_content for doc in semantic_result.get('source_documents', [])[:2]])}

Der Nutzer fragte nach: {query}

Wir haben EWG {', '.join(found_ewgs)} gefunden, aber EWG {', '.join(missing_ewgs)} fehlt.

Gib ZUERST die gefundenen EWGs vollständig wieder, erwähne dann transparent welche fehlen.

ANTWORT:"""
                    
                    response = self.llm.invoke(combined_prompt)
                    self._save_to_memory(query, response.content)
                    
                    return {
                        'result': response.content,
                        'source_documents': docs + semantic_result.get('source_documents', [])[:2],
                        'pipeline_used': 'keyword_partial_with_semantic'
                    }
                
                else:
                    # Kompletter Fallback
                    return self._handle_semantic(query, filter_law)
        
        # Normal processing
        context = "\n\n".join([doc.page_content for doc in docs])
        chat_history = self._get_chat_history_text()
        
        # Generate appropriate prompt based on type
        if 'erwägungsgrund' in analysis.extracted_references:
            ewg_nums = ', '.join(map(str, analysis.extracted_references['erwägungsgrund']))
            prompt_type = "EWG"
        elif 'artikel' in analysis.extracted_references:
            ewg_nums = ', '.join(map(str, analysis.extracted_references['artikel']))
            prompt_type = "ARTIKEL"
        elif 'anhang' in analysis.extracted_references:
            ewg_nums = ', '.join(map(str, analysis.extracted_references['anhang']))
            prompt_type = "ANHANG"
        else:
            prompt_type = "GENERIC"
        
        prompt = f"""{chat_history}

Du bist Rechtsexperte. Der Nutzer fragt nach {prompt_type} {ewg_nums if prompt_type != "GENERIC" else ""}.

STRUKTUR:

1. Gib den VOLLSTÄNDIGEN Originaltext in Anführungszeichen wieder mit Quellenangabe
2. Erkläre die Bedeutung in 3-5 Sätzen mit praktischem Beispiel
3. Stelle eine weiterführende Frage
4. Liste Quellen auf

KONTEXT:
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
        """Handle Semantic-Pipeline"""
        logger.info("🔵 Semantic Pipeline gestartet")
        
        try:
            result = self.qa_chain({"question": query})
            
            docs = result.get('source_documents', [])
            
            if filter_law and docs:
                docs = [d for d in docs if d.metadata.get('source_law') == filter_law]
            
            logger.info(f"✅ Semantic Pipeline: {len(docs)} Quellen")
            
            return {
                'result': result.get('answer', ''),
                'source_documents': docs,
                'pipeline_used': 'semantic'
            }
        except Exception as e:
            logger.error(f"❌ Semantic Pipeline Fehler: {str(e)}")
            return {
                'result': f"Entschuldigung, es ist ein Fehler aufgetreten: {str(e)}",
                'source_documents': [],
                'pipeline_used': 'semantic_error'
            }
    
    def _get_chat_history_text(self) -> str:
        """Get formatted chat history"""
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
        """Save to conversation memory"""
        self.qa_chain.memory.chat_memory.add_message(HumanMessage(content=query))
        self.qa_chain.memory.chat_memory.add_message(AIMessage(content=response))
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.qa_chain.memory.clear()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        messages = self.qa_chain.memory.chat_memory.messages
        return {
            'total_messages': len(messages),
            'capacity': self.qa_chain.memory.k
        }


# ==============================================================================
# RAG BACKEND - ✅ UPDATED FOR V3.0
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
        print("🔧 SETUP VERSION 3.0 - MIT QUERY PREPROCESSING")
        print("="*70)
        
        try:
            # 1. Dokumente laden
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
            print("\n🔧 ERSTELLE ENHANCED TRIPLE PIPELINE...")
            self._create_triple_pipeline()
            
            self.initialized = True
            print("\n✅ SETUP ABGESCHLOSSEN (v3.0)!")
            print("   🔄 Query Preprocessing: AKTIV")
            print("   🔵 Semantic Pipeline: AKTIV")
            print("   🟢 Keyword Pipeline: ENHANCED")
            print("   🟡 Definition Pipeline: AKTIV")
            
        except Exception as e:
            print(f"\n❌ FEHLER: {e}")
            raise
    
    def _load_all_documents(self, paths: Dict[str, str]) -> List[Document]:
        """Load all documents - aus v2.0"""
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
        """Initialize AI models"""
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
        """Create vector database"""
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
        """Create enhanced triple pipeline with preprocessing"""
        
        # Extract defined terms
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
        
        # ✅ Enhanced Router with Preprocessing
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
        
        print("   ✅ Enhanced Triple Pipeline bereit (v3.0)")
    
    def query(
        self,
        question: str,
        filter_law: Optional[str] = None,
        show_sources: bool = False
    ) -> Dict[str, Any]:
        """Query the system"""
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
        """Clear conversation memory"""
        if self.triple_pipeline:
            self.triple_pipeline.clear_memory()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if self.triple_pipeline:
            return self.triple_pipeline.get_memory_stats()
        return {}
    
    def get_vectordb_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
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
