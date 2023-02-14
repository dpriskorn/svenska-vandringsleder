import requests
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.entities import ItemEntity
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_helpers import execute_sparql_query

# get all swedish paths first
config["user_agent"] = "svenska-vandringsleder @So9q"


def validate_item(wikidata_entity_schema: str = "", entity: str = ""):
    # validate the current item
    language = "en"
    json_result = requests.get(f"http://entityshape.toolforge.org/api?"
                               f"language={language}&"
                               f"entityschema{wikidata_entity_schema}&"
                               f"entity={entity}")
    print(json_result)

results = execute_sparql_query(
    """
    SELECT DISTINCT ?item WHERE {
  ?item wdt:P31 wd:Q2143825;
        wdt:P17 wd:Q34.
}
"""
)
# check them all individually with https://github.com/Teester/entityshape
wbi = WikibaseIntegrator()
for result in results["results"]["bindings"]:
    print(result)
    item = wbi.item.get(
        entity_id=result["item"]["value"].replace("http://www.wikidata.org/entity/", ""))
    print(item.id)
    validate_item(entity=item.id, wikidata_entity_schema="E375")
    exit()