"""지원 버전의 spring-boot 문서와 외부 문서(springdoc 등) 원문을 로컬에 받는다. (F2004 데이터 구축)

실행: python -m scripts.fetch_docs
이미 받은 파일은 건너뛴다. 버전당 약 2~3분 (호출 간격 1초).
"""
from data_prep import external_docs
from data_prep.boot_docs import VERSIONS, download, load_docs


def main():
    for version in VERSIONS:
        fetched = download(version)
        print(f"{version}: 새로 받은 문서 {fetched}건, 보관 문서 {len(load_docs(version))}건")
    for source in external_docs.SOURCES:
        fetched = external_docs.download(source)
        counts = {v: len(external_docs.load(source, v)) for v in VERSIONS}
        print(f"{source}: 새로 받은 파일 {fetched}건, 버전별 문서 {counts}")


if __name__ == "__main__":
    main()
