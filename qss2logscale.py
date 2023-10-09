"""
    Receive and forward Zoom Qss WebSocket events to LogScale

    Asynchronous tasks:
        1) heartbeat ticker
        2) websocket listener/forwarder

    Required environmental variables:
        LOGSCALE_HOST=<logscale server>
        LOGSCALE_INGEST_TOKEN=<token>
        LOGSCALE_REPOSITORY=<repo>

        ZOOM_ACCOUNT_ID=<account id>
        ZOOM_CLIENT_ID=<client id>
        ZOOM_CLIENT_SECRET=<client secret>
        ZOOM_WSS_URL=wss://ws.zoom.us/ws?subscriptionId=<subscription id>

    Assumptions:
        Valid Zoom and LogScale credentials
"""

import asyncio
import json
import logging
import time
import os
import re
from base64 import b64encode
import websockets
import requests
from logscale import IngestApi, HecEvent, Payload, WebSocketReceiveException, \
    WebSocketConnectException, QssEventException, QssApiException
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)


def qos_a2e(qos_array):
    """convert QOS array to vector field elements"""
    qos = {}
    for i in qos_array:
        qos[i["type"]] = i["details"]
        if "date_time" in i:
            qos[i["type"]].update({"date_time": i["date_time"]})
    return qos


def data_a2e(data_array):
    """convert single DATA object qos_array to elements"""
    data = {}
    for k, v in data_array[0].items():
        data[k] = v
    return data


def b64(b64_string):
    return b64encode(
        b64_string.encode('ascii')
    ).decode('ascii')


def get_api_token(account_id, client_id_secret):
    """Request a QSS api access token
       From: https://developers.zoom.us/docs/internal-apps/
    """
    headers = {'Host': 'zoom.us',
               'Authorization': 'Basic {cidsec}'.format(cidsec=client_id_secret)}
    payload = {
        'grant_type': 'account_credentials',
        'account_id': '{accountID}'.format(accountID=account_id)
    }
    zoom_oauth = "https://zoom.us/oauth/token"
    response = requests.post(zoom_oauth, data=payload, headers=headers)
    if response.ok:
        c = json.loads(response.content)
    else:
        raise QssApiException(response.status_code)

    return c['access_token']


async def heartbeat(timeout, websocket):
    """send QSS heartbeats"""
    while True:
        await asyncio.sleep(timeout)
        msg = json.dumps({"module": "heartbeat"})
        await websocket.send(msg)
        logger.debug("heartbeat sent.")


async def qss():
    logscale_host         = os.getenv('LOGSCALE_HOST')
    logscale_repository   = os.getenv('LOGSCALE_REPOSITORY')
    logscale_ingest_token = os.getenv('LOGSCALE_INGEST_TOKEN')
    zoom_client_id        = os.getenv('ZOOM_CLIENT_ID')
    zoom_client_secret    = os.getenv('ZOOM_CLIENT_SECRET')
    zoom_wss_url          = os.getenv('ZOOM_WSS_URL')
    zoom_account_id       = os.getenv('ZOOM_ACCOUNT_ID')

    logscale = IngestApi(host=logscale_host, repository=logscale_repository, token=logscale_ingest_token)
    client_id_secret = b64(zoom_client_id + ":" + zoom_client_secret)
    access_token = get_api_token(zoom_account_id, client_id_secret)
    uri = zoom_wss_url + "&access_token=" + access_token
    async with websockets.connect(uri) as ws:
        msg = await ws.recv()
        d = json.loads(msg)
        if d['module'] == "build_connection":
            if not d['success']:
                raise WebSocketConnectException(d['success'])
            else:
                # start the Qss connection heartbeat
                logger.debug("starting QSS heartbeat.")
                asyncio.create_task(heartbeat(30, ws))
        else:  # unexpected connection message
            raise WebSocketConnectException(d['module'])

        # suggestion: set the source field to uniquely identify the data stream
        source = "zoom_websocket"
        # requirement: set the sourcetype to the target ingest parser name
        sourcetype = "zoom_qss"
        hec_event = HecEvent(host=logscale_host, index=logscale_repository, source=source, sourcetype=sourcetype)
        payload = Payload()

        logger.debug("waiting for events.....")
        # Receive events; send to LogScale
        while True:
            msg = await ws.recv()
            d = json.loads(msg)
            if d['module'] == 'message':
                c = json.loads(d['content'])
                d['content'] = c
                if c['event']:
                    if re.search("_qos", c['event']):
                        qos = qos_a2e(c['payload']['object']['participant']['qos'])
                        c['payload']['object']['participant']['qos'] = qos
                    elif re.search("_data", c['event']):
                        data = data_a2e(c['payload']['object']['participant']['data'])
                        c['payload']['object']['participant']['data'] = data
                    else:
                        raise QssEventException(c['event'])
                    hev = hec_event.create(message=d)
                    payload.pack(hev)
                    if payload.full:  # send event batch
                        logger.debug(
                            "post events: {ec}, payload: {b}".format(ec=payload.event_count, b=payload.size_bytes))
                        logscale.send_event("hec", payload.packed)
                        payload.reset()
                else:
                    raise WebSocketConnectException
            else:
                if d['module'] == 'heartbeat':
                    logger.debug("heartbeat")
                else:
                    raise WebSocketReceiveException(msg)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(qss())
