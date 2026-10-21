"""ChromaDB 컬렉션 생성·조회. 컬렉션은 items(항목 메타데이터)와 docs(외부 문서) 두 개."""
import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from config import CONFIG, ROOT

load_dotenv()


def get_collection(name: str) -> Chroma:
    key = os.environ.get("GMS_KEY")
    if not key:
        raise RuntimeError("GMS_KEY가 없습니다. .env를 확인하세요.")
    embeddings = OpenAIEmbeddings(
        model=CONFIG["models"]["embedding"],
        api_key=key,
        base_url=CONFIG["models"]["base_url"],
        check_embedding_ctx_length=False,  # tiktoken 다운로드 없이 GMS 프록시로 그대로 전송
    )
    return Chroma(
        collection_name=name,
        embedding_function=embeddings,
        persist_directory=str(ROOT / CONFIG["paths"]["chroma_dir"]),
    )
