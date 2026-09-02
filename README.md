# 하이챗봇 (HY-Chatbot)

한양대학교 공지사항을 검색해서 답해주는 멀티모달 RAG 챗봇입니다. 텍스트 공지뿐 아니라 이미지로만 올라오는 공지(포스터, 카드뉴스 등)까지 이해하고 검색합니다.

한양대학교 캡스톤 프로젝트로 시작된 **팀 프로젝트**입니다. 이 저장소에서 제가 맡은 부분은 초기 데이터 수집 및 전처리 모듈, 임베딩 벡터 기반 검색(Milvus/Zilliz), 하이브리드 검색 설계, 멀티모달(이미지) 검색, 재랭킹, LLM 최종 답변 생성입니다. 키워드 검색 (Elasticsearch), 프론트엔드/UI 제작은 팀원과 함께 하였습니다

(주)와이즈넛에서 필요한 서버 및 자원을 제공받았습니다.

## 왜 하이브리드 검색인가

공지사항 검색은 키워드 검색만으로는 부족합니다. "이번 학기 장학금 신청 마감일"처럼 정확한 단어가 없어도 의미가 통해야 하고, 반대로 "컴퓨터소프트웨어학부 20학번"처럼 정확히 일치해야 하는 키워드도 있습니다. 그래서 두 검색 방식을 함께 씁니다.

```
사용자 질문
   │
   ├─► Elasticsearch (BM25 키워드 검색)      ─┐
   │     - 형태소 분석(Komoran)으로 키워드 추출 │
   │     - 날짜 필터링                        │
   │                                          ├─► 점수 정규화 + 가중합 (dense 0.7 : sparse 0.3)
   ├─► Milvus/Zilliz (벡터 의미 검색)         │        │
   │     - 텍스트: BGE-M3 로컬 임베딩          │        ▼
   │     - 이미지 요약: OpenAI 임베딩         ─┘   재랭킹 (ko-reranker)
   │                                                    │
   └────────────────────────────────────────────────────┴─► GPT-4o 멀티모달 답변 생성
                                                              (텍스트 + 이미지 컨텍스트)
```

1. **Elasticsearch**로 키워드(BM25) 기반 검색을 수행합니다. 한국어 형태소 분석으로 질문에서 키워드를 뽑고, 질문에 날짜가 포함되어 있으면 날짜로도 필터링합니다.
2. **Milvus(Zilliz Cloud)**로 의미 기반(dense vector) 검색을 함께 수행합니다. 텍스트는 로컬 임베딩 모델(BGE-M3), 이미지는 GPT-4o로 생성한 이미지 요약문을 OpenAI 임베딩으로 검색합니다.
3. 두 검색 결과 점수를 정규화한 뒤 가중합(dense 0.7 : sparse 0.3)으로 합쳐 1차 랭킹을 만들고, 한국어 특화 reranker(`ko-reranker`)로 다시 정렬합니다.
4. 최종적으로 검색된 텍스트/이미지를 컨텍스트로 GPT-4o에 넣어 답변을 생성합니다. 검색 결과가 없으면 재질문을 유도하는 후속 질문도 함께 생성합니다.

## 구조

```
api-builder/   FastAPI 백엔드 (검색 파이프라인, 데이터 수집/색인)
ui/            프런트엔드 (순수 HTML/CSS/JS, 프레임워크 없음)
```

- `api-builder/app/utils/ela.py` — Elasticsearch/Milvus 검색
- `api-builder/app/utils/hybrid.py` — 점수 정규화 및 하이브리드 결합
- `api-builder/app/utils/reranking.py` — 재랭킹
- `api-builder/app/utils/qa.py` — GPT-4o 멀티모달 답변 생성
- `api-builder/app/utils/collection.py` — 공지 원본 수집/전처리/임베딩/색인
- `api-builder/app/api/routers/rest.py` — API 엔드포인트

## 실행하려면

이 프로젝트는 OpenAI API, Zilliz Cloud, Elasticsearch에 의존하는 RAG 시스템이라 본인의 API 키/인프라 없이는 그대로 돌아가지 않습니다. 코드 구조와 파이프라인 설계를 참고하는 용도로 봐주세요.

```bash
cd api-builder
cp .env.example .env   # 값 채우기 (OpenAI, Zilliz, Elasticsearch)
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 27500
```

`ui/` 아래 HTML 파일들은 별도 빌드 없이 브라우저로 바로 열어보거나, 정적 파일 서버로 서빙하면 됩니다. 단, 백엔드 API 주소를 각 HTML 안의 `fetch()` 호출부에서 본인 서버 주소로 바꿔야 합니다.

## 알려진 제약

- 프로젝트를 실제로 서빙하던 서버는 현재 운영을 종료했습니다. Elasticsearch에 색인되어 있던 공지 데이터는 로컬(`127.0.0.1`)에서만 접근 가능했고 별도로 백업되어 있지 않아, 재현하려면 원본 공지 데이터를 다시 수집/색인해야 합니다.
- 관리자 로그인(`관리자화면.html`)은 프런트엔드 자바스크립트로만 비밀번호를 검증하는 데모 수준 구현입니다. 실제 서비스라면 서버 사이드 인증으로 교체가 필요합니다.

## 라이선스

`api-builder/`의 기본 프로젝트 골격은 Wisenut의 Python FastAPI Template(비상업적 사용 허용, `api-builder/LICENSE` 참고)을 기반으로 합니다. 검색 파이프라인, 하이브리드 서치, 재랭킹, 멀티모달 답변 생성, 프런트엔드 등 실제 챗봇 로직은 팀에서 직접 구현했습니다.
