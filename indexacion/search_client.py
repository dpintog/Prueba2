from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from embedder import settings

def make_search_client() -> SearchClient:
    if settings.AZURE_SEARCH_USE_MSI:
        cred = DefaultAzureCredential()
        return SearchClient(settings.AZURE_SEARCH_ENDPOINT, settings.AZURE_SEARCH_INDEX, cred)
    if not settings.AZURE_SEARCH_API_KEY:
        raise RuntimeError("Provide AZURE_SEARCH_API_KEY or set AZURE_SEARCH_USE_MSI=true")
    return SearchClient(settings.AZURE_SEARCH_ENDPOINT, settings.AZURE_SEARCH_INDEX,
                        AzureKeyCredential(settings.AZURE_SEARCH_API_KEY))
