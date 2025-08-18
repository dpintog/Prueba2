# Para crear el índice en Azure AI Search
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile, SearchField,
    SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearch, SynonymMap, SearchSuggester
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
import os
from dotenv import load_dotenv

load_dotenv()

class settings:
    EMBED_DIM: int = int(os.getenv("EMBED_DIM", "768"))
    AZURE_SEARCH_USE_MSI: bool = os.getenv("AZURE_SEARCH_USE_MSI", "false").lower() == "true"
    AZURE_SEARCH_API_KEY: str | None = os.getenv("AZURE_SEARCH_API_KEY")
    AZURE_SEARCH_ENDPOINT: str | None = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_INDEX: str = os.getenv("AZURE_SEARCH_INDEX", "legal-index")
    SEMANTIC_CONFIG_NAME: str = "legal-semantic"


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
        SearchableField(name="content", type="Edm.String", analyzer_name="es.microsoft", synonym_map_names=["es-legal-syn"]),
        SimpleField(name="source", type="Edm.String", filterable=True, facetable=True),
        
        SimpleField(name="date", type="Edm.DateTimeOffset", filterable=True, sortable=True),
        SimpleField(name="year", type="Edm.Int32", filterable=True, sortable=True, facetable=True),

        SimpleField(name="relevance", type="Edm.Double", filterable=True, sortable=True),
        SearchableField(name="tema_subtema_raw", type="Edm.String", analyzer_name="es.microsoft"),

        # se genera al tokenizar la columna "Tema - subtema"
        SimpleField(name="temas", type="Collection(Edm.String)", filterable=True, facetable=True),

        SearchField(name="content_vector", type="Collection(Edm.Single)", searchable=True,
                    vector_search_dimensions=settings.EMBED_DIM, vector_search_profile_name="vprofile"),
    ]

    vector = VectorSearch(
        profiles=[VectorSearchProfile(name="vprofile", algorithm_configuration_name="hnsw")],
        algorithms=[HnswAlgorithmConfiguration(name="hnsw")]
    )

    semantic = SemanticSearch(
        configurations=[SemanticConfiguration(
            name=settings.SEMANTIC_CONFIG_NAME,
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")]
            )
        )]
    )

    synonyms = SynonymMap(
        name="es-legal-syn",
        format="solr",
        synonyms="\n".join([
            # equivalence (bi-directional)
            "bullying, acoso escolar",
            "matoneo, acoso escolar",
            "redes sociales, social media",
            "piar, plan individual de ajustes razonables",
            # expansions (uni-directional examples)
            "ciberacoso => acoso escolar",
            "facebook, instagram, tiktok, youtube => redes sociales",
        ])
    )

    # scoring = [
    #     ScoringProfile(
    #         name="recency",
    #         functions=[
    #             FreshnessScoringFunction(
    #                 field_name="date",
    #                 boost=2.0,
    #                 parameters=FreshnessScoringParameters(boosting_duration="P730D")  # 2 años
    #             )
    #         ]
    #     )
    # ]

    suggester = SearchSuggester(name="sg", source_fields=["title", "content"])

    idx = SearchIndex(
        name=settings.AZURE_SEARCH_INDEX,
        fields=fields,
        vector_search=vector,
        semantic_search=semantic,
        suggesters=[suggester],
        # scoring_profiles=scoring si necesitamos ordenar por fecha
        #default_scoring_profile="recency",
        synonym_maps=[synonyms]
    )

    ic = client()
    
    # Delete existing index if it exists
    try:
        ic.delete_index(settings.AZURE_SEARCH_INDEX)
    except Exception:
        pass

    # Create or replace synonym map first
    try:
        ic.create_synonym_map(synonyms)
        print("Synonym map created: es-legal-syn")
    except Exception:
        try:
            ic.delete_synonym_map(synonyms.name)
            ic.create_synonym_map(synonyms)
            print("Synonym map recreated: es-legal-syn")
        except Exception as e:
            print(f"Warning: Could not create synonym map: {e}")
            # Remove synonym map reference from content field if creation failed
            for field in fields:
                if hasattr(field, 'name') and field.name == 'content':
                    field.synonym_map_names = []

    # Create the index
    ic.create_index(idx)
    print("Index created:", settings.AZURE_SEARCH_INDEX)

if __name__ == "__main__":
    create_or_replace()
