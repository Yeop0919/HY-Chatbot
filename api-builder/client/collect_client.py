import requests
from pathlib import Path
# FastAPI 서버의 URL
url = "http://localhost:27500/rest/upload"

# 사용자 입력 받기
text = input("업로드할 텍스트를 입력하세요: ")
file_paths = input("업로드할 이미지 파일 경로들을 쉼표로 구분하여 입력하세요: ").split(',')

# 요청할 데이터 (텍스트 포함)
data = {"text": text}

# 파일을 리스트로 구성
files = []
open_files = []

try:
    for file_path in file_paths:
        file_path = file_path.strip()
        try:
            file = open(file_path, "rb")  # 파일 열기
            open_files.append(file)  # 나중에 닫기 위해 리스트에 추가
            files.append(("files", (Path(file_path).name, file, "image/jpeg")))  # 클라이언트에서 파일명만 전송
        except FileNotFoundError:
            print(f"파일을 찾을 수 없습니다: {file_path}")
            continue

    # POST 요청 보내기 (multipart/form-data)
    response = requests.post(url, files=files, data=data)

    # 응답 확인
    if response.status_code == 200:
        print("업로드 성공:", response.json())
    else:
        print("업로드 실패:", response.status_code, response.text)

finally:
    # 열린 파일 닫기
    for f in open_files:
        f.close()
