# Para crear el índice en Azure AI Search
from backend.config import settings
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSettings
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

def client():
    if settings.AZURE_SEARCH_USE_MSI:
        cred = DefaultAzureCredential()
    else:
        cred = AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
    return SearchIndexClient(settings.AZURE_SEARCH_ENDPOINT, credential=cred)

def create_or_replace():
    fields = [
        SimpleField(name="id", type="Edm.String", key=True, filterable=True, sortable=True),
        SearchableField(name="title", type="Edm.String", analyzer_name="es.microsoft"),
        SearchableField(name="content", type="Edm.String", analyzer_name="es.microsoft"),
        SimpleField(name="source", type="Edm.String", filterable=True, facetable=True),
        SimpleField(name="jurisdiction", type="Edm.String", filterable=True, facetable=True),
        SimpleField(name="date", type="Edm.String", sortable=True),
        SimpleField(name="year", type="Edm.Int32", filterable=True, sortable=True),
        SimpleField(name="content_vector", type="Collection(Edm.Single)", searchable=True,
                    dimensions=settings.EMBED_DIM, vector_search_profile_name="vprofile"),
    ]

    vector = VectorSearch(
        profiles=[VectorSearchProfile(name="vprofile", algorithm_configuration_name="hnsw")],
        algorithms=[HnswAlgorithmConfiguration(name="hnsw")]
    )

    semantic = SemanticSettings(
        configurations=[SemanticConfiguration(
            name=settings.SEMANTIC_CONFIG_NAME,
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")]
            )
        )]
    )

    idx = SearchIndex(
        name=settings.AZURE_SEARCH_INDEX,
        fields=fields,
        vector_search=vector,
        semantic_settings=semantic
    )

    ic = client()
    try:
        ic.delete_index(settings.AZURE_SEARCH_INDEX)
    except Exception:
        pass
    ic.create_index(idx)
    print("Index created:", settings.AZURE_SEARCH_INDEX)

if __name__ == "__main__":
    create_or_replace()
