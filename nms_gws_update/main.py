# Creator: LORIOT AG
# Copyright 2026 Loriot
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

import time
import sys
import logging
import concurrent.futures
import argparse
from loriot import getRequest, postRequest, putRequest, getResourcesFromPages, loginAdme

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def update_gateway(server, account, network, gw, session):
    logger.info(f"✏️ [UPDATE] [{gw}] Starting update process for user {account}...")

    # 1. Allow next update (Using PUT as requested)
    putRequest(server, "{}", f"/1/nwk/gateway/{gw}/software/allow-next-update", session)
    logger.info(f"🧑‍🏭 [UPDATE] [{gw}] Allow next update done")

    # 2. Restart the gateway
    postRequest(server, "{}", f"/1/nwk/gateway/{gw}/restart", session)
    logger.info(f"🔄 [UPDATE] [{gw}] Restart command sent")

    # 3. Wait until GW is available again: Retry each 15s max 5 times
    max_retries = 5
    retry_interval = 5
    is_connected = False

    for attempt in range(1, max_retries + 1):
        logger.info(f"⏳ [UPDATE] [{gw}] Waiting to reconnect... (Attempt {attempt}/{max_retries})")
        time.sleep(retry_interval)

        gw_info = getRequest(server, f"/1/nwk/network/{network}/gateways/{gw}", session)

        # Check if the gateway object shows as connected
        if gw_info and gw_info.get("connected"):
            is_connected = True
            logger.info(f"✅ [UPDATE] [{gw}] ONLINE AND SUCCESSFULLY RESTARTED")
            break

    # 4. Check final status
    if not is_connected:
        logger.error(f"❌ [UPDATE] [{gw}] ERROR: Gateway failed to come online after {max_retries * retry_interval} seconds.")
        return False

    return True


def create_parser():
    parser = argparse.ArgumentParser(
        description="Update and restart gateways in parallel via Loriot API"
    )
    parser.add_argument("--server", required=True, help="Loriot server URL")
    parser.add_argument("--user", required=True, help="Username for Loriot")
    parser.add_argument("--password", required=True, help="Password for Loriot")
    return parser


def print_help():
    create_parser().print_help()


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()

    accounts = {}
    customerObj = {}
    customerObj['user'] = args.user
    customerObj['server'] = args.server
    customerObj['password'] = args.password

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger.info(f"🔑 [MAIN] Get session for: {customerObj['server']}")
    loriotResponse = loginAdme(customerObj['server'], customerObj['user'], customerObj['password'])

    if loriotResponse.get("session") is None:
        logger.error("🛑 Login failed. Check your credentials.")
        sys.exit(1)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger.info("📡 [MAIN] Getting total gateways...")
    gateways = getResourcesFromPages(customerObj, loriotResponse['session'], "/1/admin/gateways", "gateways")
    logger.info(f"📊 Total gateways: {len(gateways)}")

    logger.info("🟢 [MAIN] Getting online gateways...")
    onlineGWs = [gw for gw in gateways if gw.get('connected')]
    logger.info(f"📈 Online gateways: {len(onlineGWs)}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger.info("👥 [MAIN] Getting user sessions...")
    for gw in onlineGWs:
        # Initialize user data structure
        if gw.get("userid") not in accounts:
            accounts[gw.get("userid")] = {"networks": {}, "session": "", "restartResult": ""}

        # Initialize network data structure
        if gw.get("nwkid") not in accounts[gw.get("userid")]["networks"]:
            accounts[gw.get("userid")]["networks"][gw.get("nwkid")] = []

        accounts[gw.get("userid")]["networks"][gw.get("nwkid")].append(gw.get("EUI").replace("-", ""))

    # Get impersonation sessions
    for account in accounts:
        impersonate = postRequest(customerObj['server'], {}, f"/1/admin/user/{account}/impersonate", loriotResponse['session'])
        accounts[account]["session"] = impersonate.get("sessionId")

    # Prepare the list of tasks for the thread pool
    update_tasks = []
    for account, account_data in accounts.items():
        session = account_data["session"]
        for network, gw_list in account_data["networks"].items():
            for gw in gw_list:
                update_tasks.append((customerObj['server'], account, network, gw, session))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    max_concurrent_threads = 10
    has_errors = False
    logger.info(f"🧵 [MAIN] Starting parallel updates for {len(update_tasks)} gateways... (Max threads: {max_concurrent_threads})")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_threads) as executor:
        # Submit all tasks to the executor
        future_to_gw = {
            executor.submit(update_gateway, server, acc, nwk, gw, sess): gw
            for (server, acc, nwk, gw, sess) in update_tasks
        }

        # Process the results as they complete
        for future in concurrent.futures.as_completed(future_to_gw):
            gw = future_to_gw[future]
            try:
                success = future.result()
                if not success:
                    has_errors = True
            except Exception as exc:
                logger.error(f"❌ [UPDATE] [{gw}] Exception occurred during update: {exc}")
                has_errors = True

    if has_errors:
        logger.error("⚠️  [DONE] Completed with some errors. Please check the logs above.")
        sys.exit(1)
    else:
        logger.info("🏁 [DONE] All gateways successfully updated and restarted.")