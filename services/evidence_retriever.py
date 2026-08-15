from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_TOP_K = 5

SEMANTIC_WEIGHT = 0.70
TFIDF_WEIGHT = 0.30


@lru_cache(maxsize=1)
def get_semantic_model():
    return SentenceTransformer(
        "all-MiniLM-L6-v2"
    )


def build_question_query(
    question_text,
    description=None,
):
    parts = []

    if question_text:
        parts.append(
            str(question_text).strip()
        )

    if description:
        parts.append(
            str(description).strip()
        )

    return " ".join(parts)


class EvidenceRetriever:
    def __init__(self, evidence_documents):
        self.chunks = [
            chunk
            for document in evidence_documents
            for chunk in document.get(
                "chunks",
                [],
            )
            if chunk.get("text")
        ]

        self.vectorizer = None
        self.evidence_matrix = None
        self.semantic_model = None
        self.semantic_embeddings = None

        if not self.chunks:
            return

        texts = [
            chunk["text"]
            for chunk in self.chunks
        ]

        # -------------------------
        # Lexical retrieval
        # -------------------------

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )

        self.evidence_matrix = (
            self.vectorizer.fit_transform(
                texts
            )
        )

        # -------------------------
        # Semantic retrieval
        # -------------------------

        self.semantic_model = (
            get_semantic_model()
        )

        self.semantic_embeddings = (
            self.semantic_model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        )

    def search(
        self,
        question_text,
        description=None,
        top_k=DEFAULT_TOP_K,
    ):
        if not self.chunks:
            return []

        query = build_question_query(
            question_text=question_text,
            description=description,
        )

        if not query:
            return []

        # -------------------------
        # TF-IDF scores
        # -------------------------

        query_vector = (
            self.vectorizer.transform(
                [query]
            )
        )

        tfidf_scores = cosine_similarity(
            query_vector,
            self.evidence_matrix,
        ).flatten()

        # -------------------------
        # Semantic scores
        # -------------------------

        semantic_query = (
            self.semantic_model.encode(
                [query],
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0]
        )

        semantic_scores = (
            self.semantic_embeddings
            @ semantic_query
        )

        # -------------------------
        # Individual rankings
        # -------------------------

        tfidf_order = (
            tfidf_scores.argsort()[::-1]
        )

        semantic_order = (
            semantic_scores.argsort()[::-1]
        )

        tfidf_ranks = {
            int(chunk_index): rank
            for rank, chunk_index in enumerate(
                tfidf_order,
                start=1,
            )
        }

        semantic_ranks = {
            int(chunk_index): rank
            for rank, chunk_index in enumerate(
                semantic_order,
                start=1,
            )
        }

        # -------------------------
        # Weighted hybrid scoring
        # -------------------------

        ranked_results = []

        for index, chunk in enumerate(
            self.chunks
        ):
            tfidf_score = float(
                tfidf_scores[index]
            )

            semantic_score = float(
                semantic_scores[index]
            )

            hybrid_score = (
                SEMANTIC_WEIGHT
                * semantic_score
                +
                TFIDF_WEIGHT
                * tfidf_score
            )

            ranked_results.append(
                {
                    "source_id": chunk[
                        "source_id"
                    ],
                    "evidence_id": chunk[
                        "evidence_id"
                    ],
                    "file_name": chunk[
                        "file_name"
                    ],
                    "file_type": chunk[
                        "file_type"
                    ],
                    "score": round(
                        hybrid_score,
                        4,
                    ),
                    "hybrid_score": round(
                        hybrid_score,
                        4,
                    ),
                    "tfidf_score": round(
                        tfidf_score,
                        4,
                    ),
                    "semantic_score": round(
                        semantic_score,
                        4,
                    ),
                    "tfidf_rank": (
                        tfidf_ranks[index]
                    ),
                    "semantic_rank": (
                        semantic_ranks[index]
                    ),
                    "text": chunk[
                        "text"
                    ],
                    "provenance": chunk[
                        "provenance"
                    ],
                }
            )

        ranked_results.sort(
            key=lambda result: (
                result["hybrid_score"]
            ),
            reverse=True,
        )

        return ranked_results[:top_k]