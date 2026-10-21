"""지원 버전의 spring-boot 문서 원문을 로컬에 받는다. (F2004 데이터 구축)

실행: python -m scripts.fetch_docs
이미 받은 파일은 건너뛴다. 버전당 약 2~3분 (호출 간격 1초).
"""
from data_prep.boot_docs import VERSIONS, download, load_docs


def main():
    for version in VERSIONS:
        fetched = download(version)
        print(f"{version}: 새로 받은 문서 {fetched}건, 보관 문서 {len(load_docs(version))}건")


if __name__ == "__main__":
    main()
