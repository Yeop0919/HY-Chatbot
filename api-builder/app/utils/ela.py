from elasticsearch import Elasticsearch
import re
import os
import json
from datetime import datetime, timedelta
from konlpy.tag import Okt,Komoran
from app.config import settings
import requests
from pymilvus import MilvusClient
from openai import OpenAI
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

def get_es_client():
    """
    Elasticsearch 로컬 클라이언트 생성
    """
    return Elasticsearch("http://localhost:8001")

def check_elasticsearch_connection():
    """
    Elasticsearch 연결 상태 확인
    """
    es = get_es_client()
    try:
        health = es.cluster.health()
        print(f"✅ Elasticsearch 연결 성공! 상태: {health['status']}")
        return {"status": "connected", "cluster_status": health["status"], "message": "Elasticsearch 연결 성공!"}
    except Exception as e:
        print(f"❌ Elasticsearch 요청 오류: {str(e)}")
        return {"status": "error", "error": f"Elasticsearch 요청 오류: {str(e)}"}
    finally:
        es.close()

komoran = Komoran()

def extract_keywords(query: str):
    """
    한국어 문장에서 주요 키워드 추출 (명사, 동사, 형용사)
    """
    stopwords = {'것', '하다', '되다', '있다', '없다', '이다', '그', '수', '이', '저'}
    keywords = []

    for word, pos in komoran.pos(query):
        if pos in ["NNG", "NNP", "VV", "VA"]:
            word = word.strip()
            if word not in stopwords:
                keywords.append(word)

    return keywords

### 날짜 추출 함수 (텍스트)
def extract_date_from_query(query: str):
    now = datetime.now()
    current_year = str(now.year)

    # "년" 또는 "월" 단어가 있을 때만 인식
    match = re.search(r'(\d{4})년\s*(\d{1,2})?월?', query)
    if match:
        year = match.group(1) if match.group(1) else current_year
        month_raw = match.group(2)
        month = month_raw.zfill(2) if month_raw else None

        if month:
            return f"{year}-{month}", f"{year}-{month}"
        else:
            return f"{year}-01", f"{year}-12"

    return None, None


def extract_date_with_day_from_query(query: str):
    now = datetime.now()
    current_year = str(now.year)

    # "년", "월", "일" 명시된 경우만 인식
    match = re.search(r'(\d{4})년\s*(\d{1,2})?월?\s*(\d{1,2})?일?', query)
    if match:
        year = match.group(1) if match.group(1) else current_year
        month_raw = match.group(2)
        day_raw = match.group(3)

        month = month_raw.zfill(2) if month_raw else None
        day = day_raw.zfill(2) if day_raw else None

        try:
            if day and month:
                return f"{year}-{month}-{day}", f"{year}-{month}-{day}"
            elif month:
                last_day = (datetime(int(year), int(month) % 12 + 1, 1) - timedelta(days=1)).day
                return f"{year}-{month}-01", f"{year}-{month}-{last_day}"
            else:
                return f"{year}-01-01", f"{year}-12-31"
        except ValueError:
            return None, None

    return None, None


def text_index_sort(year_list: list):
    """
    색인 정리
    """
    index_list = []
    if "2022-2024" in year_list:
        index_list.append("text_data")
    if "2025" in year_list:
        index_list.append("text_test_data")
    return ",".join(index_list)

def image_index_sort(year_list: list):
    """
    색인 정리
    """
    index_list = []
    if "2022-2024" in year_list:
        index_list.append("image_data")
    if "2025" in year_list:
        index_list.append("image_summary_by_bundle")
    return ",".join(index_list)


def search_text_es(query: str, year_list: list, size: int = 5):
    """
    로컬 Elasticsearch에서 본문 검색 (BM25 점수만 반환)
    """
    es = get_es_client()
    index_name = text_index_sort(year_list)
    keywords = extract_keywords(query)
    if index_name == "text_data":
        start_date, end_date = extract_date_from_query(query)
    elif index_name == "text_test_data":
        start_date, end_date = extract_date_with_day_from_query(query)

    filter_conditions = []
    if start_date and end_date:
        filter_conditions.append({"range": {"metadata.date": {"gte": start_date, "lte": end_date}}})

    es_query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"page_content": {"query": " ".join(keywords), "operator": "or"}}}
                ],
                "filter": filter_conditions
            }
        }
    }

    try:
        response = es.search(index=index_name, body=es_query, size=size)
        hits = response.get("hits", {}).get("hits", [])

        return hits if hits else [{
            "_index": f"{index_name}",
            "_id": "-1",
            "_score": 1e-6,
            "_source": {
                "page_content": "검색된 공지가 없습니다.",
                "metadata": {
                    "doc_name": "no_result",
                    "date": "0000-00",
                    "bundle": "not in bundle"
                }
            }
        }]
    finally:
        es.close()

