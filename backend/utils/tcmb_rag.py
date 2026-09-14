#!/usr/bin/env python3
"""
TCMB RAG Vectorstore Pipeline

Fetches datagroups and series from the TCMB EVDS API, normalizes the data,
stores it in 'backend/database/clean_datagroups_with_series.json', and embeds/indexes it into
Qdrant vectorstore collections ('datagroups' and 'series') using Cohere embed-v4.0.

Usage:
    python backend/utils/tcmb_rag.py
    python backend/utils/tcmb_rag.py --json-path backend/database/clean_datagroups_with_series.json
    python backend/utils/tcmb_rag.py --force-extract
    python backend/utils/tcmb_rag.py --skip-embed
"""

import argparse
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set

import cohere
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
import requests

load_dotenv()

# Resolve workspace paths and environment
try:
    from backend.shared.constants import (
        COHERE_API_KEY,
        DATABASE_DIR,
        PROJECT_ROOT,
        TCMB_API_KEY,
        TCMB_DATAGROUPS_JSON_PATH,
        VECTORSTORE_PATH_STR,
    )
    from backend.shared.logger import get_logger

    logger = get_logger("TCMB_RAG")
except ImportError:
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("TCMB_RAG")
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    DATABASE_DIR = PROJECT_ROOT / "backend" / "database"
    VECTORSTORE_PATH_STR = str(DATABASE_DIR / "vectorstore")
    TCMB_DATAGROUPS_JSON_PATH = DATABASE_DIR / "clean_datagroups_with_series.json"
    TCMB_API_KEY = os.getenv("TCMB_API_KEY", "")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")

# UUID namespaces for reproducible point IDs
DATAGROUP_UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "airis.datagroups")
SERIES_UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "airis.series")

# EVDS API Endpoints
EVDS_DATAGROUP_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis/datagroups/type=json&mode=0"
EVDS_SERIES_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis/serieList/type=json&code="

# Embedding configurations
DEFAULT_EMBED_BATCH_SIZE = 32
VECTOR_SIZE = 1536


def chunked(items: List[Any], batch_size: int) -> Generator[List[Any], None, None]:
    """Yield successive batch_size chunks from items."""
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def resolve_json_path(custom_path: Optional[str] = None) -> Path:
    """Find the path for clean_datagroups_with_series.json.
    
    Defaults to backend/database/clean_datagroups_with_series.json.
    """
    if custom_path:
        return Path(custom_path)

    # Primary location: backend/database/clean_datagroups_with_series.json
    if TCMB_DATAGROUPS_JSON_PATH.exists():
        return TCMB_DATAGROUPS_JSON_PATH

    # Fallback check if legacy file exists at project root or working directory
    legacy_candidates = [
        PROJECT_ROOT / "clean_datagroups_with_series.json",
        Path("clean_datagroups_with_series.json"),
    ]
    for candidate in legacy_candidates:
        if candidate.exists():
            return candidate

    return TCMB_DATAGROUPS_JSON_PATH


# ---------------------------------------------------------------------------
# EVDS Data Extraction
# ---------------------------------------------------------------------------


