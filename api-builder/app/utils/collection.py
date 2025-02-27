import base64
import json
import os

import requests
from app.config import settings
from elasticsearch import Elasticsearch, helpers
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pymilvus import MilvusClient
from tqdm import tqdm

milvus_client = milvus_client = MilvusClient(uri="https://in03-0e20997fb5c4a00.serverless.gcp-us-west1.cloud.zilliz.com",
                                             token='6c5c4aca5950756003f5db05fa289b291aa796575bb9d2bd5ee3f41d6391be6237b3cab4c3c42b877b77409b4337e424d740b3b2')
os.environ[
    "OPENAI_API_KEY"] = "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"
OPENAI_API_KEY = os.getenv(
    "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")


def get_text_bundle(base_folder_path):
    docs = []
    folders = os.listdir(base_folder_path)
    for folder in folders:
        folder_path = os.path.join(base_folder_path, folder)
        all_items = os.listdir(folder_path)

        txt_path = None
        json_path = None

        for item in all_items:
            full_path = os.path.join(folder_path, item)
            if os.path.isdir(full_path):
                continue
            if item.endswith(".txt"):
                txt_path = full_path
            elif item.endswith(".json"):
                json_path = full_path

        with open(txt_path, "r", encoding="utf-8") as txt_file, \
                open(json_path, "r", encoding="utf-8") as json_file:
            text_content = txt_file.read()  # .txt 파일 내용
            json_content = json.load(json_file)  # .json 파일 내용 (파싱)

            docs.append({
                "date": json_content['date'],
                "bundle": folder,
                "content": text_content})
    return docs


def text_chunking(base_folder_path):
    docs = get_text_bundle(base_folder_path)
    documents = [
        Document(page_content=doc["content"], metadata={"date": doc["date"], 'bundle': doc['bundle']}) for doc in docs
    ]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)
    return texts


def emb_text(text):
    openai_client = OpenAI()
    return (
        openai_client.embeddings.create(input=text, model="text-embedding-3-small")
        .data[0]
        .embedding
    )


def to_upload_milvus_text(texts):
    data = []
    for line in tqdm(texts, desc="Creating embeddings"):
        data.append({"metadata": line.metadata, "vector": emb_text(line.page_content), "text": line.page_content})
    return data


def create_2025_text_milvus_collection():
    collection_name = "text_2025_collection"

    if milvus_client.has_collection(collection_name):
        print(f"Collection '{collection_name}' already exists. Skip creation.")
        return collection_name

    milvus_client.create_collection(
        collection_name=collection_name,
        dimension=1536,
        metric_type="IP",
        consistency_level="Strong",
    )
    return collection_name


def milvus_upload_text(texts):
    collection_name = create_2025_text_milvus_collection()
    data = to_upload_milvus_text(texts)
    milvus_client.flush(collection_name)
    stats = milvus_client.get_collection_stats(collection_name=collection_name)
    current_count = stats["row_count"]
    next_id = current_count
    for doc in data:
        doc["id"] = next_id
        next_id += 1
        milvus_client.insert(collection_name=collection_name, data=doc)


