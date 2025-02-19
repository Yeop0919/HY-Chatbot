from fastapi import APIRouter, Query, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List
from app.dependencies import get_current_user 
from app.utils.ela import search_text_es, search_image_es, milvus_text_search, milvus_image_search
from app.utils.hybrid import tmm_norm_elastic,tmm_norm_milvus, txt_hybrid_search, img_hybrid_search
from app.utils.reranking import txt_reranking, img_reranking
from app.utils.qa import llm_answer
# FastAPI APIRouter 생성
router = APIRouter(
    prefix="/rest",
    tags=["rest"],
    dependencies=[Depends(get_current_user)],
)


# API 모델 정의
class LLMRequest(BaseModel):
    user_query: str

class ChatResponse(BaseModel):
    llm_answer: str

@router.post("/llm_answer", summary="검색 수행 후 답변", description="사용자의 입력을 받아 공지사항 및 이미지 검색 후 llm으로 최종답변 생성")
async def post_search_results(request: LLMRequest):
    """
    🔹 사용자의 입력을 받아 검색을 수행하는 POST 요청
    - Elasticsearch 및 Milvus에서 텍스트 및 이미지 검색 수행
    - Hybrid Search 및 Reranking 적용 후 결과 반환
    - llm을 통한 최종답변 생성
    """
    user_query = request.user_query  # JSON 본문에서 동적으로 user_query 추출
    print(f"\n✅ [DEBUG] 검색 요청: {user_query}")  # 디버깅 로그 추가

    try:
        # 검색 수행
        elastic_keyword_results = search_text_es(user_query)
        elastic_txt_results = tmm_norm_elastic(elastic_keyword_results)
        elastic_image_results = search_image_es(user_query)
        elastic_img_results = tmm_norm_elastic(elastic_image_results)
        milvus_text_results = milvus_text_search(user_query)
        milvus_txt_results = tmm_norm_milvus(milvus_text_results)
        milvus_image_results = milvus_image_search(user_query)
        milvus_img_results = tmm_norm_milvus(milvus_image_results)

        # Hybrid Search & Re-ranking 적용
        text_initial_result = txt_hybrid_search(milvus_txt_results, elastic_txt_results, 0.7, 0.3)
        image_initial_result = img_hybrid_search(milvus_img_results, elastic_img_results, 0.7, 0.3)
        text_reranked_result = txt_reranking(user_query, text_initial_result)
        image_reranked_result = img_reranking(user_query, image_initial_result)
        llm_text_answer= llm_answer(user_query,text_reranked_result, image_reranked_result)

        # 검색 결과 없을 때 예외 처리
        if not elastic_keyword_results and not elastic_image_results:
            print("\n❌ [DEBUG] 검색 결과 없음")  # 추가 로그
            raise HTTPException(status_code=404, detail="검색 결과가 없습니다.")

        print("\n✅ [DEBUG] 검색 성공")  # 성공 로그
        return {
            "llm_text_answer":llm_text_answer
        }

    except Exception as e:
        print(f"\n❌ [ERROR] 검색 중 오류 발생: {str(e)}")  # 오류 로그
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")
    
    # combine_results(keyword_results, )









