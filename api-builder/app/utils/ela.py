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
    """
    자연어 쿼리에서 날짜(YYYY-MM 또는 YYYY년 형태)를 추출하는 함수
    """
    now = datetime.now()
    current_year = str(now.year)

    match = re.search(r'(\d{4})[년\s\-]*(\d{0,2})[월\s\-]*', query)
    if match:
        year = match.group(1) if match.group(1) else current_year
        month = match.group(2).zfill(2) if match.group(2) else None

        if month:
            return f"{year}-{month}", f"{year}-{month}"
        else:
            return f"{year}-01", f"{year}-12"

    return None, None

def extract_date_with_day_from_query(query: str):
    """
    자연어 쿼리에서 날짜(YYYY-MM-DD 또는 YYYY-MM)를 추출
    """
    now = datetime.now()
    current_year = str(now.year)

    match = re.search(r'(\d{4})[년\s\-]*(\d{0,2})[월\s\-]*(\d{0,2})[일\s\-]*', query)
    if match:
        year = match.group(1) if match.group(1) else current_year
        month = match.group(2).zfill(2) if match.group(2) else None
        day = match.group(3).zfill(2) if match.group(3) else None

        if day and month:
            return f"{year}-{month}-{day}", f"{year}-{month}-{day}"
        elif month:
            last_day = (datetime(int(year), int(month) % 12 + 1, 1) - timedelta(days=1)).day
            return f"{year}-{month}-01", f"{year}-{month}-{last_day}"
        else:
            return f"{year}-01-01", f"{year}-12-31"

    return None, None

def text_index_sort(year_list: list):
    """
    색인 정리
    """
    index_list = []
    if "2022-2024" in year_list:
        index_list.append("text_data")
    if "2025" in year_list:
        index_list.append("text_data_2025")
    return ",".join(index_list)

def image_index_sort(year_list: list):
    """
    색인 정리
    """
    index_list = []
    if "2022-2024" in year_list:
        index_list.append("image_data")
    if "2025" in year_list:
        index_list.append("image_data_2025")
    return ",".join(index_list)


def search_text_es(query: str, year_list: list, size: int = 10):
    """
    로컬 Elasticsearch에서 본문 검색 (BM25 점수만 반환)
    """
    es = get_es_client()
    index_name = text_index_sort(year_list)
    keywords = extract_keywords(query)
    if index_name == "text_data":
        start_date, end_date = extract_date_from_query(query)
    elif index_name == "text_data_2025":
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

### 보고서로 쓸 예정이니 지우지 말 것 ###
###############################################################################################################
# def search_image_es(query: str, year_list: list, size: int = 10):
#     """
#     로컬 Elasticsearch에서 이미지 검색, 보고서로 쓸 예정이니 지우지 말 것
#     """
#     es = get_es_client()
#     index_name = image_index_sort(year_list)
#     keywords = extract_keywords(query)
#     start_date, end_date = extract_date_with_day_from_query(query)

#     filter_conditions = []
#     if start_date and end_date:
#         filter_conditions.append({"range": {"metadata.date": {"gte": start_date, "lte": end_date}}})

#     es_query = {
#         "query": {
#             "bool": {
#                 "must": [
#                     {"match": {"image_summary": {"query": " ".join(keywords), "operator": "or"}}}
#                 ],
#                 "filter": filter_conditions
#             }
#         }
#     }

#     try:
#         response = es.search(index=index_name, body=es_query, size=size)
#         hits = response.get("hits", {}).get("hits", [])

#         return hits if hits else [{
#             "_index": f"{index_name}",
#             "_id": "-1",
#             "_score": 1e-6,
#             "_source": {
#                 "image_summary": "검색된 공지가 없습니다.",
#                 "img_base64": "공지가 없어요",
#                 "metadata": {
#                     "doc_name": "no_result",
#                     "date": "0000-00",
#                     "bundle": "not in bundle"
#                 }
#             }
#         }]
#     finally:
#         es.close()
###############################################################################################################

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

# def search_base64_by_bundle(bundle, size: int = 15):
#     """
#     로컬 Elasticsearch에서 bundle을 이용해 같은 공지의 이미지를 검색
#     """
#     index_name = "image_data_2025"

#     # 로컬 Elasticsearch 클라이언트 연결
#     es = get_es_client() 

#     es_query = {
#         "query": {
#             "term": {
#                 "metadata.bundle": bundle  # 정확한 UUID 일치 검색
#             }
#         }
#     }

#     try:
#         response = es.search(index=index_name, body=es_query, size=size)

#         hits = response.get("hits", {}).get("hits", [])

#         # img_base64 필드만 추출하여 반환
#         base64_results = [
#             hit["_source"]["img_base64"]
#             for hit in hits
#             if "_source" in hit and "img_base64" in hit["_source"]
#         ]

#         return base64_results if base64_results else [None]

#     except Exception as e:
#         return [{"error": f"❌ 검색 중 오류 발생: {str(e)}"}]

#     finally:
#         es.close()

def search_base64_by_bundle(bundle, size: int = 15):
    """
    로컬 Elasticsearch에서 같은 bundle을 가진 이미지 묶음을 검색
    """
    index_name = "image_data_2025"

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
os.environ["OPENAI_API_KEY"] = "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"
OPENAI_API_KEY = os.getenv("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")
embedding_dim=1536
openai_client = OpenAI()
def emb_text(text):
    return (
        openai_client.embeddings.create(input=text, model="text-embedding-3-small")
        .data[0]
        .embedding
    )

milvus_client = milvus_client = MilvusClient(uri="https://in03-0e20997fb5c4a00.serverless.gcp-us-west1.cloud.zilliz.com", token='6c5c4aca5950756003f5db05fa289b291aa796575bb9d2bd5ee3f41d6391be6237b3cab4c3c42b877b77409b4337e424d740b3b2')


def milvus_text_search(user_query,year):
    question = user_query
    if year=='2022-2024':
        collection_name = "txt_collection"
    elif year == '2025':
        collection_name="text_2025_collection"
    try:
        search_res = milvus_client.search(
        collection_name=collection_name,
        data=[
            emb_text(question)
        ],
        limit=10,
        #limit=5,
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
        collection_name="image_2025_collection"
    try:
        search_res = milvus_client.search(
        collection_name=collection_name,
        data=[
            emb_text(question)
        ],
        limit=10,
        #limit=5,
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
    
