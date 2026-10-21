# 버전 인지형 Spring Boot 문서 Q&A

Spring Initializr 의존성 항목과 Spring Boot 버전을 고르면, 그 버전의 공식 문서를 근거로 답하고 근거 문서를 함께 보여주는 RAG 서비스.

- 요구사항: [docs/requirements.md](docs/requirements.md)
- 설계: [docs/rag-design.md](docs/rag-design.md)

## 구조 (예정)
data_prep / vector_store / rag / services / app.py (Streamlit)

## 실행 (예정)
```
copy .env.example .env     # GMS_KEY 입력
pip install -r requirements.txt
streamlit run app.py
```

## 데이터 출처와 이용 조건
docs/requirements.md 1.1 참고.
