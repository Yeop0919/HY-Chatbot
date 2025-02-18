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

### Elasticsearch 연결 체크
def check_elasticsearch_connection():
    """Elasticsearch 연결 상태 확인 (_cluster/health 호출)"""
    auth = (settings.ELASTIC_USERNAME, settings.ELASTIC_PASSWORD)  # ID/PW 인증

    try:
        response = requests.get(
            f"{settings.ELASTIC_CLOUD_URL}/_cluster/health",  # 클러스터 상태 확인 API
            auth=auth,  # ID/PW 인증 추가
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Elasticsearch 연결 성공! 상태: {data['status']}")
            return {"status": "connected", "cluster_status": data["status"], "message": "Elasticsearch 연결 성공!"}
        else:
            print(f"❌ Elasticsearch 연결 실패: {response.status_code} - {response.text}")
            return {"status": "failed", "error": f"연결 실패: {response.status_code} - {response.text}"}

    except Exception as e:
        print(f"❌ Elasticsearch 요청 오류: {str(e)}")
        return {"status": "error", "error": f"Elasticsearch 요청 오류: {str(e)}"}

check_elasticsearch_connection()

komoran = Komoran()
def extract_keywords(query: str):
    """
    한국어 문장에서 주요 키워드 추출 (명사, 동사, 형용사)
    """
    stopwords = {'것', '하다', '되다', '있다', '없다', '이다', '그', '수', '이', '저'}  # 불필요한 단어 목록
    keywords = []

    for word, pos in komoran.pos(query):
        if pos in ["NNG", "NNP", "VV", "VA"]:  # 일반 명사, 고유 명사, 동사, 형용사
            word = word.strip()
            if word not in stopwords:  # 불필요한 단어 제거
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

### 날짜 추출 함수 (이미지)
def img_extract_date_from_query(query: str):
    """
    자연어 쿼리에서 날짜(YYYY-MM-DD 또는 YYYY-MM 또는 YYYY년 형태)를 추출하는 함수
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

### Elasticsearch 클라이언트 생성
def get_es_client():
    """ 새로운 Elasticsearch 클라이언트 생성 (API Key 인증) """
    headers = {
        "Authorization": f"ApiKey {settings.ELASTIC_API_KEY}",
        "X-Token": settings.X_TOKEN
    }

    return {
        "url": f"{settings.ELASTIC_CLOUD_URL}",
        "headers": headers
    }


def search_text_es(query: str, size: int = 5):
    """ Elasticsearch에서 본문만 검색하고 BM25 점수만 반환 """
    index_name = "text_data"
    es_client = get_es_client()
    keywords = extract_keywords(query)
    start_date, end_date = extract_date_from_query(query)

    # 필터 조건 (날짜 범위 필터 적용)
    filter_conditions = []
    if start_date and end_date:
        filter_conditions.append({"range": {"metadata.date": {"gte": start_date, "lte": end_date}}})

    es_query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "page_content": {
                                "query": " ".join(keywords),
                                "operator": "or"
                            }
                        }
                    }
                ],
                "filter": filter_conditions if filter_conditions else []  
            }
        }
    }

    try:
        response = requests.get(
            f"{es_client['url']}/{index_name}/_search",
            headers=es_client["headers"],
            json=es_query, 
            params={"size": size},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            hits = result.get("hits", {}).get("hits", [])

            return hits if hits else [{"error": "❌ 검색 결과가 없습니다."}]

        else:
            return [{"error": f"❌ 검색 실패: {response.status_code} - {response.text}"}]

    except Exception as e:
        return [{"error": f"❌ 검색 중 오류 발생: {str(e)}"}]




def search_image_es(query: str, size: int = 5, return_field: str = "image_summary"):
    index_name = "image_data"
    es_client = get_es_client()
    keywords = extract_keywords(query)
    start_date, end_date = img_extract_date_from_query(query)

    filter_conditions = []
    if start_date and end_date:
        filter_conditions.append({"range": {"metadata.date": {"gte": start_date, "lte": end_date}}})

    es_query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "image_summary": {
                                "query": " ".join(keywords),
                                "operator": "or"
                            }
                        }
                    }
                ],
                "filter": filter_conditions if filter_conditions else [] 
            }
        }
    }

    try:
        response = requests.get(
            f"{es_client['url']}/{index_name}/_search",
            headers=es_client["headers"],
            json=es_query,
            params={"size": size},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            hits = result.get("hits", {}).get("hits", [])

            # # `img_base64` 필드만 제거하여 반환
            # for hit in hits:
            #     if "_source" in hit and "img_base64" in hit["_source"]:
            #         del hit["_source"]["img_base64"]

            return hits

        else:
            return [{"error": f"❌ 검색 실패: {response.status_code} - {response.text}"}]

    except Exception as e:
        return [{"error": f"❌ 검색 중 오류 발생: {str(e)}"}]
# elastic 클라우드에서 원하는 doc id의 base64 가져오기기
def search_base64(query: str, size: int = 1):
    """
    Elasticsearch에서 이미지의 Base64 데이터만 검색하고 반환
    """
    index_name = "image_data"
    es_client = get_es_client()
    keywords = extract_keywords(query)

    es_query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "_id": {
                                "query": " ".join(keywords)
                            }
                        }
                    }
                ],
            }
        }
    }

    try:
        response = requests.get(
            f"{es_client['url']}/{index_name}/_search",
            headers=es_client["headers"],
            json=es_query,
            params={"size": size},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            hits = result.get("hits", {}).get("hits", [])

            # `img_base64` 필드만 추출하여 반환
            base64_results = [
                {"img_base64": hit["_source"]["img_base64"]}
                for hit in hits
                if "_source" in hit and "img_base64" in hit["_source"]
            ]

            return base64_results

        else:
            return [{"error": f"❌ 검색 실패: {response.status_code} - {response.text}"}]

    except Exception as e:
        return [{"error": f"❌ 검색 중 오류 발생: {str(e)}"}]

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


def milvus_text_search(user_query):
    question = user_query
    collection_name = "txt_collection"
    try:
        search_res = milvus_client.search(
        collection_name=collection_name,
        data=[
            emb_text(question)
        ],
        limit=10,
        search_params={"metric_type": "IP", "params": {}},  # Inner product distance
        output_fields=["text"],
        )
        dense_results = [
        {"id": result["id"], "text": result["entity"].get("text"), "distance": result["distance"]}
        for result in search_res[0]
        ]


        if not dense_results:
            return print("\n❌ [DEBUG] 검색 결과 없음")

        else:
            return dense_results
    except Exception as e:
        return print(f"\n❌ [DEBUG] 검색 중 오류 발생: {e}")  
    
def milvus_image_search(user_query):
    question = user_query
    collection_name = "img_collection"
    try:
        search_res = milvus_client.search(
        collection_name=collection_name,
        data=[
            emb_text(question)
        ],
        limit=10,
        search_params={"metric_type": "IP", "params": {}},  # Inner product distance
        output_fields=["img_summary"],
        )
        dense_results = [
        {"id": result["id"], "img_summary": result["entity"].get("img_summary"), "distance": result["distance"]}
        for result in search_res[0]
        ]

        if not dense_results:
            return print("\n❌ [DEBUG] 검색 결과 없음")

        else:
            return dense_results
    except Exception as e:
        return print(f"\n❌ [DEBUG] 검색 중 오류 발생: {e}")  
    
