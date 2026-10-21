"""LLM 프롬프트. 1: 검색어 추출(F2003), 2: 후보 문서 선별(F2004). 3(답변 생성)은 F2007에서 추가."""

SEARCH_TERMS = """너는 Spring 기술 문서 전문가다. 질문에 답하려면 Spring Boot 공식 문서에서 어떤 말로 찾아야 하는지 정한다.

[항목] {name}: {description}
[Spring Boot 버전] {version}
[질문] {question}

규칙:
- 공식 문서는 영어다. 질문이 한국어여도 검색어는 영어 소문자 단어나 짧은 구(1~3단어)로 쓴다.
- 클래스 이름, 설정 속성 접두사(예: spring.kafka), 기술 이름처럼 문서 본문에 그대로 나올 말을 고른다.
- 3~6개를 고른다. spring, boot, configuration처럼 모든 문서에 나오는 말은 빼라.
- JSON 문자열 배열만 출력한다. 다른 글은 쓰지 않는다."""

SELECT_DOCS = """너는 Spring 기술 문서 전문가다. 질문에 답하는 데 필요한 Spring Boot {version} 공식 문서를 고른다.

[항목] {name}
[질문] {question}

[후보 문서]
{candidates}

규칙:
- 질문의 답이 들어 있을 문서만 최대 {max_docs}개 고른다. 관련 있는 문서가 없으면 빈 배열.
- 고른 문서 번호의 JSON 정수 배열만 출력한다. 예: [2, 5]"""
