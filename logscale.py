"""Send events to Logscale HEC ingestion api

   Required variables:
    LOGSCALE_HOST - LogScale server
    LOGSCALE_REPOSITORY - LogScale repository
    LOGSCALE_INGEST_TOKEN - LogScale ingest token

   Assumptions:
        POST Payload MAX_POST_BYTES, MAX_POST_EVENTS comply with
        current api best practice (see link below).
"""

import time
import json
import logging
from xmlrpc.client import Boolean
import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)


class QssEventException(Exception):
    """QssEventException Exception"""


class QssApiException(Exception):
    """QssApiException Exception"""


class WebSocketConnectException(Exception):
    """WebSocket Connect Argument Exception"""


class WebSocketReceiveException(Exception):
    """WebSocket Receive Argument Exception"""


class WebSocketEventException(Exception):
    """WebSocket Event Exception"""


class LogScaleArgumentException(Exception):
    """LogScale Argument Exception"""


class LogScaleSendException(Exception):
    """LogScale Send Exception"""


class Payload(object):
    """LogScale ingest api payload"""

    # recommended API POST payload limits:
    #   5Mb max size or max 5000 batched events
    # from: https://library.humio.com/falcon-logscale/api-ingest.html#api-ingest-best-practices
    MAX_POST_BYTES = 5242880
    MAX_POST_EVENTS = 5000  # batched events

    def __init__(self) -> None:
        self.payload = ""
        self.payload_pack_count = 0
        self.payload_size_bytes = 0

    def pack(self, event) -> None:
        event_string = json.dumps(event)
        if self.payload_pack_count == 0:
            self.payload = event_string
        else:
            self.payload = self.payload + "\n" + event_string
        self.payload_pack_count = self.payload_pack_count + 1
        self.payload_size_bytes = self.payload_size_bytes + len(self.payload.encode('utf-8'))

    def reset(self) -> None:
        self.payload = ""
        self.payload_size_bytes = 0
        self.payload_pack_count = 0

    @property
    def packed(self):
        """Packed payload"""
        return self.payload

    @property
    def event_count(self):
        """Packed payload event count"""
        return self.payload_pack_count

    @property
    def size_bytes(self):
        """Packed payload size in bytes"""
        return self.payload_size_bytes

    @property
    def full(self) -> Boolean:
        if (self.payload_size_bytes >= Payload.MAX_POST_BYTES) or (self.payload_pack_count >= Payload.MAX_POST_EVENTS):
            return True
        else:
            return False

    @property
    def empty(self) -> Boolean:
        if self.payload_size_bytes == 0:
            return True
        else:
            return False


# LogScale HEC Event
class HecEvent(object):
    """LogScale HEC Ingest Event
       https://library.humio.com/humio-server/log-shippers-hec.html
    """

    def __init__(self, index, host, source, sourcetype) -> None:
        self.index = index
        self.host = host
        self.source = source
        self.sourcetype = sourcetype
        self.payload = Payload()
        self.hec_event = {}

    @staticmethod
    def _current_milli_time():
        return time.time()

    def create(self, message) -> dict:
        self.hec_event = {
            'time': self._current_milli_time(),
            'source': self.source,
            'sourcetype': self.sourcetype,
            'host': self.host,
            'index': self.index,
            'event': message,
            'fields': {}}
        # self.hec_event['timezone'] = 'utc'
        return self.hec_event


class IngestApi(object):
    INGEST_ENDPOINTS = {
        'hec': "api/v1/ingest/hec",
        'api-structured': "api/v1/ingest/humio-structured"
    }

    def __init__(self, host, repository, token):
        self.host = host
        self.repository = repository
        self.ingest_token = token

    def send_event(self, endpoint, payload):
        if endpoint not in IngestApi.INGEST_ENDPOINTS.keys():
            raise LogScaleArgumentException
        ingest_host = "https://{host}/{ep}".format(host=self.host, ep=IngestApi.INGEST_ENDPOINTS[endpoint])
        headers = {'Authorization': 'Bearer {token}'.format(token=self.ingest_token),
                   'Content-Type': 'application/json'}
        try:
            r = requests.post(ingest_host, data=payload, headers=headers)
        except LogScaleSendException as hse:
            logger.error("Exception sending payload: {e}".format(e=hse))
            raise hse

        if r.status_code != 200:
            logger.warn("Post status code: {status} - Reason: {reason} - Text: {text}".format(status=r.status_code,
                                                                                              reason=r.reason,
                                                                                              text=r.text))
