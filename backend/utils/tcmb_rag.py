from qdrant_client import QdrantClient
from qdrant_client import models
import os
import json
import uuid
import cohere
from dotenv import load_dotenv
load_dotenv()
client = QdrantClient(path="./backend/database/vectorstore", timeout=30)
if not client.collection_exists(collection_name="datagroups"):
    client.create_collection(
        collection_name="datagroups",
        vectors_config=models.VectorParams(
            size=1536, distance=models.Distance.COSINE
        ),
    )
else:
    print("Datagroups collection already exists")
    print(client.count(collection_name="datagroups"))

if not client.collection_exists(collection_name="series"):
    client.create_collection(
        collection_name="series",
        vectors_config=models.VectorParams(
            size=1536, distance=models.Distance.COSINE
        ),
    )
else:
    print("Series collection already exists")
    print(client.count(collection_name="series"))

with open("clean_datagroups_with_series.json", "r", encoding="utf-8") as f:
    datagroups = json.load(f)

co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

DATAGROUP_UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "airis.datagroups")
SERIES_UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "airis.series")
EMBED_BATCH_SIZE = 8


def chunked(items, batch_size):
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def get_first_point_vector(collection_name: str):
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=1,
        with_vectors=True,
    )
    if not points:
        return None
    return points[0].vector

datagroup_vector = get_first_point_vector("datagroups")
print(len(datagroup_vector))

def repair_nested_vectors(collection_name: str, batch_size: int = 128):
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


# for datagroup in datagroups:
#     point_id = str(uuid.uuid5(DATAGROUP_UUID_NAMESPACE, datagroup["DATAGROUP_CODE"]))
#     existing_points = client.retrieve(
#         collection_name="datagroups",
#         ids=[point_id],
#     )
#     if existing_points:
#         print(f"Skipped {datagroup['DATAGROUP_CODE']} (already exists)")
#         continue


#     note = ""
#     if 'NOTE_ENG' not in datagroup:
#         if 'NOTE' in datagroup:
#             note = datagroup["NOTE"]
#     else:
#         note = datagroup["NOTE_ENG"]

#     text = datagroup["DATAGROUP_NAME_ENG"] + "\n" + note
#     metadata = {
#         **datagroup,
#     }
#     metadata.pop("SERIES")
#     print(metadata)
#     print(text)

#     embedding = co.embed(
#         inputs=[{"content": [{"type": "text", "text": text}]}],
#         model="embed-v4.0",
#         input_type="search_document",
#         output_dimension=1536,
#         embedding_types=["float"],
#     ).embeddings.float
#     client.upsert(
#         collection_name="datagroups",
#         points=[models.PointStruct(id=point_id, vector=embedding, payload={"text": text, "metadata": metadata})],
#     )
#     print(f"Upserted {datagroup['DATAGROUP_CODE']}")

# count = 0
# pending_series_points = []
# for datagroup in datagroups:
#     series = datagroup["SERIES"]
#     datagroup_code = datagroup["DATAGROUP_CODE"]
#     for series in series:
#         series_code = series["SERIE_CODE"]
#         series_name_eng = series["SERIE_NAME_ENG"]
#         frequency_string = series["FREQUENCY_STR"]
#         default_aggregation = series["DEFAULT_AGG_METHOD_STR"]
#         point_id = str(uuid.uuid5(SERIES_UUID_NAMESPACE, series_code))
#         existing_points = client.retrieve(
#             collection_name="series",
#             ids=[point_id],
#         )
#         if existing_points:
#             print(f"Skipped {series_code} (already exists)")
#             continue
#         series_text = f"Series name: {series_name_eng}\nFrequency: {frequency_string}\nDefault aggregation: {default_aggregation}"
#         series_metadata = {
#             **series,
#             "DATAGROUP_CODE": datagroup_code,
#         }
        
        
#         series_metadata.pop("SERIE_NAME_ENG")
#         series_metadata.pop("FREQUENCY_STR")
#         series_metadata.pop("DEFAULT_AGG_METHOD_STR")


#         pending_series_points.append(
#             {
#                 "point_id": point_id,
#                 "series_code": series_code,
#                 "text": series_text,
#                 "metadata": series_metadata,
#             }
#         )

# for batch in chunked(pending_series_points, EMBED_BATCH_SIZE):
#     embeddings = co.embed(
#         inputs=[
#             {"content": [{"type": "text", "text": item["text"]}]}
#             for item in batch
#         ],
#         model="embed-v4.0",
#         input_type="search_document",
#         output_dimension=1536,
#         embedding_types=["float"],
#     ).embeddings.float

#     points = [
#         models.PointStruct(
#             id=item["point_id"],
#             vector=embedding,
#             payload={"text": item["text"], "metadata": item["metadata"]},
#         )
#         for item, embedding in zip(batch, embeddings)
#     ]
#     client.upsert(
#         collection_name="series",
#         points=points,
#     )
#     for item in batch:
#         print(f"Upserted {item['series_code']}, {count}")
#         count += 1

client.close()