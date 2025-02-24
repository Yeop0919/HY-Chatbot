from fastapi import APIRouter, Query, HTTPException, Request, Depends, File, Form, UploadFile
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

#@router.post("/collection", summary="데이터 수집 모듈", description="서버에 임시 저장된 공지 데이터들을 수집하여 정제 후 데이터베이스에 업로드")
#async def collect_data(request: LLMRequest):
    """
    🔹 사용자의 입력을 받아 검색을 수행하는 POST 요청
    - Elasticsearch 및 Milvus에서 텍스트 및 이미지 검색 수행
    - Hybrid Search 및 Reranking 적용 후 결과 반환
    - llm을 통한 최종답변 생성
    """

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
    
    #combine_results(keyword_results, )


from pathlib import Path
import uuid
import shutil

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from pathlib import Path
import shutil
import uuid
import json

@router.get("/", response_class=HTMLResponse)
async def upload_form():
    return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>이미지 및 텍스트 업로드</title>
</head>
<body>
    <h2>이미지 및 텍스트 업로드</h2>
    <form id="upload-form">
        <label for="title">텍스트 입력:</label>
        <textarea name="title" id="title" rows="4" cols="50" required></textarea><br><br>

        <!-- 날짜 필드 추가 -->
        <label for="date">날짜 입력 (YYYY-MM-DD):</label>
        <input type="text" id="date" placeholder="2025-02-24" required><br><br>

        <label for="file-input">이미지 업로드:</label>
        <input type="file" id="file-input" multiple required><br><br>

        <button type="button" class="submit-btn">업로드</button>
    </form>

    <h3>서버 응답:</h3>
    <pre id="response-message"></pre>

    <script>
        document.querySelector(".submit-btn").addEventListener("click", function () {
            const title = document.getElementById("title").value.trim();
            const dateValue = document.getElementById("date").value.trim();
            const fileInput = document.getElementById("file-input");

            // 유효성 검사
            if (!title || !dateValue || fileInput.files.length === 0) {
                alert("텍스트, 날짜, 그리고 파일을 모두 입력해야 합니다.");
                return;
            }

            // FormData 구성
            let formData = new FormData();
            formData.append("title", title);
            formData.append("date", dateValue);

            for (let i = 0; i < fileInput.files.length; i++) {
                formData.append("files", fileInput.files[i]);
            }

            // 서버에 POST 요청
            fetch("http://localhost:27500/rest/upload", {
                method: "POST",
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById("response-message").textContent = JSON.stringify(data, null, 2);
                alert("텍스트, 날짜, 그리고 파일이 서버에 저장되었습니다!");
            })
            .catch(error => {
                console.error("Error:", error);
                alert("오류 발생: 저장에 실패했습니다.");
            });
        });
    </script>
</body>
</html>
"""

# 파일 업로드 처리
@router.post("/upload")
async def upload_file(
    title: str = Form(...),
    date: str = Form(...),            # 날짜 추가
    files: list[UploadFile] = File(...)
):
    """ 업로드된 텍스트와 파일을 서버에 저장 + 날짜 정보를 JSON으로 저장 """
    
    BASE_SAVE_DIRECTORY = Path("/root/.vscode-server/chatbot_project/notice_db")
    BASE_SAVE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    
    unique_folder_name = str(uuid.uuid4())  # 각 업로드마다 고유한 폴더 생성
    save_directory = BASE_SAVE_DIRECTORY / unique_folder_name
    save_directory.mkdir(parents=True, exist_ok=True)

    image_folder = save_directory / "images"
    image_folder.mkdir(parents=True, exist_ok=True)

    # 1. 이미지 저장
    file_locations = []
    for file in files:
        filename = Path(file.filename).name
        file_location = image_folder / filename

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_locations.append(str(file_location))

    # 2. 텍스트(title) 저장
    text_filename = save_directory / f"{unique_folder_name}.txt"
    with open(text_filename, "w", encoding="utf-8") as text_file:
        text_file.write(title)

    # 3. 날짜(date) 정보를 JSON 파일로 저장
    json_filename = save_directory / f"{unique_folder_name}.json"
    data = {
        "date": date
    }
    with open(json_filename, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    return {
        "message": "Files, text and date saved successfully",
        "file_locations": file_locations,
        "text_location": str(text_filename),
        "json_location": str(json_filename)
    }




