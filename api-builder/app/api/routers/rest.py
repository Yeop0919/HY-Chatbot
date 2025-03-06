from fastapi import APIRouter, Query, HTTPException, Request, Depends, File, Form, UploadFile
from pydantic import BaseModel
from typing import List
from app.dependencies import get_current_user 
from app.utils.ela import search_text_es, search_image_es, milvus_text_search, milvus_image_search
from app.utils.hybrid import tmm_norm_elastic,tmm_norm_milvus, txt_hybrid_search, img_hybrid_search
from app.utils.reranking import txt_reranking, img_reranking
from app.utils.qa import llm_answer
import time
# FastAPI APIRouter 생성
router = APIRouter(
    prefix="/rest",
    tags=["rest"],
    dependencies=[Depends(get_current_user)],
)


# API 모델 정의
class LLMRequest(BaseModel):
    user_query: str
    selected_year: str

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
    year = request.selected_year
    print(f"\n✅ [DEBUG] 검색 요청: {user_query}")  # 디버깅 로그 추가

    elapsed_time = []  # 각 단계의 시간 기록을 위한 리스트

    try:
        # 시작 시간 기록
        start_time = time.time()

        # 검색 수행 - Elasticsearch 관련
        elastic_start_time = time.time()
        elastic_keyword_results = search_text_es(user_query, [year])
        elastic_end_time = time.time()
        elapsed_time.append(f"Elasticsearch 텍스트 검색 시간: {elastic_end_time - elastic_start_time:.4f}초")

        elastic_txt_results = tmm_norm_elastic(elastic_keyword_results)

        elastic_image_start_time = time.time()
        elastic_image_results = search_image_es(user_query, [year])
        elastic_image_end_time = time.time()
        elapsed_time.append(f"Elasticsearch 이미지 검색 시간: {elastic_image_end_time - elastic_image_start_time:.4f}초")

        elastic_img_results = tmm_norm_elastic(elastic_image_results)

        # Milvus 관련
        milvus_text_start_time = time.time()
        milvus_text_results = milvus_text_search(user_query, year)
        milvus_text_end_time = time.time()
        elapsed_time.append(f"Milvus 텍스트 검색 시간: {milvus_text_end_time - milvus_text_start_time:.4f}초")

        milvus_txt_results = tmm_norm_milvus(milvus_text_results)

        milvus_image_start_time = time.time()
        milvus_image_results = milvus_image_search(user_query, year)
        milvus_image_end_time = time.time()
        elapsed_time.append(f"Milvus 이미지 검색 시간: {milvus_image_end_time - milvus_image_start_time:.4f}초")

        milvus_img_results = tmm_norm_milvus(milvus_image_results)

        # Hybrid Search & Re-ranking 적용
        text_initial_start_time = time.time()
        text_initial_result = txt_hybrid_search(milvus_txt_results, elastic_txt_results, 0.7, 0.3)
        text_initial_end_time = time.time()
        elapsed_time.append(f"텍스트 Hybrid Search 시간: {text_initial_end_time - text_initial_start_time:.4f}초")

        image_initial_start_time = time.time()
        image_initial_result = img_hybrid_search(milvus_img_results, elastic_img_results, 0.7, 0.3)
        image_initial_end_time = time.time()
        elapsed_time.append(f"이미지 Hybrid Search 시간: {image_initial_end_time - image_initial_start_time:.4f}초")

        # Reranking
        text_reranked_start_time = time.time()
        text_reranked_result = txt_reranking(user_query, text_initial_result)
        text_reranked_end_time = time.time()
        elapsed_time.append(f"텍스트 Re-ranking 시간: {text_reranked_end_time - text_reranked_start_time:.4f}초")

        image_reranked_start_time = time.time()
        image_reranked_result = img_reranking(user_query, image_initial_result)
        image_reranked_end_time = time.time()
        elapsed_time.append(f"이미지 Re-ranking 시간: {image_reranked_end_time - image_reranked_start_time:.4f}초")

        # LLM 답변 생성
        llm_start_time = time.time()
        llm_text_answer = llm_answer(user_query, text_reranked_result, image_reranked_result)
        llm_end_time = time.time()
        elapsed_time.append(f"LLM 답변 생성 시간: {llm_end_time - llm_start_time:.4f}초")

        # 검색 결과 없을 때 예외 처리
        if not elastic_keyword_results and not elastic_image_results:
            print("\n❌ [DEBUG] 검색 결과 없음")  # 추가 로그
            raise HTTPException(status_code=404, detail="검색 결과가 없습니다.")

        # 전체 처리 시간
        end_time = time.time()
        elapsed_time.append(f"전체 처리 시간: {end_time - start_time:.4f}초")

        # 마지막에 일괄로 출력
        print("\n✅ [DEBUG] 검색 성공")  # 성공 로그
        for time_log in elapsed_time:
            print(time_log)  # 각 단계별 소요 시간 출력

        return {
            "llm_text_answer": llm_text_answer
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
from typing import Optional
from datetime import datetime

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

@router.post("/upload")
async def upload_file(
    title: str = Form(""),  
    date: str = Form(...),  
    files: Optional[list[UploadFile]] = File(None)  # ✅ None을 허용하도록 수정
):
    """ 업로드된 텍스트와 파일을 서버에 저장 + 날짜 정보를 JSON으로 저장 """

    # ✅ 날짜 형식 검증
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    BASE_SAVE_DIRECTORY = Path("/root/.vscode-server/chatbot_project/notice_db")
    BASE_SAVE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    unique_folder_name = str(uuid.uuid4())  
    save_directory = BASE_SAVE_DIRECTORY / unique_folder_name
    save_directory.mkdir(parents=True, exist_ok=True)

    image_folder = save_directory / "images"
    image_folder.mkdir(parents=True, exist_ok=True)

    file_locations = []
    
    # ✅ 파일 저장 (파일이 있는 경우만 실행)
    if files:
        for file in files:
            if file.filename:  # 빈 파일 체크
                filename = Path(file.filename).name
                file_location = image_folder / filename

                with open(file_location, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                file_locations.append(str(file_location))

    # ✅ title이 있으면 저장
    if title:
        text_filename = save_directory / f"{unique_folder_name}.txt"
        with open(text_filename, "w", encoding="utf-8") as text_file:
            text_file.write(title)

    # ✅ JSON 데이터 저장
    json_filename = save_directory / f"{unique_folder_name}.json"
    data = {
        "date": date
    }

    with open(json_filename, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    return {
        "message": "Files, text and date saved successfully",
        "saved_data": data
    }



from fastapi.responses import JSONResponse
from app.utils.collection import text_chunking, generate_img_summaries, delete_directory
from app.utils.collection import milvus_upload_text, milvus_upload_image
from app.utils.collection import elastic_indexing_text, elastic_indexing_image

# 업로드된 파일 임베딩, 색인
@router.get("/emb")
async def emb_file():
    """
    입력된 경로로부터 파일을 처리하는 GET 요청
    """
    try:
        folder_path = "/root/.vscode-server/chatbot_project/notice_db"
        
        # 전처리
        chunked_text = text_chunking(folder_path)
        summarized_img = generate_img_summaries(folder_path)
        
        # milvus
        milvus_upload_text(chunked_text)
        milvus_upload_image(summarized_img)
        
        # elasticsearch
        elastic_indexing_text(chunked_text)
        elastic_indexing_image(summarized_img)
        
        delete_directory("/root/.vscode-server/chatbot_project/notice_db")
        
        return JSONResponse(content={"message": "파일 처리 성공"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오류 발생: {str(e)}")
    
        
