import requests

# 1️⃣ 검색 요청 (POST /search)
query = input("검색어를 입력하세요: ") 
search_url = "http://localhost:8070/rest/llm_answer"
search_data = {"user_query": query}
search_response = requests.post(search_url, json=search_data)

if search_response.status_code == 200:
    search_result = search_response.json()

    print("\n🔍 검색 결과:", search_result["final_response_text"])  # 검색된 텍스트 출력
    print("\n🖼️ 검색된 이미지:", search_result["final_response_image"])  # 검색된 이미지 출력
    print("\n🤖 LLM 응답:", search_result["llm_text_answer"])  # LLM 응답 출력

else:
    print("\n❌ 검색 실패:", search_response.status_code, search_response.text)