![CrowdStrike Zoom QSS_to_LogScale](/docs/assets/cs-logo.png)

[![Twitter URL](https://img.shields.io/twitter/url?label=Follow%20%40CrowdStrike&style=social&url=https%3A%2F%2Ftwitter.com%2FCrowdStrike)](https://twitter.com/CrowdStrike)<br/>

# Zoom QSS WebSocket Events to LogScale Ingest

This integration provides Python3 code and supporting assets to create a persistent WebSocket connection to the Zoom QSS api, in order to receive Zoom QoS events, and forward them to LogScale for ingest.

[Zoom QSS](https://explore.zoom.us/en/qss/) (Quality of Service Subscription) provides near real-time quality of service (QoS) telemetry for Zoom video conference calls, webinars, and phone calls.

The Python3 code in this integration provides two (2) persistent coroutines:
- a connection heart-beat pulse.
- an event loop that receives and forwards QSS/QoS events.

This integration is a companion to the Zoom Qss LogScale package.
The Zoom Qss LogScale package comprises the set assets that provide search analytics and data visualization of Zoom Qss QoS telemetry.

## Installation and Setup
### Create a Zoom Server-to-Server OAuth app
- Sign into you Zoom account.
- Navigate to the [Zoom Marketplace](https://marketplace.zoom.us/develop/create)
- Create a Server-to-Server OAuth app for WebSocket API access.
    - see (https://www.youtube.com/watch?v=OkBE7CHVzho)
- Apply the following scopes to your app:

    |Scope Name|ID|
    |----------|--|
    |View all users' meetings information on Dashboard|dashboard_meetings:read:adminDelete|
    |View all users' webinar information on Dashboard|dashboard_webinars:read:adminDelete|

    *Note: This integration does not currently support Zoom phone calls*
### Prepare the integration


#### Prepare the Docker image Environmental Variables file
- create directory: /etc/zoom-qss 
- create the vars file: /etc/zoom-qss/env.vars
- add the environmental variable definitions *(note: values should be bare. i.e. unquoted)*
    ```
    LOGSCALE_HOST=<host>
    LOGSCALE_INGEST_TOKEN=<token>
    LOGSCALE_REPOSITORY=<repository>
    ZOOM_ACCOUNT_ID=<acct id>
    ZOOM_CLIENT_ID=<client id>
    ZOOM_CLIENT_SECRET=<secret>
    ZOOM_WSS_URL=<url>
    ```
    - LogScale variables
      - LOGSCALE_HOST - LogScale server
      - LOGSCALE_REPOSITORY - LogScale repository
      - LOGSCALE_INGEST_TOKEN - LogScale ingest token
    - Zoom API variables *(from the Zoom app)*
      - ZOOM_ACCOUNT_ID - Zoom app credentials - Account ID
      - ZOOM_CLIENT_ID - Zoom app credentials - Client ID
      - ZOOM_CLIENT_SECRET - Zoom app credentials - Client Secret
      - ZOOM_WSS_URL - WebSocket endpoint URL
        - see (https://developers.zoom.us/docs/api/rest/websockets/)

### Prepare LogScale
#### Setup the Ingest Repository
- select, or create a target ingest repository

- create an ingest token, or use the default ingest token
    - install the LogScale Zoom QSS package.
    - assign the ```zoom_qss``` parser to the repository

##### optionally set logging level to DEBUG to view payload delivery and heartbeat progress
```python
    logger.setLevel(logging.DEBUG)
```
*warning: DEBUG output generates copious logging*

#### Prepare the Python Docker image
- cd to the directory that contains the Dockerfile, Python code, and requirements.txt
- build the docker image:
    - ```docker build -t zoom-qss .```


#### Prepare the systemd service
- install the qss2logscale service file
    - cp qss2logscale.service /etc/systemd/system
    - systemctl daemon-reload
- start the qss2logscale service 
    - service qss2logscale start
#### Verify event delivery
- if DEBUG logging was enabled, check syslog for payload and heartbeat logging.
- check the LogScale repository to verify that events are arriving

---

<p align="center"><img src="/docs/assets/cs-logo-footer.png"><BR/><img width="250px" src="/docs/assets/adversary-red-eyes.png"></P>
<h3><P align="center">WE STOP BREACHES</P></h3>