import base64
import logging
import urllib
from urllib.parse import unquote

import requests

from .api import BaseAPI

_LOGGER = logging.getLogger(__name__)


class GatewayAPI(BaseAPI):
    username: str = "gateway"

    def __init__(self, hostname: str, password: str) -> None:
        super().__init__(hostname, self.username, password)
        self.password: str = password
        self.api_host: str = hostname

        self.request_count: int = 0
        self.last_request_signature: str | None = None
        self.udid: str = "homeassistant"

    def call(self, endpoint: str, data: dict = None) -> dict:
        if data is None:
            data = {}

        _LOGGER.debug("[%s] - requesting", endpoint)
        json_response = None

        try:
            data['userlogin'] = self.username
            data['udid'] = self.udid
            data['reqcount'] = self.request_count

            post_data_sorted = sorted(data.items(), key=lambda val: val[0])

            urlencoded_body = urllib.parse.urlencode(post_data_sorted, encoding='utf-8')
            urlencoded_body_prepared_for_hash = self._prepare_request_body_for_hash(urlencoded_body)
            urlencoded_body_prepared_for_hash = urlencoded_body_prepared_for_hash.replace('&', '|')
            urlencoded_body_prepared_for_hash = urlencoded_body_prepared_for_hash + "|"

            request_signature = base64.b64encode(
                self.encode_signature(urlencoded_body_prepared_for_hash, self.password)).decode()

            self.last_request_signature = request_signature

            urlencoded_body = urlencoded_body + "&" + urllib.parse.urlencode({"request_signature": request_signature},
                                                                             encoding='utf-8')

            _LOGGER.debug("[%s] - body: %s", endpoint, urlencoded_body)

            response = self.session.post("http://{hostname}/{endpoint}".format(hostname=self.api_host, endpoint=endpoint),
                                         data=urlencoded_body,
                                         headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                                         )

            self.request_count = self.request_count + 1

            _LOGGER.debug("[%s] - response code: %s", endpoint, response.status_code)

            json_response = response.json()
        except Exception as exception:
            _LOGGER.exception("Unable to fetch data from API [%s]: %s", endpoint, exception)
            raise

        _LOGGER.debug("[%s] - response body: %s", endpoint, json_response)

        if not json_response.get('success', False):
            _LOGGER.error("[%s] - API call unsuccessful: %s", endpoint, json_response)
            raise Exception('Failed to get data from API endpoint: {}'.format(endpoint))
        else:
            _LOGGER.debug('[%s] - successfully fetched data from API', endpoint)

        return json_response

    def login(self):
        try:
            response = self.call("admin/login/check")

            if not response.get('success', False):
                _LOGGER.error("Gateway login check failed")
                raise Exception("Unable to login")
        except Exception as e:
            _LOGGER.exception("Exception during gateway login: %s", e)
            raise

        _LOGGER.info("Successfully logged into Gateway API")
        return self

    def all_modules(self) -> dict:
        try:
            response = self.call("api/gateway/allmodules")
            return response['modules']['rooms']
        except Exception as e:
            _LOGGER.error("Error fetching all modules: %s", e)
            raise

    def db_modules(self) -> dict:
        try:
            return self.call("api/gateway/dbmodules")
        except Exception as e:
            _LOGGER.error("Error fetching DB modules: %s", e)
            raise

    def get_module_details(self, module_id) -> dict | None:
        try:
            response = self.db_modules()
            if module_id in response['modules']:
                return response['modules'][module_id]
            else:
                _LOGGER.warning("Module details not found for module ID: %s", module_id)
                return None
        except Exception as e:
            _LOGGER.error("Error fetching module details for %s: %s", module_id, e)
            raise
