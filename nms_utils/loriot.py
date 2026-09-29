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
from typing import Tuple

from colorama import Fore, Style

from .log import debugPrint
from .request import TIMEOUT, postRequest, getRequest, putRequest
from .gmail import manage2FALogin, manageGmailAPI, EMAIL, gmail

import math
import concurrent.futures

def login(host, api, user, password):
    credentials = {"pwd": password, "user": user}
    usrdata = {}
    headers = {"Content-Type": "application/json"}

    try:
        conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
        conn.request("POST", api, json.dumps(credentials), headers)
        response = conn.getresponse()

        if response.status == 200:
            usrdata = json.loads(response.read().decode(encoding="utf-8"))
        elif response.status == 401:
            print("Unauthorized. Check your credentials")
            usrdata["session"] = ""
        else:
            print("Status code: " + str(response.status))
            print(f"Login error. Host:{host} API:{api}")
            usrdata["session"] = ""

    except Exception as e:
        debugPrint(str(e))
        print(f"Login error. Host:{host} API:{api}")
        usrdata["session"] = ""

    finally:
        return usrdata


def loginAdme(host, user, password):
    api = "/1/admin/login"
    return login(host, api, user, password)


def loginImpersonate(host, userid, adminSessionId):
    api = "/1/admin/user/" + str(userid) + "/impersonate"

    debugPrint(f"Impersonating user {userid} on {host}")
    debugPrint(f"Using admin session: {adminSessionId[:20]}...")

    data = postRequest(host, "", api, adminSessionId)

    debugPrint(f"Impersonate response keys: {list(data.keys()) if data else 'None'}")

    session = data.get("sessionId", "")

    if session:
        debugPrint(f"Got sessionId from impersonate: {session[:20]}...")
    else:
        debugPrint(f"No sessionId in response. Full response: {data}")

    return session


def login2FA(host, passcode, session):
    api = "/1/admin/login-with-passcode"
    credentials = {"passcode": passcode, "session": session}
    usrdata = {}
    headers = {"Content-Type": "application/json"}
    errorResult = ""

    try:
        conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
        conn.request("POST", api, json.dumps(credentials), headers)
        response = conn.getresponse()

        if response.status == 200:
            usrdata = json.loads(response.read().decode(encoding="utf-8"))
        elif response.status == 401:
            errorResult += "Unauthorized. Check your credentials"
            usrdata["session"] = ""
        else:
            errorResult += "\nStatus code: " + str(response.status)
            errorResult += f"\nLogin error. Host: {host} API: {api}"
            usrdata["session"] = ""

    except Exception as e:
        errorResult += "\n" + str(e)
        errorResult += f"\nLogin error. Host: {host} API: {api}"
        usrdata["session"] = ""

    finally:
        return usrdata, errorResult

def is2FAEnabled(loriotResponse):
    return ('twoFactorRequired' in loriotResponse) and loriotResponse['twoFactorRequired'] is True

def getInstanceType(server, session):
    return getRequest(server, "/1/nwk/status", session)["serverType"]

def fetchAccountsPage(server, page, session, api, apiFieldName):
    MAX_RETRIES = 3

    for attempt in range(MAX_RETRIES):
        data = getRequest(server, f"{api}?page={page}", session)
        if data and data != "":
            return data.get(apiFieldName, [])

    print(f"{server}: Failed to retrieve {apiFieldName} page {page} after {MAX_RETRIES} attempts, skipping")
    return []

def getResourcesFromPages(customerObj, session, api, apiFieldName):
    REQUEST_THREADS=10

    resources = []
    data = getRequest(customerObj['server'], f"{api}?page=1", session)

    if not data or data == "" or "error" in data:
        print(customerObj['server'] + ": 0 resources retrieved")
        return resources

    # Record Page 1 no extra actions required
    if apiFieldName in data:
        resources.extend(data[apiFieldName])

    total = data.get('total')
    perPage = data.get('perPage',10) # Default to 10 if not provided to avoid issues with LNS v7
    total_pages = math.ceil(total / perPage) if perPage > 0 else 1

    # only one page
    if total_pages <= 1:
        return resources

    pages_to_fetch = range(2, total_pages + 1)

    # Multithreading to fetch remaining pages concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=REQUEST_THREADS) as executor:
        # Submit all page requests to the thread pool
        futures = {
            executor.submit(fetchAccountsPage, customerObj['server'], page, session, api, apiFieldName): page
            for page in pages_to_fetch
        }

        # As each thread completes, extend the main accounts list
        for future in concurrent.futures.as_completed(futures):
            try:
                page_resources = future.result()
                if page_resources:
                    resources.extend(page_resources)
            except Exception as e:
                page_num = futures[future]
                print(f"{customerObj['server']}: thread for page {page_num} raised an exception: {e}")
    return resources

