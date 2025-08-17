# Para indexar nuestro excel en un índice de Azure AI Search
import pandas as pd
import json, argparse, io, requests
from typing import List, Dict
from backend.config import settings
from search_client import make_search_client
from backend.providers.gemini_provider import get_gemini_client

def embed(texts: List[str]) -> List[List[float]]:
    genai = get_gemini_client()
    vecs = []
    for t in texts:
        e = genai.embed_content(model=settings.GEMINI_EMBED_MODEL, content=str(t))
        vecs.append(e["embedding"]["values"])
    return vecs

def load_excel(path_or_sas: str) -> pd.DataFrame:
    if path_or_sas.lower().startswith("http"):
        data = requests.get(path_or_sas, timeout=60).content
        return pd.read_excel(io.BytesIO(data))
    return pd.read_excel(path_or_sas)

def chunk(text: str, max_words=180, overlap=40) -> List[str]:
    words = str(text).split()
    chunks, i = [], 0
    while i < len(words):
        j = min(len(words), i + max_words)
        chunks.append(" ".join(words[i:j]))
        i = j - overlap if j - overlap > i else j
    return chunks

def prepare_docs(df: pd.DataFrame, text_col: str, title_col: str | None,
                 source_col: str | None, date_col: str | None,
                 jurisdiction_col: str | None, year_col: str | None) -> List[Dict]:
    docs = []
    for i, row in df.iterrows():
        title = (str(row[title_col]) if title_col and pd.notna(row[title_col]) else None)
        source = (str(row[source_col]) if source_col and pd.notna(row[source_col]) else None)
        date   = (str(row[date_col]) if date_col and pd.notna(row[date_col]) else None)
        jur    = (str(row[jurisdiction_col]) if jurisdiction_col and pd.notna(row[jurisdiction_col]) else None)
        year   = int(row[year_col]) if year_col and pd.notna(row[year_col]) else None

        chunks = chunk(row[text_col])
        for j, c in enumerate(chunks):
            docs.append({
                "id": f"{i}-{j}",
                "title": title,
                "content": c,
                "source": source,
                "date": date,
                "jurisdiction": jur,
                "year": year
            })
    return docs

def upload_docs(docs: List[Dict]):
    client = make_search_client()
    batch = 32
    for i in range(0, len(docs), batch):
        page = docs[i:i+batch]
        vecs = embed([d["content"] for d in page])
        for d, v in zip(page, vecs):
            d["content_vector"] = v
        client.upload_documents(page)
        print(f"Uploaded {i + len(page)}/{len(docs)}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--path", required=True, help="Excel path or Blob SAS URL")
    p.add_argument("--text-col", required=True)
    p.add_argument("--title-col")
    p.add_argument("--source-col")
    p.add_argument("--date-col")
    p.add_argument("--jurisdiction-col")
    p.add_argument("--year-col")
    args = p.parse_args()

    df = load_excel(args.path)
    docs = prepare_docs(df, args.text_col, args.title_col, args.source_col,
                        args.date_col, args.jurisdiction_col, args.year_col)
    upload_docs(docs)
