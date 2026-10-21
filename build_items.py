"""항목 메타데이터를 items 컬렉션에 색인한다. (F2001, F2002)

실행: python build_items.py
청크 ID가 항목 id라서 다시 실행해도 덮어쓰기만 일어난다.
"""
from datetime import date

from langchain_core.documents import Document

from data_prep.initializr import item_text, load_items
from vector_store.store import get_collection


def main():
    items = load_items()
    docs = [
        Document(
            page_content=item_text(i),
            metadata={
                "item_id": i["id"], "name": i["name"], "group": i["group"],
                "doc_url": i["doc_url"], "source": "initializr",
                "collected_at": date.today().isoformat(),
            },
        )
        for i in items
    ]
    col = get_collection("items")
    col.add_documents(docs, ids=[i["id"] for i in items])
    print(f"로드한 항목 {len(items)}건, 색인된 청크 {col._collection.count()}건")


if __name__ == "__main__":
    main()
