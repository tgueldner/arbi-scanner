import logging
import logging.config
import os
import time

import eth_utils
import requests
import yaml
from keys.telegram import TELEGRAM_CHAT_ID, TELEGRAM_TOKEN
from keys.arbi import ARBI_START_BLOCK, ARBI_LOG_ADDRESS, ARBI_LOG_TOPIC0, ARBI_DEST_CONTRACT

logging_yaml_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "resources", "logging_config.yaml")
)


last_seen_block = ARBI_START_BLOCK

def setup_logging():
    with open(logging_yaml_path, "r") as f:
        config = yaml.safe_load(f.read())
        config["handlers"]["telegram"]["token"] = TELEGRAM_TOKEN
        config["handlers"]["telegram"]["chat_id"] = TELEGRAM_CHAT_ID
        logging.config.dictConfig(config)


def getLogs(start_block, dest_topic):
    logs_url = "https://api-nova.arbiscan.io/api?module=logs&action=getLogs&fromBlock={}" \
               "&address={}" \
               "&topic0={}" \
               "&topic0_{}_opr=and" \
               "&topic{}={}" \
               "&apikey=YourApiKeyToken" \
           .format(start_block, ARBI_LOG_ADDRESS, ARBI_LOG_TOPIC0, dest_topic, dest_topic, ARBI_DEST_CONTRACT)
    logs_response = requests.get(logs_url)
    if logs_response.status_code != 200:
        raise Exception("Wrong response code. Code={}".format(logs_response.status_code))
    else:
        return logs_response.json()["result"]


def getLogDataValue(entry):
    value = int(entry["data"], 16)
    return eth_utils.from_wei(value, 'ether')


def getLogBlockNumber(entry):
    return int(entry["blockNumber"], 16)


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("ArbiScanner started")
    withdrawls = getLogs(ARBI_START_BLOCK, 2)
    last_seen_block = getLogBlockNumber(withdrawls[-1])
    value = getLogDataValue(withdrawls[-1])
    logger.info("Start at block {} with withdrawl of {}ARB".format(last_seen_block, value))

    while True:
        # wait 30 secs
        time.sleep(30)
        # withdrawls
        last_seen_withdrawls = last_seen_block
        last_seen_deposits = last_seen_block
        withdrawls = getLogs(last_seen_block + 1, 2)
        for entry in withdrawls:
            logger.info("Found new withdrawls of -{}ARB".format(getLogDataValue(entry)))
            last_seen_withdrawls = getLogBlockNumber(entry)
        time.sleep(5)
        # deposits
        deposits = getLogs(last_seen_block + 1, 1)
        for entry in deposits:
            logger.info("Found new deposit of {}ARB".format(getLogDataValue(entry)))
            last_seen_deposits = getLogBlockNumber(entry)

        last_seen_block = max(last_seen_deposits, last_seen_withdrawls, last_seen_block)


