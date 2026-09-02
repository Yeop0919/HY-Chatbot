# api-builder — 하이챗봇 백엔드

하이챗봇의 검색/답변 파이프라인을 서빙하는 FastAPI 백엔드입니다. 전체 프로젝트 설명은 [루트 README](../README.md)를 참고하세요.

이 디렉터리의 기본 골격(설정 관리, 로깅, 에러 핸들링, Gunicorn/uv 세팅 등)은 Wisenut의 Python FastAPI Template을 기반으로 시작했습니다 (`LICENSE` 참고, 비상업적 사용 허용). 검색·색인·답변 생성 로직(`app/utils/`, `app/api/routers/rest.py`)은 이 프로젝트에서 직접 구현했습니다.

## 실행

```bash
uv sync
cp .env.example .env   # OpenAI / Zilliz / Elasticsearch 값 채우기
uv run uvicorn app.main:app --host 0.0.0.0 --port 27500
```

실행 후 `/docs`에서 Swagger UI로 API 명세를 확인할 수 있습니다.

## 주요 엔드포인트 (`/rest`)

| 엔드포인트 | 설명 |
|---|---|
| `POST /rest/llm_answer` | 사용자 질문을 받아 하이브리드 검색 → 재랭킹 → GPT-4o 답변 생성까지 수행 |
| `POST /rest/upload` | 공지 원본(텍스트+이미지)을 서버에 임시 저장 |
| `POST /rest/emb` | 저장된 공지 원본을 전처리·임베딩해 Milvus/Elasticsearch에 색인 |

모든 `/rest` 엔드포인트는 `Authorization` 헤더의 API 키(`ELASTIC_API_KEY` 환경변수와 대조)로 인증합니다.

## 디렉터리

```
app/
  api/routers/rest.py   API 엔드포인트
  utils/ela.py           Elasticsearch + Milvus 검색
  utils/hybrid.py         하이브리드 점수 결합
  utils/reranking.py      재랭킹 (ko-reranker)
  utils/qa.py              GPT-4o 멀티모달 답변 생성
  utils/collection.py     공지 원본 수집/전처리/임베딩/색인
  config.py                환경설정
client/
  client.py               터미널에서 /rest/llm_answer 테스트
  collect_client.py       터미널에서 /rest/upload 테스트
```