def search_image_es(query: str, year_list: list, size: int = 10):
    """
    로컬 Elasticsearch에서 이미지 검색 (Base64 제외)
    """
    es = get_es_client()
    index_name = image_index_sort(year_list)
    keywords = extract_keywords(query)
    start_date, end_date = extract_date_with_day_from_query(query)

    filter_conditions = []
    if start_date and end_date:
        filter_conditions.append({"range": {"metadata.date": {"gte": start_date, "lte": end_date}}})

    es_query = {
        "_source": {
            "excludes": ["img_base64"]
        },
        "query": {
            "bool": {
                "must": [
                    {"match": {"image_summary": {"query": " ".join(keywords), "operator": "or"}}}
                ],
                "filter": filter_conditions
            }
        }
    }

    try:
        response = es.search(index=index_name, body=es_query, size=size)
        hits = response.get("hits", {}).get("hits", [])

        return hits if hits else [{
            "_index": f"{index_name}",
            "_id": "-1",
            "_score": 1e-6,
            "_source": {
                "image_summary": "검색된 공지가 없습니다.",
                "metadata": {
                    "doc_name": "no_result",
                    "date": "0000-00",
                    "bundle": "not in bundle"
                }
            }
        }]
    finally:
        es.close()



def search_base64(query: str, size: int = 1):
    """
    Elasticsearch에서 이미지의 Base64 데이터 검색 (ID 기반)
    """
    es = get_es_client()
    index_name = "image_data"

    es_query = {
        "query": {
            "ids": {
                "values": [query] if isinstance(query, str) else query
            }
        }
    }

    try:
        response = es.search(index=index_name, body=es_query, size=size)
        hits = response.get("hits", {}).get("hits", [])

        return [hit["_source"].get("img_base64", "") for hit in hits if "_source" in hit] or [None]
    finally:
        es.close()

def search_base64_by_bundle(bundle, size: int = 15):
    """
    로컬 Elasticsearch에서 같은 bundle을 가진 이미지 묶음을 검색
    """
    index_name = "image_summary_by_bundle"

    es = get_es_client()

    es_query = {
        "_source": ["img_base64"],
        "query": {
            "term": {
                "metadata.bundle": bundle
            }
        },
        "size": size
    }

    try:
        response = es.search(index=index_name, body=es_query)
        base64_results = [hit["_source"]["img_base64"] for hit in response.get("hits", {}).get("hits", [])]
        return base64_results if base64_results else [{"error": "❌ 검색된 데이터가 없습니다."}]

    except Exception as e:
        return [{"error": f"❌ 검색 중 오류 발생: {str(e)}"}]

    finally:
        es.close()

#===========================================================================================================

#text 공지 임베딩 후 milvus에 업로드
embedding_dim=1536
openai_client = OpenAI()

def emb_text(text):
    openai_client = OpenAI()
    embedding = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    ).data[0].embedding

    # L2 정규화
    norm = np.linalg.norm(embedding)
    normalized_embedding = embedding if norm == 0 else np.array(embedding) / norm

    return normalized_embedding.tolist()

def emb_text_m3(text):
    model = SentenceTransformer("BAAI/bge-m3")
    embeddings = model.encode(text, normalize_embeddings=True)
    return embeddings

milvus_client = MilvusClient(uri=os.getenv("MILVUS_URI", ""), token=os.getenv("MILVUS_TOKEN", ""))


def milvus_text_search(user_query,year):
    question = user_query
    if year=='2022-2024':
        collection_name = "txt_collection"
    elif year == '2025':
        collection_name="text_collection"
    try:
        search_res = milvus_client.search(
        collection_name=collection_name,
        data=[
            emb_text_m3(question)
        ],
        limit=5,
        search_params={"metric_type": "IP", "params": {}},  # Inner product distance
        output_fields=["text","metadata"],
        )
        dense_results = [
        {"id": result["id"],
         "text": result["entity"].get("text"),
         "distance": result["distance"],
         "date": result["entity"].get("metadata",{}).get("date", "날짜 없음"),
         'bundle':result["entity"].get("metadat",{}).get("bundle","bundle 없음")}
        for result in search_res[0]
        ]


        if not dense_results:
            return print("\n❌ [DEBUG] 검색 결과 없음")

        else:
            return dense_results
    except Exception as e:
        return print(f"\n❌ [DEBUG] milvus 검색 중 오류 발생: {e}")

def milvus_image_search(user_query,year):
    question = user_query
    if year=='2022-2024':
        collection_name = "img_collection"
    elif year == '2025':
        collection_name="summary_by_bundle"
    try:
        search_res = milvus_client.search(
        collection_name=collection_name,
        data=[
            emb_text(question)
        ],
        limit=10,
        search_params={"metric_type": "IP", "params": {}},  # Inner product distance
        output_fields=["img_summary",'metadata'],
        )
        dense_results = [
        {"id": result["id"],
         "img_summary": result["entity"].get("img_summary"),
         "distance": result["distance"],
         "date":result["entity"].get("metadata",{}).get("date","날짜 없음"),
         "bundle":result["entity"].get("metadata",{}).get("bundle","bundle 없음")}
        for result in search_res[0]
        ]

        if not dense_results:
            return print("\n❌ [DEBUG] 검색 결과 없음")

        else:
            return dense_results
    except Exception as e:
        return print(f"\n❌ [DEBUG] milvus 검색 중 오류 발생: {e}")
