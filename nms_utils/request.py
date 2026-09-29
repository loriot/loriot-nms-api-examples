# Copyright 2026 Loriot AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import http.client
import json
from typing import Any, Dict

from .log import debugPrint

TIMEOUT = 30


def _headers_with_session(session: str) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
    }
    if session:
        headers["Authorization"] = "Session " + session
    return headers


def getRequest(host: str, api: str, session: str) -> Any:
    data: Any = ""
    headers = _headers_with_session(session)
    try:
        conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
        conn.request("GET", api, "", headers)
        response = conn.getresponse()
        response_body = response.read().decode(encoding="utf-8")

        if response.status == 200:
            data = json.loads(response_body)
        elif response.status == 401:
            print("Unauthorized. Check your credentials")
            print(f"Response body: {response_body[:200]}")
            try:
                data = json.loads(response_body)
            except Exception:
                data = {}
        else:
            print("Status code: " + str(response.status))
            print("GET Request error")
            print(f"Response body: {response_body[:200]}")
            try:
                data = json.loads(response_body)
            except Exception:
                data = {}

    except Exception as e:
        debugPrint(str(e))
        print(f"GET Request error. Host:{host} API:{api} | Reason: {repr(e)}")
    finally:
        return data


def postRequest(host: str, params: str, api: str, session: str) -> Any:
    data: Any = ""
    headers = _headers_with_session(session)
    try:
        conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
        conn.request("POST", api, params, headers)
        response = conn.getresponse()
        response_body = response.read().decode(encoding="utf-8")

        if response.status == 200:
            data = json.loads(response_body)
        elif response.status == 204:
            data = {}
        elif response.status == 401:
            print("Unauthorized. Check your credentials")
            print(f"Response body: {response_body[:200]}")
            try:
                data = json.loads(response_body)
            except Exception:
                data = {}
        else:
            print("Status code: " + str(response.status))
            print("post Request error")
            print(f"Response body: {response_body[:200]}")
            try:
                data = json.loads(response_body)
            except Exception:
                data = {}

    except Exception as e:
        debugPrint(str(e))
        print(f"POST Request error. Host:{host} API:{api} | Reason: {repr(e)}")
    finally:
        return data

def putRequest(host: str, params: str, api: str, session: str) -> Any:
    data: Any = ""
    headers = _headers_with_session(session)
    try:
        conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
        # Changed "POST" to "PUT" here
        conn.request("PUT", api, params, headers)
        response = conn.getresponse()
        response_body = response.read().decode(encoding="utf-8")

        if response.status == 200:
            data = json.loads(response_body)
        elif response.status == 204:
            data = {}
        elif response.status == 401:
            print("Unauthorized. Check your credentials")
            print(f"Response body: {response_body[:200]}")
            try:
                data = json.loads(response_body)
            except Exception:
                data = {}
        else:
            print("Status code: " + str(response.status))
            print("PUT Request error")
            print(f"Response body: {response_body[:200]}")
            try:
                data = json.loads(response_body)
            except Exception:
                data = {}

    except Exception as e:
        debugPrint(str(e))
        print(f"PUT Request error. Host:{host} API:{api} | Reason: {repr(e)}")
    finally:
        return data


def deleteRequest(host: str, api: str, session: str) -> Any:
    data: Any = ""
    headers = _headers_with_session(session)

    print("Host: " + host + ". API: " + api)

    try:
        conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
        conn.request("DELETE", api, "", headers)
        response = conn.getresponse()
        response_body = response.read().decode(encoding="utf-8")
        if (response.status == 204) or (response.status == 200):
            data = "DELETE successful"
        elif response.status in (400, 401):
            print("Unauthorized. Check your credentials")
            print(f"Response body: {response_body[:200]}")
            data = ""
        else:
            print("Status code: " + str(response.status))
            print("DELETE Request error")
            print(f"Response body: {response_body[:200]}")
            data = ""

    except Exception as e:
        debugPrint(str(e))
        print(f"DELETE Request error. Host:{host} API:{api}")
    finally:
        return data

__all__ = ["TIMEOUT", "getRequest", "postRequest", "deleteRequest"]
