from fastapi import APIRouter, Query, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List
from app.dependencies import get_current_user 
from app.utils.ela import search_text_es, search_image_es, milvus_text_search, milvus_image_search,tmm_norm_elastic,tmm_norm_milvus,txt_hybrid_search, img_hybrid_search

# FastAPI APIRouter 생성
router = APIRouter(
    prefix="/rest",
    tags=["rest"],
    dependencies=[Depends(get_current_user)],
)


# API 모델 정의
class ChatRequest(BaseModel):
    user_input: str  # 사용자의 질문

class ChatResponse(BaseModel):
    final_response_text: List[dict]  
    final_response_image: List[dict] 

@router.get("/search", response_model=ChatResponse, summary="공지 검색", description="사용자의 입력을 받아 공지사항 및 이미지 검색")
async def get_search_results(user_query: str = Query(..., description="사용자가 입력한 검색 쿼리")):
    print(f"\n✅ [DEBUG] get_search_results 실행됨 - 검색어: {user_query}")  # 추가

    try:
        elastic_keyword_results = search_text_es(user_query)
        elastic_txt_results=tmm_norm_elastic(elastic_keyword_results)
        elastic_image_results = search_image_es(user_query)
        elastic_img_results=tmm_norm_elastic(elastic_image_results)
        milvus_text_results = milvus_text_search(user_query)
        milvus_txt_results=tmm_norm_milvus(milvus_text_results)
        milvus_image_results = milvus_image_search(user_query)
        milvus_img_results=tmm_norm_milvus(milvus_image_results)
        text_final_result=txt_hybrid_search(milvus_txt_results, elastic_txt_results, 0.7, 0.3)
        image_final_result=img_hybrid_search(milvus_img_results, elastic_img_results, 0.7, 0.3)

        if not elastic_keyword_results and not elastic_image_results:
            print("\n❌ [DEBUG] 검색 결과 없음")  # 추가
            raise HTTPException(status_code=404, detail="검색 결과가 없습니다.")

        print("\n✅ [DEBUG] 검색 성공")  # 추가
        return ChatResponse(final_response_text=text_final_result,
                            final_response_image=image_final_result,
                            )

    except Exception as e:
        print(f"\n❌ [DEBUG] 검색 중 오류 발생: {e}")  # 추가
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")
    
    # combine_results(keyword_results, )