def getAccounts(customerObj, session):
    return getResourcesFromPages(customerObj, session, "/1/admin/accounts", "accounts")

def getGateways(customerObj, api, account, session):
    gateways = []
    connectedGateways = 0
    multCardSlot = 0

    # Get all gateways for the user using the paginated API
    resources = getResourcesFromPages(customerObj, session, '/1/admin/user/' + str(account['userid']) + '/gateways',"gateways")

    for gw in resources:
        gateways.append(gw)
        if customerObj.get('retrieveConnected'):
            if gw.get('connected'):
                if gw.get('card', 0) != 0 and gw.get('basename', '') != 'Basics Station':
                    multCardSlot += 1
                else:
                    connectedGateways += 1

    return gateways, connectedGateways, multCardSlot

def getOrganizations(customerObj, session):
    return getResourcesFromPages(customerObj, session, "/1/admin/organizations", "organizations")

def getActiveDevicesCountLastMonth(customerObj, session, globalCount, organizationId):
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    today = datetime.today() + relativedelta(months=-1)
    lastMonth = today.strftime("%Y-%m-%d")

    if globalCount:
        api = "/1/admin/devices?filter=[lastSeen>" + lastMonth + "T00:00:00.000Z;organizationId!=1]&perPage=1"
    else:
        api = "/1/admin/devices?filter=[lastSeen>" + lastMonth + "T00:00:00.000Z;organizationId=" + str(organizationId) + "]&perPage=1"

    data = getRequest(customerObj['server'], api, session)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise ValueError(f"THREAD) ERROR: {customerObj['name']} JSONDecodeError on /1/admin/devices | globalCount: {globalCount} | organizationId: {organizationId} | data: {data}")
        except Exception as e:
            raise ValueError(f"THREAD) ERROR: {customerObj['name']} Unexpected error: {e} on /1/admin/devices | globalCount: {globalCount} | organizationId: {organizationId} | data: {data}")

    return data['total']


def getInOutFrames(customerObj, session):
    frames = {
        'date': 0, 'input_max': 0, 'input_avg': 0,
        'output_max': 0, 'output_avg': 0,
        'latency_max': 0, 'latency_avg': 0,
    }

    data = getRequest(customerObj['server'], "/1/admin/system/latency-history", session)
    if data == "" or len(data) == 0:
        print(customerObj['server'] + ": 0 input/output frames retrieved")
        for k in ('input_max', 'input_avg', 'output_max', 'output_avg', 'latency_max', 'latency_avg'):
            frames[k] = "-"
        return frames

    frames['date'] = data[0]['_id'].replace(":00.000Z", "") + "|" + data[-1]['_id'].replace(":00.000Z", "")
    for frame in data:
        frames['input_max'] = max(frames['input_max'], frame['inc'])
        frames['input_avg'] += frame['inc']
        frames['output_max'] = max(frames['output_max'], frame['cnt'])
        frames['output_avg'] += frame['cnt']
        if frame['cnt'] != 0:
            frames['latency_max'] = round(max(frames['latency_max'], frame['lat'] / frame['cnt']), 2)
            frames['latency_avg'] += frame['lat'] / frame['cnt']

    frames['input_avg'] = round(frames['input_avg'] / len(data), 2)
    frames['output_avg'] = round(frames['output_avg'] / len(data), 2)
    frames['latency_avg'] = round(frames['latency_avg'] / len(data), 2)
    return frames


def getServerRelease(customerObj, session):
    data = getRequest(customerObj['server'], "/1/admin/status", session)
    if data == "" or not data:
        print(customerObj['server'] + ": server status not retrieved")
        return "N/A"

    for component in data.get('version', []):
        if 'component' in component and component['component'] == 'global':
            return component['version']

    return "N/A"


__all__ = [
    "login",
    "loginAdme",
    "loginImpersonate",
    "login2FA",
    "is2FAEnabled",
    "manage2FALogin",
    "manageGmailAPI",
    "getInstanceType",
    "EMAIL",
    "gmail",
    "getAccounts",
    "getGateways",
    "getActiveDevicesCountLastMonth",
    "getOrganizations",
    "getInOutFrames",
    "getServerRelease",
]
