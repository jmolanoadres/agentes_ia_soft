"""
Memoria vectorial para el Requirements Agent v2.0.
Usa ChromaDB con fallback a almacenamiento en memoria.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from .requirements_config import get_config

logger = logging.getLogger(__name__)

# ── Intentar importar ChromaDB ──────────────────
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb no está instalado. Usando almacenamiento en memoria como fallback.")


class InMemoryVectorStore:
    """Fallback cuando ChromaDB no está disponible."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._documents: list[str] = []
        self._metadatas: list[dict[str, Any]] = []
        self._ids: list[str] = []

    def add(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        for doc, meta, doc_id in zip(documents, metadatas, ids):
            self._store[doc_id] = {
                "document": doc,
                "metadata": meta,
            }
            self._documents.append(doc)
            self._metadatas.append(meta)
            self._ids.append(doc_id)

    def query(
        self,
        query_texts: list[str],
        n_results: int = 5,
    ) -> dict[str, Any]:
        """Búsqueda simple por coincidencia de palabras clave."""
        results_docs = []
        results_meta = []
        results_ids = []
        results_distances = []

        for query in query_texts:
            query_lower = query.lower()
            query_words = set(query_lower.split())
            scored = []

            for doc_id, data in self._store.items():
                doc_lower = data["document"].lower()
                doc_words = set(doc_lower.split())
                # Jaccard similarity
                intersection = query_words & doc_words
                union = query_words | doc_words
                score = len(intersection) / len(union) if union else 0.0
                scored.append((doc_id, data, score))

            scored.sort(key=lambda x: x[2], reverse=True)
            top = scored[:n_results]

            results_docs.append([item[1]["document"] for item in top])
            results_meta.append([item[1]["metadata"] for item in top])
            results_ids.append([item[0] for item in top])
            results_distances.append([1.0 - item[2] for item in top])

        return {
            "documents": results_docs,
            "metadatas": results_meta,
            "ids": results_ids,
            "distances": results_distances,
        }

    def count(self) -> int:
        return len(self._store)

    def delete(self, ids: list[str] | None = None) -> None:
        if ids:
            for doc_id in ids:
                self._store.pop(doc_id, None)
        else:
            self._store.clear()
            self._documents.clear()
            self._metadatas.clear()
            self._ids.clear()


class RequirementsMemory:
    """
    Memoria vectorial para requisitos.

    Funcionalidades:
    - Almacenar requisitos como embeddings
    - Buscar requisitos similares
    - Detectar duplicados
    - Obtener contexto histórico
    """

    def __init__(
        self,
        collection_name: str = "requirements",
        persist_directory: str | None = None,
    ):
        config = get_config()
        self._collection_name = collection_name
        self._persist_dir = persist_directory or config.vector_db_path
        self._similarity_threshold = config.similarity_threshold
        self._collection: Any = self._init_collection()
        logger.info(
            f"RequirementsMemory inicializado "
            f"[backend={'chromadb' if CHROMADB_AVAILABLE else 'in-memory'}]"
        )

    def _init_collection(self) -> Any:
        """Inicializar colección de vectores."""
        if CHROMADB_AVAILABLE:
            try:
                client = chromadb.Client(
                    ChromaSettings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory=self._persist_dir,
                        anonymized_telemetry=False,
                    )
                )
                collection = client.get_or_create_collection(
                    name=self._collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(f"ChromaDB collection '{self._collection_name}' lista")
                return collection
            except Exception as e:
                logger.warning(f"Error inicializando ChromaDB: {e}. Usando fallback.")
                return InMemoryVectorStore()
        else:
            return InMemoryVectorStore()

    # ── Operaciones principales ──────────────────

    def store_requirement(self, requirement: Any) -> str:
        """
        Almacenar un requisito en la memoria vectorial.

        Args:
            requirement: Objeto Requirement con to_dict().

        Returns:
            ID del documento almacenado.
        """
        req_dict = requirement.to_dict()
        doc_text = self._requirement_to_text(req_dict)
        doc_id = str(req_dict.get("id", str(uuid.uuid4())))

        metadata = {
            "req_id": doc_id,
            "title": req_dict.get("title", ""),
            "req_type": req_dict.get("req_type", req_dict.get("type", "functional")),
            "priority": req_dict.get("priority", "should"),
            "status": req_dict.get("status", "draft"),
            "created_at": req_dict.get("created_at", datetime.now().isoformat()),
            "completeness_score": req_dict.get("completeness_score", 0.0),
        }

        self._collection.add(
            documents=[doc_text],
            metadatas=[metadata],
            ids=[doc_id],
        )

        logger.debug(f"Requisito almacenado en memoria: {doc_id}")
        return doc_id

    def search_similar(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Buscar requisitos similares a una consulta.

        Args:
            query: Texto de búsqueda.
            top_k: Número máximo de resultados.

        Returns:
            Lista de resultados con document, metadata y distance.
        """
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        output = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

            for doc, meta, dist in zip(docs, metas, dists):
                output.append(
                    {
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": 1.0 - dist,
                    }
                )

        return output

    def detect_duplicates(
        self,
        requirement: Any,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Detectar posibles duplicados de un requisito.

        Returns:
            Lista de requisitos similares que superan el umbral.
        """
        threshold = threshold or self._similarity_threshold
        req_dict = requirement.to_dict()
        query = self._requirement_to_text(req_dict)
        results = self.search_similar(query, top_k=10)

        duplicates = []
        for r in results:
            if r["similarity"] >= threshold:
                # Excluir el mismo requisito
                if r.get("metadata", {}).get("req_id") != req_dict.get("id"):
                    duplicates.append(r)

        if duplicates:
            logger.warning(
                f"Posibles duplicados detectados para '{req_dict.get('title')}': {len(duplicates)}"
            )

        return duplicates

    def get_historical_context(
        self,
        project_type: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Obtener contexto histórico de requisitos similares.

        Args:
            project_type: Tipo de proyecto (ej: "api_rest", "web_app").
            top_k: Número de resultados.

        Returns:
            Requisitos históricos relevantes.
        """
        query = f"requisitos para proyecto tipo {project_type}"
        return self.search_similar(query, top_k=top_k)

    # ── Utilidades ───────────────────────────────

    def clear(self) -> int:
        """Limpiar toda la memoria."""
        count: int = int(self.stats().get("total_documents", 0))
        if isinstance(self._collection, InMemoryVectorStore):
            self._collection.delete()
        else:
            # ChromaDB: recrear colección
            try:
                self._collection.delete()
            except Exception:
                pass
        logger.info(f"Memoria limpiada: {count} documentos eliminados")
        return count

    def stats(self) -> dict[str, Any]:
        """Obtener estadísticas de la memoria."""
        count = self._collection.count()
        return {
            "total_documents": count,
            "collection_name": self._collection_name,
            "backend": "chromadb" if CHROMADB_AVAILABLE else "in-memory",
            "persist_directory": self._persist_dir,
        }

    @staticmethod
    def _requirement_to_text(req_dict: dict[str, Any]) -> str:
        """Convertir requisito a texto para embedding."""
        parts = [
            f"Título: {req_dict.get('title', '')}",
            f"Descripción: {req_dict.get('description', '')}",
            f"Tipo: {req_dict.get('req_type', req_dict.get('type', ''))}",
            f"Prioridad: {req_dict.get('priority', '')}",
        ]
        criteria = req_dict.get("acceptance_criteria", [])
        if criteria:
            parts.append(f"Criterios: {'; '.join(criteria)}")
        tags = req_dict.get("tags", [])
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")
        return " | ".join(parts)