def fetch_and_clean_datagroups(
    json_path: Path,
    api_key: Optional[str] = None,
    force_extract: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch datagroups and series from EVDS API, or load from json_path if existing.

    Avoids duplicate work:
    - If json_path already exists and contains complete series, loads and returns it.
    - If json_path contains partial data, resumes fetching for missing series only.
    - If json_path does not exist or force_extract is True, fetches all.
    """
    key = api_key or TCMB_API_KEY or os.getenv("TCMB_API_KEY", "")
    dg_data: List[Dict[str, Any]] = []

    # 1. Check if the JSON file already exists
    if not force_extract and json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            if isinstance(loaded_data, list) and len(loaded_data) > 0:
                is_complete = all("SERIES" in item for item in loaded_data)
                if is_complete:
                    logger.info(
                        f"Found existing complete dataset at '{json_path}' "
                        f"({len(loaded_data)} datagroups). Skipping EVDS extraction."
                    )
                    return loaded_data
                else:
                    processed_count = sum(1 for item in loaded_data if "SERIES" in item)
                    logger.info(
                        f"Found partial dataset at '{json_path}' "
                        f"({processed_count}/{len(loaded_data)} datagroups processed). Resuming extraction..."
                    )
                    dg_data = loaded_data
        except Exception as e:
            logger.warning(f"Failed to read existing '{json_path}': {e}. Starting fresh extraction.")
            dg_data = []

    if not key:
        raise ValueError(
            "TCMB_API_KEY is not set. Please set TCMB_API_KEY in your environment or .env file."
        )

    # 2. Fetch datagroups catalog if not loaded
    if not dg_data:
        logger.info(f"Fetching datagroups list from EVDS ({EVDS_DATAGROUP_URL})...")
        response = requests.get(EVDS_DATAGROUP_URL, headers={"key": key}, timeout=30)
        response.raise_for_status()
        dg_data = response.json()

        if not isinstance(dg_data, list):
            raise ValueError(f"Unexpected datagroups response format from EVDS: {dg_data}")

        logger.info(f"Retrieved {len(dg_data)} datagroups from EVDS.")

    # 3. Fetch series for datagroups that do not have 'SERIES' yet
    headers = {"key": key}
    total = len(dg_data)
    already_done = sum(1 for item in dg_data if "SERIES" in item)
    logger.info(f"Processing series: {already_done}/{total} datagroups already have series.")

    processed_in_this_run = 0

    for idx, item in enumerate(dg_data, start=1):
        if "SERIES" in item:
            continue

        datagroup_code = item.get("DATAGROUP_CODE")
        if not datagroup_code:
            item["SERIES"] = []
            continue

        url = f"{EVDS_SERIES_URL}{datagroup_code}"
        series_list = []
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    series_list = data
            else:
                logger.warning(
                    f"EVDS returned status {resp.status_code} for datagroup {datagroup_code}"
                )
        except Exception as e:
            logger.warning(f"Error fetching series for datagroup {datagroup_code}: {e}")

        # Clean series fields
        cleaned_series_list = []
        for s in series_list:
            if not isinstance(s, dict):
                continue
            clean_series = {
                "SERIE_CODE": s.get("SERIE_CODE", ""),
                "SERIE_NAME": s.get("SERIE_NAME", ""),
                "SERIE_NAME_ENG": s.get("SERIE_NAME_ENG", ""),
                "FREQUENCY_STR": s.get("FREQUENCY_STR", ""),
                "DEFAULT_AGG_METHOD_STR": s.get("DEFAULT_AGG_METHOD_STR", ""),
                "TAG": s.get("TAG", ""),
                "TAG_ENG": s.get("TAG_ENG", ""),
                "METADATA_LINK": s.get("METADATA_LINK", ""),
                "METADATA_LINK_ENG": s.get("METADATA_LINK_ENG", ""),
                "START_DATE": s.get("START_DATE", ""),
                "END_DATE": s.get("END_DATE", ""),
            }
            cleaned_series_list.append(clean_series)

        item["SERIES"] = cleaned_series_list
        processed_in_this_run += 1
        current_processed = already_done + processed_in_this_run

        print(f"{current_processed}/{total} datagroups processed.")

        # Save progress incrementally every 10 datagroups
        if processed_in_this_run % 10 == 0:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(dg_data, f, ensure_ascii=False, indent=4)

    # Final save
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dg_data, f, ensure_ascii=False, indent=4)

    logger.info(f"Saved complete datagroups and series data to '{json_path}'.")
    return dg_data


# ---------------------------------------------------------------------------
# Qdrant Collections & Deduplication
# ---------------------------------------------------------------------------


def init_qdrant_collections(client: QdrantClient) -> None:
    """Initialize datagroups and series collections in Qdrant with appropriate indices."""
    if not client.collection_exists(collection_name="datagroups"):
        client.create_collection(
            collection_name="datagroups",
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE, distance=models.Distance.COSINE
            ),
        )
        logger.info("Created Qdrant collection 'datagroups'.")
    else:
        cnt = client.count(collection_name="datagroups").count
        logger.info(f"Qdrant collection 'datagroups' exists ({cnt} points).")

    if not client.collection_exists(collection_name="series"):
        client.create_collection(
            collection_name="series",
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE, distance=models.Distance.COSINE
            ),
        )
        logger.info("Created Qdrant collection 'series'.")
    else:
        cnt = client.count(collection_name="series").count
        logger.info(f"Qdrant collection 'series' exists ({cnt} points).")

    # Ensure payload index on metadata.DATAGROUP_CODE for efficient MatchAny filtering
    try:
        client.create_payload_index(
            collection_name="series",
            field_name="metadata.DATAGROUP_CODE",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        logger.info("Payload index on 'metadata.DATAGROUP_CODE' verified in 'series' collection.")
    except Exception as e:
        logger.debug(f"Payload index creation note: {e}")


def get_existing_point_ids(client: QdrantClient, collection_name: str) -> Set[str]:
    """Retrieve all existing point IDs in a collection efficiently without loading vectors."""
    existing_ids: Set[str] = set()
    next_offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=1000,
            offset=next_offset,
            with_vectors=False,
            with_payload=False,
        )
        for p in points:
            existing_ids.add(str(p.id))

        if next_offset is None:
            break

    return existing_ids


# ---------------------------------------------------------------------------
# Embedding & Ingestion
# ---------------------------------------------------------------------------


def embed_batch_with_retry(
    co_client: cohere.ClientV2,
    texts: List[str],
    max_retries: int = 5,
) -> List[List[float]]:
    """Embed texts using Cohere embed-v4.0 with exponential backoff on errors/rate limits."""
    inputs = [{"content": [{"type": "text", "text": text}]} for text in texts]

    for attempt in range(max_retries):
        try:
            response = co_client.embed(
                inputs=inputs,
                model="embed-v4.0",
                input_type="search_document",
                output_dimension=VECTOR_SIZE,
                embedding_types=["float"],
            )
            return response.embeddings.float
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                logger.warning(f"Cohere embedding retry ({attempt + 1}/{max_retries}) in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Cohere embedding failed after {max_retries} attempts: {e}")
                raise


def upload_datagroups(
    client: QdrantClient,
    co_client: cohere.ClientV2,
    datagroups: List[Dict[str, Any]],
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
) -> int:
    """Embed and upload datagroups into Qdrant, skipping already uploaded points."""
    existing_ids = get_existing_point_ids(client, "datagroups")
    logger.info(f"Found {len(existing_ids)} existing points in 'datagroups' collection.")

    pending: List[Dict[str, Any]] = []
    for dg in datagroups:
        dg_code = str(dg.get("DATAGROUP_CODE", "")).strip()
        if not dg_code:
            continue

        point_id = str(uuid.uuid5(DATAGROUP_UUID_NAMESPACE, dg_code))
        if point_id in existing_ids:
            continue

        note = dg.get("NOTE_ENG") or dg.get("NOTE") or ""
        name = dg.get("DATAGROUP_NAME_ENG") or dg.get("DATAGROUP_NAME") or ""
        text = f"{name}\n{note}".strip()
        metadata = {k: v for k, v in dg.items() if k != "SERIES"}

        pending.append(
            {
                "point_id": point_id,
                "code": dg_code,
                "text": text,
                "metadata": metadata,
            }
        )

    if not pending:
        logger.info("All datagroups are already present in Qdrant. Nothing to upload.")
        return 0

    logger.info(f"Embedding and uploading {len(pending)} new datagroups (batch size: {batch_size})...")
    total_uploaded = 0

    for batch in chunked(pending, batch_size):
        texts = [item["text"] for item in batch]
        embeddings = embed_batch_with_retry(co_client, texts)

        points = [
            models.PointStruct(
                id=item["point_id"],
                vector=emb,
                payload={"text": item["text"], "metadata": item["metadata"]},
            )
            for item, emb in zip(batch, embeddings)
        ]

        client.upsert(collection_name="datagroups", points=points)
        total_uploaded += len(points)
        logger.info(f"Upserted {total_uploaded}/{len(pending)} datagroups.")

    return total_uploaded


def upload_series(
    client: QdrantClient,
    co_client: cohere.ClientV2,
    datagroups: List[Dict[str, Any]],
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
) -> int:
    """Embed and upload series into Qdrant, skipping already uploaded points."""
    existing_ids = get_existing_point_ids(client, "series")
    logger.info(f"Found {len(existing_ids)} existing points in 'series' collection.")

    pending: List[Dict[str, Any]] = []
    for dg in datagroups:
        dg_code = str(dg.get("DATAGROUP_CODE", "")).strip()
        series_items = dg.get("SERIES", [])

        for s in series_items:
            serie_code = str(s.get("SERIE_CODE", "")).strip()
            if not serie_code:
                continue

            point_id = str(uuid.uuid5(SERIES_UUID_NAMESPACE, serie_code))
            if point_id in existing_ids:
                continue

            name_eng = s.get("SERIE_NAME_ENG") or s.get("SERIE_NAME") or ""
            freq = s.get("FREQUENCY_STR") or ""
            agg = s.get("DEFAULT_AGG_METHOD_STR") or ""

            series_text = (
                f"Series name: {name_eng}\n"
                f"Frequency: {freq}\n"
                f"Default aggregation: {agg}"
            ).strip()

            series_metadata = {
                **s,
                "DATAGROUP_CODE": dg_code,
                "text": series_text,
            }

            pending.append(
                {
                    "point_id": point_id,
                    "series_code": serie_code,
                    "text": series_text,
                    "metadata": series_metadata,
                }
            )

    if not pending:
        logger.info("All series are already present in Qdrant. Nothing to upload.")
        return 0

    logger.info(f"Embedding and uploading {len(pending)} new series (batch size: {batch_size})...")
    total_uploaded = 0

    for batch in chunked(pending, batch_size):
        texts = [item["text"] for item in batch]
        embeddings = embed_batch_with_retry(co_client, texts)

        points = [
            models.PointStruct(
                id=item["point_id"],
                vector=emb,
                payload={"text": item["text"], "metadata": item["metadata"]},
            )
            for item, emb in zip(batch, embeddings)
        ]

        client.upsert(collection_name="series", points=points)
        total_uploaded += len(points)
        if total_uploaded % (batch_size * 10) == 0 or total_uploaded == len(pending):
            logger.info(f"Upserted {total_uploaded}/{len(pending)} series.")

    return total_uploaded


def repair_nested_vectors(client: QdrantClient, collection_name: str, batch_size: int = 128) -> int:
    """Repair any 2D nested vectors (e.g. [[...]]) into 1D vectors."""
    fixed_count = 0
    next_offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=next_offset,
            with_vectors=True,
            with_payload=True,
        )
        if not points:
            break

        fixed_points = []
        for point in points:
            vector = point.vector
            if isinstance(vector, list) and len(vector) == 1 and isinstance(vector[0], list):
                fixed_points.append(
                    models.PointStruct(
                        id=point.id,
                        vector=vector[0],
                        payload=point.payload,
                    )
                )

        if fixed_points:
            client.upsert(
                collection_name=collection_name,
                points=fixed_points,
            )
            fixed_count += len(fixed_points)

        if next_offset is None:
            break

    return fixed_count


# ---------------------------------------------------------------------------
# Main Orchestration
# ---------------------------------------------------------------------------


def build_tcmb_vectorstore(
    json_path: Optional[str] = None,
    force_extract: bool = False,
    skip_embed: bool = False,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    repair_vectors: bool = False,
) -> None:
    """
    Main pipeline:
    1. Extract or load clean_datagroups_with_series.json (without duplicate EVDS requests).
    2. Connect to Qdrant and initialize collections.
    3. Embed and upsert datagroups and series using Cohere embed-v4.0.
    """
    target_json = resolve_json_path(json_path)

    # 1. Extraction / Load
    datagroups = fetch_and_clean_datagroups(
        json_path=target_json,
        force_extract=force_extract,
    )

    if skip_embed:
        logger.info("Flag --skip-embed provided. Skipping Qdrant indexing.")
        return

    # 2. Check Cohere API key
    co_api_key = COHERE_API_KEY or os.getenv("COHERE_API_KEY", "")
    if not co_api_key:
        raise ValueError("COHERE_API_KEY is not set. Please set COHERE_API_KEY to embed documents.")

    co_client = cohere.ClientV2(api_key=co_api_key)

    # 3. Connect to Qdrant
    logger.info(f"Connecting to Qdrant at '{VECTORSTORE_PATH_STR}'...")
    client = QdrantClient(path=VECTORSTORE_PATH_STR, timeout=60)

    try:
        init_qdrant_collections(client)

        if repair_vectors:
            logger.info("Running vector repair check...")
            repaired_dg = repair_nested_vectors(client, "datagroups")
            repaired_sr = repair_nested_vectors(client, "series")
            logger.info(f"Repaired {repaired_dg} datagroups and {repaired_sr} series vectors.")

        # 4. Upload datagroups
        uploaded_dg = upload_datagroups(
            client=client,
            co_client=co_client,
            datagroups=datagroups,
            batch_size=batch_size,
        )

        # 5. Upload series
        uploaded_sr = upload_series(
            client=client,
            co_client=co_client,
            datagroups=datagroups,
            batch_size=batch_size,
        )

        total_dg = client.count(collection_name="datagroups").count
        total_sr = client.count(collection_name="series").count

        logger.info(
            f"Pipeline complete! Uploaded {uploaded_dg} new datagroups and {uploaded_sr} new series. "
            f"Total in Qdrant: {total_dg} datagroups, {total_sr} series."
        )

    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Fetch TCMB datagroups and series from EVDS, save to JSON, and index into Qdrant vectorstore."
    )
    parser.add_argument(
        "--json-path",
        type=str,
        default=None,
        help="Path to clean_datagroups_with_series.json (default: backend/database/clean_datagroups_with_series.json)",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Force re-extraction from TCMB EVDS API even if the JSON file already exists",
    )
    parser.add_argument(
        "--skip-embed",
        action="store_true",
        help="Only extract/clean and save JSON without embedding/uploading to Qdrant",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_EMBED_BATCH_SIZE,
        help=f"Batch size for Cohere embeddings (default: {DEFAULT_EMBED_BATCH_SIZE})",
    )
    parser.add_argument(
        "--repair-vectors",
        action="store_true",
        help="Scan and repair any nested vectors in existing collections before uploading",
    )

    args = parser.parse_args()

    build_tcmb_vectorstore(
        json_path=args.json_path,
        force_extract=args.force_extract,
        skip_embed=args.skip_embed,
        batch_size=args.batch_size,
        repair_vectors=args.repair_vectors,
    )


if __name__ == "__main__":
    main()
