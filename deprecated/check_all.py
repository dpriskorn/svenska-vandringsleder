import json
import logging
from contextlib import redirect_stdout
from io import StringIO
from jsonasobj import loads, as_json
from typing import Dict, Any, Union, Tuple

import requests
from ShExJSG import ShExJ
from dict_compare import compare_dicts, json_filtr
from pydantic import BaseModel
from pyshexc.parser_impl.generate_shexj import parse
from rich.console import Console
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_helpers import execute_sparql_query

console = Console()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class GetWikidataJsonLdError(BaseException):
    pass


class MissingInformationError(BaseException):
    pass


class HikingTrailValidator(BaseModel):
    """Takes a hiking trail and validates it"""

    wikidata_entity: str
    wikidata_entity_schema: str = (
        "E375"  # We hardcode the schema here because there is only one
    )
    item_jsonld: Dict[str, Any] = dict()
    cleaned_item_jsonld: Dict[str, Any] = dict()

    def _get_and_clean_item_jsonld(self):
        """helper method"""
        self._get_wikidata_entity_jsonld()
        self._clean_item_jsonld()

    def _clean_item_jsonld(self):
        if self.item_jsonld:
            cleaned = self.item_jsonld
            del cleaned["@context"]
            # del cleaned["type"]
            # del cleaned["start"]
            self.cleaned_item_jsonld = cleaned

    def validate_item_using_entityshape_api(self):
        # validate the current item
        language = "en"
        response = requests.get(
            f"http://entityshape.toolforge.org/api?"
            f"language={language}&"
            f"entityschema={self.wikidata_entity_schema}&"
            f"entity={self.wikidata_entity}"
        )
        if response.status_code == 200:
            json_result = response.json()
            console.print(json_result)
            # TODO act on the result once the API is functional again

    def _get_schema(self) -> Dict[str, Any]:
        """
        Downloads the schema from wikidata
        """
        if self.wikidata_entity_schema:
            url: str = f"https://www.wikidata.org/wiki/EntitySchema:{self.wikidata_entity_schema}?action=raw"
            response = requests.get(url)
            return response.json()["schemaText"]

    @staticmethod
    def _compare_shexj(
        shex: Union[ShExJ.Schema, str], shexj: Union[ShExJ.Schema, str]
    ) -> Tuple[bool, StringIO]:
        """This is copied from
        https://github.com/shexSpec/grammar-python-antlr/blob/master/tests/utils/simple_shex_test.py see license there
        """
        d1 = loads(as_json(shex) if isinstance(shex, ShExJ.Schema) else shex)
        d2 = loads(as_json(shexj) if isinstance(shexj, ShExJ.Schema) else shexj)

        log = StringIO()
        with redirect_stdout(log):
            return (
                compare_dicts(
                    d1._as_dict,
                    d2._as_dict,
                    d1name="expected",
                    d2name="actual  ",
                    filtr=json_filtr,
                ),
                log,
            )

    def _get_wikidata_entity_jsonld(self):
        # get wikidata item jsonld
        result = requests.get(
            f"http://www.wikidata.org/entity/{self.wikidata_entity}.jsonld"
        )
        if result.status_code == 200:
            item_jsonld = result.json()
            console.print(item_jsonld)
            self.item_jsonld = item_jsonld
        else:
            raise GetWikidataJsonLdError()

    @property
    def _get_cleaned_item_jsonld_as_string(self):
        if not self.cleaned_item_jsonld:
            raise MissingInformationError()
        return json.dumps(self.cleaned_item_jsonld)

    def validate_item_using_pyshexc(self):
        raise NotImplementedError("This does not work because the translation "
                                  "of the entityschema -> shexj does not look "
                                  "anything like the jsonld from Wikidata so we get a comparison error."
                                  "The Entityshape API and the code behind it seems like a more viable solution")
        entityschema = self._get_schema()
        console.print(entityschema)
        base = "http://www.wikidata.org/entity/"
        # convert shexc -> shexj
        shex: ShExJ.Schema = parse(str(entityschema), default_base=base)
        # shex['@context'] = "http://www.w3.org/ns/shex.jsonld"
        del shex["type"]
        del shex["start"]
        console.print(shex)
        self._get_and_clean_item_jsonld()
        # validate
        # Copied from https://github.com/shexSpec/grammar-python-antlr/blob/master/tests/utils/simple_shex_test.py
        msg = "ShExC to ShExJ Comparison Error"
        rslt, log = self._compare_shexj(shex, self._get_cleaned_item_jsonld_as_string)
        if not rslt:
            print(f"***** {msg} *****")
            print(log.getvalue())
            # print("\n***** Actual ShExJ *****")
            # print(as_json(shex))
        # for entry in log:
        #     print("Entry:")
        #     console.print(entry)
        exit()


def get_all_paths() -> Dict[str, Any]:
    return execute_sparql_query(
        """
        SELECT DISTINCT ?item WHERE {
          ?item wdt:P31 wd:Q2143825; # hiking path
                wdt:P17 wd:Q34. # sweden hardcoded
        }
        """
    )


# get all swedish paths first
config["USER_AGENT"] = "svenska-vandringsleder @So9q"
# check them all individually with https://github.com/Teester/entityshape
wbi = WikibaseIntegrator()

for result in get_all_paths()["results"]["bindings"]:
    logger.debug(result)
    item = wbi.item.get(
        entity_id=result["item"]["value"].replace("http://www.wikidata.org/entity/", "")
    )
    print(item.id)
    # We get 500 because of https://www.wikidata.org/wiki/Topic:Xcl3qmgk499eju28
    validator = HikingTrailValidator(wikidata_entity=item.id)
    validator.validate_item_using_entityshape_api()
    #validator.validate_item_using_pyshexc()
    exit()
