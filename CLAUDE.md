# 프로젝트 요약
버전 인지형 Spring Boot 문서 Q&A (RAG). 명세: AI코어프로젝트_2회차_요구사항정의서.pdf (필수 F2001~F2012 수정 불가).
기획: docs/requirements.md, docs/rag-design.md

# 구조
data_prep(도메인 의존) / vector_store(ChromaDB, items·docs 컬렉션) / rag(LangGraph retrieve·generate) / services / app.py(Streamlit, 기존 골격을 이어 씀)
설정값(청크, Top-k, 검색 방식)은 config.toml.

# 규칙
- 코드 작성 전에 계획을 먼저 보여주고 확인받는다.
- 추측하지 않고 실제 저장소와 API를 직접 확인한다.
- 커밋 메시지, 코드 주석, 문서 어디에도 AI 작성 표기나 서명을 넣지 않는다.
- .env는 읽지 않는다 (키가 들어 있다).
- 외부 호출은 1초 이상 간격, 식별용 User-Agent를 붙인다.
- 임베딩 모델을 바꾸면 전체 재색인한다.
