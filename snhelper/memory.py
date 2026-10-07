from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Protocol

from .models import Memory


class MemoryStore(Protocol):
    def add(self, memory: Memory) -> Memory: ...

    def search(self, query: str, limit: int = 5) -> list[Memory]: ...

    def recent(self, limit: int = 20) -> list[Memory]: ...


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", value) if len(token) > 1}


class SQLiteMemoryStore:
    """Durable local memory store with a vector-store-compatible interface.

    The default scorer is lexical and dependency-free. It is deliberately
    behind the ``MemoryStore`` protocol so Chroma, Qdrant, or a LangChain
    retriever can be swapped in without changing any agent.
    """

    def __init__(self, path: str | Path = "data/snhelper.db") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self._db.commit()

    def add(self, memory: Memory) -> Memory:
        tags = ",".join(dict.fromkeys(tag.strip().lower() for tag in memory.tags if tag.strip()))
        cursor = self._db.execute(
            "INSERT INTO memories(title, content, tags, source, created_at) VALUES (?, ?, ?, ?, ?)",
            (memory.title, memory.content, tags, memory.source, memory.created_at),
        )
        self._db.commit()
        memory.memory_id = int(cursor.lastrowid)
        memory.tags = tags.split(",") if tags else []
        return memory

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        return Memory(
            memory_id=int(row["id"]),
            title=row["title"],
            content=row["content"],
            tags=[tag for tag in row["tags"].split(",") if tag],
            source=row["source"],
            created_at=row["created_at"],
        )

    def search(self, query: str, limit: int = 5) -> list[Memory]:
        query_tokens = _tokens(query)
        rows = self._db.execute("SELECT * FROM memories ORDER BY id DESC").fetchall()
        scored: list[tuple[int, int, sqlite3.Row]] = []
        for row in rows:
            raw_haystack = f"{row['title']} {row['content']} {row['tags']}".lower()
            haystack = _tokens(raw_haystack)
            lexical_score = len(query_tokens & haystack)
            substring_score = sum(1 for token in query_tokens if token in raw_haystack)
            score = max(lexical_score, substring_score)
            if score:
                scored.append((score, int(row["id"]), row))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [self._row_to_memory(row) for _, _, row in scored[:limit]]

    def recent(self, limit: int = 20) -> list[Memory]:
        rows = self._db.execute("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def close(self) -> None:
        self._db.close()


class LangChainVectorStore:
    """Adapter for any LangChain VectorStore (Chroma, Qdrant, FAISS, etc.).

    Pass an initialized vector store with ``add_documents`` and
    ``similarity_search`` methods. This keeps provider, embedding, and index
    configuration outside the cognitive agents.
    """

    def __init__(self, vector_store) -> None:
        self.vector_store = vector_store

    def add(self, memory: Memory) -> Memory:
        try:
            from langchain_core.documents import Document
        except ImportError as exc:
            raise RuntimeError("Install snhelper[langchain] to use LangChainVectorStore") from exc
        document = Document(
            page_content=memory.content,
            metadata={"title": memory.title, "tags": memory.tags, "source": memory.source, "created_at": memory.created_at},
        )
        ids = self.vector_store.add_documents([document])
        if ids:
            memory.memory_id = ids[0]
        return memory

    def search(self, query: str, limit: int = 5) -> list[Memory]:
        documents = self.vector_store.similarity_search(query, k=limit)
        return [
            Memory(
                memory_id=document.metadata.get("id"),
                title=document.metadata.get("title", ""),
                content=document.page_content,
                tags=list(document.metadata.get("tags", [])),
                source=document.metadata.get("source", "vector-store"),
                created_at=document.metadata.get("created_at", ""),
            )
            for document in documents
        ]

    def recent(self, limit: int = 20) -> list[Memory]:
        return []
