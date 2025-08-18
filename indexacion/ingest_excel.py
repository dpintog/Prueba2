# Para indexar nuestro excel en un índice de Azure AI Search
import pandas as pd
import json, io, requests
from typing import List, Dict
from embedder import settings
from search_client import make_search_client
from azure.storage.blob import BlobServiceClient
import google.genai as genai

def embed(texts: List[str]) -> List[List[float]]:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    vecs = []
    for t in texts:
        # Using the correct API from google-genai documentation
        response = client.models.embed_content(
            model=settings.GEMINI_EMBED_MODEL,
            contents=str(t)  # The parameter is 'contents', not 'content' or 'input'
        )
        vecs.append(response.embeddings[0].values)
    return vecs

def list_blobs_in_container() -> List[str]:
    """List all blobs in the Azure Storage container"""
    try:
        blob_service_client = BlobServiceClient(
            account_url=f"https://{settings.AZURE_BLOB_ACCOUNT_NAME}.blob.core.windows.net",
            credential=settings.AZURE_BLOB_ACCOUNT_KEY
        )
        
        container_client = blob_service_client.get_container_client(settings.AZURE_BLOB_CONTAINER_NAME)
        blob_list = container_client.list_blobs()
        return [blob.name for blob in blob_list]
        
    except Exception as e:
        print(f"Error listing blobs: {e}")
        return []

def load_excel_from_azure_storage(blob_name: str = "sentencias_pasadas.xlsx") -> pd.DataFrame:
    """Load Excel file from Azure Storage"""
    try:
        blob_service_client = BlobServiceClient(
            account_url=f"https://{settings.AZURE_BLOB_ACCOUNT_NAME}.blob.core.windows.net",
            credential=settings.AZURE_BLOB_ACCOUNT_KEY
        )
        
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_BLOB_CONTAINER_NAME,
            blob=blob_name
        )
        
        blob_data = blob_client.download_blob().readall()
        return pd.read_excel(io.BytesIO(blob_data))
        
    except Exception as e:
        print(f"Error loading Excel from Azure Storage: {e}")
        raise

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

def prepare_docs_legal(df: pd.DataFrame) -> List[Dict]:
    """Prepare documents from legal Excel with specific column structure"""
    docs = []
    for i, row in df.iterrows():
        # Extract and clean data from specific columns
        relevancia = float(row['Relevancia']) if pd.notna(row['Relevancia']) else 0.0
        providencia = str(row['Providencia']) if pd.notna(row['Providencia']) else None
        tipo = str(row['Tipo']) if pd.notna(row['Tipo']) else None
        fecha_sentencia = row['Fecha Sentencia'] if pd.notna(row['Fecha Sentencia']) else None
        tema_subtema = str(row['Tema - subtema']) if pd.notna(row['Tema - subtema']) else ""
        resuelve = str(row['resuelve']) if pd.notna(row['resuelve']) else ""
        sintesis = str(row['sintesis']) if pd.notna(row['sintesis']) else ""
        
        # Extract year from date if available
        year = None
        if fecha_sentencia:
            try:
                if isinstance(fecha_sentencia, str):
                    # Try to parse different date formats
                    from datetime import datetime
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y']:
                        try:
                            date_obj = datetime.strptime(str(fecha_sentencia), fmt)
                            year = date_obj.year
                            break
                        except ValueError:
                            continue
                else:
                    year = fecha_sentencia.year
            except:
                pass
        
        # Parse temas from "Tema - subtema" column
        temas = []
        if tema_subtema:
            # Split by common separators and clean
            parts = tema_subtema.replace(' - ', '|').replace(', ', '|').replace(',', '|').split('|')
            temas = [t.strip() for t in parts if t.strip()]
        
        # Combine resuelve and sintesis for content
        content_parts = []
        if resuelve and resuelve.lower() != 'nan':
            content_parts.append(f"Resuelve: {resuelve}")
        if sintesis and sintesis.lower() != 'nan':
            content_parts.append(f"Síntesis: {sintesis}")
        
        full_content = " ".join(content_parts)
        
        if not full_content.strip():
            continue  # Skip rows without meaningful content
            
        # Create chunks from the combined content
        chunks = chunk(full_content)
        for j, c in enumerate(chunks):
            docs.append({
                "id": f"{i}-{j}",
                "title": providencia,
                "content": c,
                "source": tipo,
                "date": fecha_sentencia.isoformat() + "Z" if hasattr(fecha_sentencia, 'isoformat') else None,
                "year": year,
                "relevance": relevancia,
                "tema_subtema_raw": tema_subtema,
                "temas": temas
            })
    return docs

def prepare_docs(df: pd.DataFrame, text_col: str, title_col: str | None,
                 source_col: str | None, date_col: str | None,
                 jurisdiction_col: str | None, year_col: str | None) -> List[Dict]:
    """Legacy function for backward compatibility"""
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
    print("Checking Azure Storage container...")
    
    # First, list available blobs to see what files exist
    available_blobs = list_blobs_in_container()
    print(f"Available files in container: {available_blobs}")
    
    # Look for Excel files
    excel_files = [blob for blob in available_blobs if blob.endswith(('.xlsx', '.xls'))]
    
    if not excel_files:
        print("No Excel files found in the container.")
        exit(1)
        
    # Use the first Excel file found, or specify the correct name
    excel_file = excel_files[0] if excel_files else "sentencias_pasadas.xlsx"
    print(f"Using Excel file: {excel_file}")
    
    print("Loading Excel from Azure Storage...")
    
    # Load Excel file from Azure Storage
    df = load_excel_from_azure_storage(excel_file)
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    
    # Check if required columns exist for legal format
    required_cols = ['Relevancia', 'Providencia', 'Tipo', 'Fecha Sentencia', 
                    'Tema - subtema', 'resuelve', 'sintesis']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Error: Missing required columns for legal format: {missing_cols}")
        print(f"Available columns: {list(df.columns)}")
        exit(1)
    
    print("Processing documents...")
    docs = prepare_docs_legal(df)
    
    print(f"Prepared {len(docs)} document chunks")
    if docs:
        print(f"Sample document: {docs[0]}")
        print("Starting upload to Azure AI Search...")
        upload_docs(docs)
        print("Upload completed successfully!")
    else:
        print("No documents to upload")