def encode_image(image_path):
    """Getting the base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def image_summarize(img_base64, prompt):
    """Make image summary"""
    chat = ChatOpenAI(model="gpt-4o", max_tokens=400)

    msg = chat.invoke(
        [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                    },
                ]
            )
        ]
    )
    return msg.content


def generate_img_summaries(base_folder_path):
    """
    Generate summaries and base64 encoded strings for images
    path: Path to list of .png,.jpeg files extracted by Unstructured
    """

    # Prompt
    from tqdm import tqdm

    prompt = """You are an assistant tasked with summarizing images for retrieval. \
        These summaries will be embedded and used to retrieve the raw image. \
        Give a concise summary of the image that is well optimized for retrieval. \
        Summarize all the important information in the image while preserving key details. \
        Focus on summarizing the textual elements within the image and exclude any design-related aspects.\
        Write it in Korean."""

    final_image_data = []
    folders = os.listdir(base_folder_path)

    for folder in folders:
        folder_path = os.path.join(base_folder_path, folder)
        all_items = os.listdir(folder_path)
        image_folder = None
        for item in all_items:
            full_path = os.path.join(folder_path, item)
            if os.path.isdir(full_path):
                image_folder = full_path
        image_files = os.listdir(image_folder)
        # Store base64 encoded images
        img_base64_list = []
        # Store image summaries
        image_summaries = []
        for img_file in tqdm(sorted(image_files), desc="Processing images"):
            img_path = os.path.join(image_folder, img_file)
            try:
                base64_image = encode_image(img_path)
                img_base64_list.append(base64_image)
                image_summaries.append(image_summarize(base64_image, prompt))


            except Exception as e:
                print(f"Error processing image {img_file}: {e}")
        json_path = None
        for item in all_items:
            full_path = os.path.join(folder_path, item)
            if item.endswith(".json"):
                json_path = full_path
        with open(json_path, "r", encoding="utf-8") as json_file:
            json_content = json.load(json_file)
            img_data = []
            for base64, image_summary in zip(img_base64_list, image_summaries):
                images_dict = {'summary': image_summary,
                               'img_base64': base64,
                               'metadata': {'bundle': folder,
                                            'date': json_content['date']}
                               }
                img_data.append(images_dict)
        final_image_data.append(img_data)
    return final_image_data


def to_upload_milvus_image(image_datas):
    final_img_data = []
    for image_data in image_datas:
        img_data = []
        for line in tqdm(image_data, desc="Creating embeddings"):
            img_data.append({"vector": emb_text(line['summary']), "img_summary": line['summary'], "metadata": line['metadata']})
        final_img_data.append(img_data)
    return final_img_data


def create_2025_image_milvus_collection():
    collection_name = "image_2025_collection"

    if milvus_client.has_collection(collection_name):
        print(f"Collection '{collection_name}' already exists. Skip creation.")
        return collection_name

    milvus_client.create_collection(
        collection_name=collection_name,
        dimension=1536,
        metric_type="IP",
        consistency_level="Strong",
    )
    return collection_name


def milvus_upload_image(image_datas):
    collection_name = create_2025_image_milvus_collection()
    datas = to_upload_milvus_image(image_datas)
    for data in datas:
        milvus_client.flush(collection_name)
        stats = milvus_client.get_collection_stats(collection_name=collection_name)
        current_count = stats["row_count"]
        next_id = current_count
        for doc in data:
            doc["id"] = next_id
            next_id += 1
            milvus_client.insert(collection_name=collection_name, data=doc)


def get_es_client():
    """
    새로운 Elasticsearch 클라이언트 생성 (API Key 인증)
    """
    headers = {
        "Authorization": f"ApiKey {settings.ELASTIC_API_KEY}",
        "X-Token": settings.X_TOKEN
    }

    return {
        "url": f"{settings.ELASTIC_CLOUD_URL}",
        "headers": headers
    }


def get_max_id(index_name):
    """
    Elasticsearch에서 현재 인덱스에 색인된 문서 개수를 가져옴.
    """
    es_client = get_es_client()
    es = Elasticsearch(es_client["url"], headers=es_client["headers"])

    try:
        if not es.ping():
            print("❌ Elasticsearch 서버에 연결할 수 없습니다.")
            return 0  # Elasticsearch 연결 실패 시 0 반환

        response = es.count(index=index_name)  # 문서 개수 요청
        return response["count"]  # 색인된 문서 개수 반환

    except Exception as e:
        print(f"❌ 문서 개수 조회 중 오류 발생: {e}")
        return 0  # 오류 발생 시 0 반환

    finally:
        es.close()


from elasticsearch import Elasticsearch, helpers


def create_text_mapping(index_name):
    """
    Elasticsearch 텍스트 인덱스를 생성하고 매핑을 설정
    이미 인덱스가 존재하면 매핑을 다시 생성하지 않음
    """
    # 수동 매핑 정의 (텍스트용)
    mapping = {
        "mappings": {
            "properties": {
                "page_content": {
                    "type": "text"
                },
                "metadata": {
                    "properties": {
                        "bundle": {
                            "type": "keyword"
                        },
                        "date": {
                            "type": "date",
                            "format": "yyyy-MM-dd"
                        }
                    }
                }
            }
        }
    }

    es_client = get_es_client()
    es = Elasticsearch(es_client["url"], headers=es_client["headers"])

    if not es.ping():
        print("❌ Elasticsearch 서버에 연결할 수 없습니다.")
        return

    # 인덱스가 존재하지 않으면 생성
    if not es.indices.exists(index=index_name):
        print(f"'{index_name}' 인덱스가 존재하지 않아 생성합니다...")
        es.indices.create(index=index_name, body=mapping)
    else:
        print(f"'{index_name}' 인덱스가 이미 존재합니다. 매핑을 다시 생성하지 않습니다.")

    es.close()


def elastic_indexing_text(docs):
    """
    Elasticsearch에 텍스트 문서를 개별적으로 색인하며, 각 문서마다 refresh를 실행
    """
    es_client = get_es_client()
    es = Elasticsearch(es_client["url"], headers=es_client["headers"])
    index_name = "text_data_2025"

    try:
        if not es.ping():
            print("❌ Elasticsearch 서버에 연결할 수 없습니다.")
            return

        # 매핑을 확인하고 인덱스가 없다면 생성
        create_text_mapping(index_name)

        # 색인 시작 (각 문서마다 refresh 수행)
        current_id = get_max_id(index_name)

        for doc in docs:
            es.index(
                index=index_name,
                id=str(current_id),
                body={
                    "page_content": doc.page_content,
                    "metadata": {
                        "bundle": doc.metadata["bundle"],
                        "date": doc.metadata["date"]
                    }
                },
                refresh=True
            )
            current_id += 1

    except Exception as e:
        print(f"❌ 색인 중 오류 발생: {e}")

    finally:
        es.close()


def create_image_mapping(index_name):
    """
    Elasticsearch 이미지 인덱스를 생성하고 매핑을 설정
    이미 인덱스가 존재하면 매핑을 다시 생성하지 않음
    """
    # 수동 매핑 정의 (이미지용)
    image_mapping = {
        "mappings": {
            "properties": {
                "img_base64": {
                    "type": "text"
                },
                "image_summary": {
                    "type": "text"
                },
                "metadata": {
                    "properties": {
                        "bundle": {
                            "type": "keyword"
                        },
                        "date": {
                            "type": "date",
                            "format": "yyyy-MM-dd"
                        }
                    }
                }
            }
        }
    }

    es_client = get_es_client()
    es = Elasticsearch(es_client["url"], headers=es_client["headers"])

    if not es.ping():
        print("❌ Elasticsearch 서버에 연결할 수 없습니다.")
        return

    # 인덱스가 존재하지 않으면 생성
    if not es.indices.exists(index=index_name):
        print(f"'{index_name}' 인덱스가 존재하지 않아 생성합니다...")
        es.indices.create(index=index_name, body=image_mapping)
    else:
        print(f"'{index_name}' 인덱스가 이미 존재합니다. 매핑을 다시 생성하지 않습니다.")

    es.close()


def elastic_indexing_image(docs):
    """
    Elasticsearch에 이미지를 개별적으로 색인하며, 각 문서마다 refresh를 실행
    """
    es_client = get_es_client()
    es = Elasticsearch(es_client["url"], headers=es_client["headers"])
    index_name = "image_data_2025"

    try:
        if not es.ping():
            print("❌ Elasticsearch 서버에 연결할 수 없습니다.")
            return

        # 매핑을 확인하고 인덱스가 없다면 생성
        create_image_mapping(index_name)

        # 색인 시작 (각 문서마다 refresh 수행)
        current_id = get_max_id(index_name)

        for doc in docs:
            for img in doc:
                es.index(
                    index=index_name,
                    id=str(current_id),
                    body={
                        "img_base64": img["img_base64"],
                        "image_summary": img["summary"],
                        "metadata": {
                            "bundle": img["metadata"]["bundle"],
                            "date": img["metadata"]["date"]
                        }
                    },
                    refresh=True
                )
                current_id += 1

    except Exception as e:
        print(f"❌ 색인 중 오류 발생: {e}")

    finally:
        es.close()
