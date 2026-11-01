"""Retrieval: chunk the registered source PDFs and search them in Pinecone.

Only registry entries with a local `file` and `ingest_allowed: true` are ingested
(sources/registry.yaml). Every chunk carries what a citation needs: source_id, title,
year, url, the printed page label and, where the PDF has an outline, the section.

Baseline retrieval is plain dense search (Pinecone-hosted llama-text-embed-v2).
Hybrid search and rerank come in the improved run (plan §9.5, lever 3).

    uv run python -m nestling.retrieval ingest [SOURCE_ID ...]
    uv run python -m nestling.retrieval search "query text"
"""

import os
import sys
from pathlib import Path

import yaml
from langsmith import traceable
from llama_index.core.node_parser import SentenceSplitter
from pinecone import Pinecone, SchemaBuilder
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "sources" / "registry.yaml"
PDF_DIR = ROOT / "sources" / "pdfs"

NAMESPACE = "sources"
EMBED = {"model": "llama-text-embed-v2", "dimension": 1024, "metric": "cosine"}
DEPLOYMENT = {"deployment_type": "managed", "cloud": "aws", "region": "us-east-1"}
CHUNK_TOKENS = 512
CHUNK_OVERLAP = 64
UPSERT_BATCH = 96  # Pinecone's cap per request when the index embeds the text
CITATION_FIELDS = ["chunk_text", "source_id", "title", "year", "url", "page", "page_label", "section"]


def load_registry() -> dict[str, dict]:
    """Registry entries keyed by source ID."""
    with open(REGISTRY, encoding="utf-8") as f:
        return {s["id"]: s for s in yaml.safe_load(f)["sources"]}


def ingestable(registry: dict[str, dict]) -> list[dict]:
    """Entries that have a local PDF, are cleared for ingestion and are not per-user."""
    return [s for s in registry.values() if s.get("file") and s.get("ingest_allowed") and not s.get("private")]


def _page_sections(reader: PdfReader) -> list[str | None]:
    """Section title for each page, carried forward from the PDF outline (None if no outline)."""
    starts: dict[int, str] = {}

    def walk(items):
        for item in items:
            if isinstance(item, list):
                walk(item)
                continue
            try:
                title = "".join(ch if ch.isprintable() else " " for ch in item.title)
                starts.setdefault(reader.get_destination_page_number(item), " ".join(title.split()))
            except Exception:  # broken outline entry: skip it, keep the rest
                pass

    try:
        walk(reader.outline)
    except Exception:
        pass
    sections, current = [], None
    for i in range(len(reader.pages)):
        current = starts.get(i, current)
        sections.append(current)
    return sections


def load_chunks(source: dict) -> list[dict]:
    """Split one source PDF into citation-ready chunk records."""
    reader = PdfReader(PDF_DIR / source["file"])
    sections = _page_sections(reader)
    splitter = SentenceSplitter(chunk_size=CHUNK_TOKENS, chunk_overlap=CHUNK_OVERLAP)
    base = {k: source[k] for k in ("title", "url") if source.get(k)}
    if source.get("year"):
        base["year"] = int(source["year"])

    chunks = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:  # e.g. pypdf's content-stream limit on a drawing-heavy page
            continue
        if len(text.strip()) < 50:
            continue
        try:
            label = reader.page_labels[i]
        except Exception:
            label = str(i + 1)
        for k, piece in enumerate(splitter.split_text(text)):
            record = {
                "_id": f"{source['id']}:p{i + 1}:c{k}",
                "chunk_text": piece,
                "source_id": source["id"],
                "page": i + 1,
                "page_label": label,
                **base,
            }
            if sections[i]:
                record["section"] = sections[i]
            chunks.append(record)
    return chunks


def get_index(pc: Pinecone | None = None, create: bool = False):
    """The source-library index, targeted by host. Creates it if asked and missing."""
    pc = pc or Pinecone()
    name = os.environ["PINECONE_INDEX"]
    if not pc.has_index(name):
        if not create:
            raise LookupError(f"Pinecone index {name!r} does not exist; run `ingest` first")
        schema = (
            SchemaBuilder()
            .add_string_field("chunk_text", embed=EMBED)
            .add_string_field("source_id", filterable=True)
            .build()
        )
        pc.indexes.create(name=name, schema=schema, deployment=DEPLOYMENT, deletion_protection="disabled")
    return pc.index(host=pc.describe_index(name).host)


def ingest(source_ids: list[str] | None = None) -> dict[str, int]:
    """(Re)ingest sources: drop each source's old chunks, then upsert fresh ones."""
    registry = load_registry()
    sources = ingestable(registry)
    if source_ids:
        unknown = set(source_ids) - {s["id"] for s in sources}
        if unknown:
            raise ValueError(f"Not ingestable (missing file, private, or ingest_allowed false): {sorted(unknown)}")
        sources = [s for s in sources if s["id"] in source_ids]

    index = get_index(create=True)
    counts = {}
    for source in sources:
        chunks = load_chunks(source)
        try:
            index.documents.delete(namespace=NAMESPACE, filter={"source_id": {"$eq": source["id"]}})
        except Exception:  # first ingest: namespace does not exist yet
            pass
        for start in range(0, len(chunks), UPSERT_BATCH):
            index.documents.upsert(namespace=NAMESPACE, documents=chunks[start:start + UPSERT_BATCH])
        counts[source["id"]] = len(chunks)
        print(f"{source['id']:20} {len(chunks):5} chunks", flush=True)
    return counts


@traceable(name="retrieval", run_type="retriever")
def search(query: str, top_k: int = 5, source_ids: list[str] | None = None) -> list[dict]:
    """Dense search over the source library. Each hit has a score plus CITATION_FIELDS."""
    index = get_index()
    response = index.documents.search(
        namespace=NAMESPACE,
        top_k=top_k,
        score_by=[{"type": "embed", "fields": ["chunk_text"], "query": query}],
        include_fields=CITATION_FIELDS,
        filter={"source_id": {"$in": source_ids}} if source_ids else None,
    )
    return [
        {"id": doc.id, "score": doc.score, **{k: doc.get(k) for k in CITATION_FIELDS}}
        for doc in response.matches
    ]


def format_citation(hit: dict) -> str:
    """Short citation for a source chip, e.g. 'WHO-ANC · WHO recommendations… (2016), p. 34'."""
    parts = [f"{hit['source_id']} · {hit.get('title')}"]
    if hit.get("year"):
        parts[0] += f" ({hit['year']})"
    parts.append(f"p. {hit.get('page_label') or hit.get('page')}")
    if hit.get("section"):
        parts.append(hit["section"])
    return ", ".join(parts)


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    command, *args = sys.argv[1:] or ["help"]
    if command == "ingest":
        ingest(args or None)
    elif command == "search" and args:
        for hit in search(" ".join(args)):
            print(f"{hit['score']:.3f}  {format_citation(hit)}\n       {hit['chunk_text'][:160]!r}")
    else:
        print(__doc__)
