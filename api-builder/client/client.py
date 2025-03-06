import requests

# 1️⃣ 검색 요청 (POST /search)
query = input("검색어를 입력하세요: ") 
search_url = "http://localhost:27500/rest/llm_answer"
search_data = {"user_query": query}
search_response = requests.post(search_url, json=search_data)

if search_response.status_code == 200:
    search_result = search_response.json()


    print("\n🤖 LLM 응답:", search_result["llm_text_answer"])  # LLM 응답 출력

else:
    print("\n❌ 검색 실패:", search_response.status_code, search_response.text)