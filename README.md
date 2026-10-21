# 버전 인지형 Spring Boot 문서 Q&A

Spring Initializr 의존성 항목과 Spring Boot 버전을 고르면, 그 버전의 공식 문서를 근거로 답하고 근거 문서를 함께 보여주는 RAG 서비스.

- 요구사항: [docs/requirements.md](docs/requirements.md)
- 설계: [docs/rag-design.md](docs/rag-design.md)

## 구조
| 경로 | 책임 |
|---|---|
| `server.py` | FastAPI 서버 (API + 화면 제공) |
| `web/` | HTML·CSS·JS 화면 |
| `scripts/` | 배치: `build_items`(항목 색인), `fetch_docs`(문서 원문 수집) |
| `data_prep/` | 외부 출처: Initializr 항목, spring-boot 문서 |
| `vector_store/` | ChromaDB 컬렉션, 청킹 |
| `rag/`, `services/` | RAG 흐름, 특화 기능 (작성 중) |

## 실행
```
copy .env.example .env     # GMS_KEY 입력
pip install -r requirements.txt
python -m scripts.build_items   # 항목 204건 색인
python -m scripts.fetch_docs    # 문서 원문 수집 (첫 실행 약 10분)
uvicorn server:app              # http://127.0.0.1:8000
```

## 데이터 출처와 이용 조건
docs/requirements.md 1.1 참고.
