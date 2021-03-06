import sys
import os
import json
import threading
import xbmc
import xbmcaddon
import logging
from logging.config import dictConfig

addon = xbmcaddon.Addon()

KODI_CONNECT_URL = os.environ.get('KODI_CONNECT_URL', 'wss://kodiconnect.kislan.sk/ws')

LIB_RESOURCE_PATH = xbmc.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'lib' ))
APP_RESOURCE_PATH = xbmc.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'connect' ))
sys.path.append(LIB_RESOURCE_PATH)
sys.path.append(APP_RESOURCE_PATH)

from log import logger

logger.debug('RESOURCE_PATHs: {}, {}'.format(LIB_RESOURCE_PATH, APP_RESOURCE_PATH))
logger.debug('__file__: {}'.format(__file__))

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.httpclient import HTTPRequest

from only_once import OnlyOnce, OnlyOnceException
from handler import Handler
from kodi import KodiInterface
from library_cache import LibraryCache
from custom_monitor import CustomMonitor
from custom_player import CustomPlayer
from utils import notif
import strings

logging_config = dict(
    version = 1,
    formatters = {
        'f': {'format':
              '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'}
        },
    handlers = {
        'h': {'class': 'logging.StreamHandler',
              'formatter': 'f',
              'level': logging.DEBUG}
        },
    loggers = {
        'tornado.general': {'handlers': ['h'],
                 'level': logging.DEBUG}
        }
)

dictConfig(logging_config)

class Client(object):
    def __init__(self, url, kodi, handler):
        self.url = url
        self.ioloop = IOLoop.current()
        self.ws = None
        self.should_stop = False
        self.last_connection_notification_message = None

        self.kodi = kodi
        self.handler = handler

        self.periodic = PeriodicCallback(self.periodic_callback, 20000)

    def start(self):
        self.connect()
        self.periodic.start()
        self.ioloop.start()

    def stop(self):
        self.should_stop = True
        if self.ws is not None:
            self.ws.close()
        self.periodic.stop()
        self.ioloop.stop()

    @gen.coroutine
    def connect(self):
        email = addon.getSetting('email')
        secret = addon.getSetting('secret')
        if len(email) == 0 or len(secret) == 0:
            logger.debug('Email and/or secret not defined, not connecting')
            return

        logger.debug('trying to connect')
        try:
            request = HTTPRequest(self.url, auth_username=email, auth_password=secret)

            self.ws = yield websocket_connect(request)
        except Exception, e:
            logger.debug('connection error: {}'.format(str(e)))
            self.ws = None
            notif.show(strings.FAILED_TO_CONENCT, level='error', tag='connection')
        else:
            logger.debug('Connected')
            self.connected = True
            notif.show(strings.CONNECTED, tag='connection')
            self.run()

    @gen.coroutine
    def run(self):
        while True:
            message_str = yield self.ws.read_message()
            if message_str is None:
                logger.debug('Connection closed')
                self.ws = None
                notif.show(strings.DISCONNECTED, level='warn', tag='connection')
                break

            try:
                message = json.loads(message_str)
                logger.debug(message)
                data = message['data']

                responseData = handler.handler(data)
            except Exception as e:
                logger.error('Handler failed: {}'.format(str(e)))
                responseData = { 'status': 'error', 'error': 'Unknown error' }

            self.ws.write_message(json.dumps({ 'correlationId': message['correlationId'], 'data': responseData }))

    def periodic_callback(self):
        logger.debug('periodic_callback')
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message(json.dumps({ 'ping': 'pong' }))

        try:
            self.kodi.update_cache()
        except Exception as e:
            logger.error('Failed to update Kodi library: {}'.format(str(e)))

class ClientThread(threading.Thread):
    def __init__(self, client):
        self.client = client
        threading.Thread.__init__(self)

    def run(self):
        self.client.start()

    def stop(self):
        logger.debug('Stopping client')
        self.client.stop()

if __name__ == '__main__':
    logger.debug('Starting')
    logger.debug('pid={}'.format(os.getpid()))

    try:
        once = OnlyOnce()
    except OnlyOnceException:
        logger.debug('Tunnel already running, exiting')
        sys.exit(0)

    library_cache = LibraryCache()
    kodi = KodiInterface(library_cache)
    handler = Handler(kodi)

    monitor = CustomMonitor(kodi)
    player = CustomPlayer()
    player.set_kodi(kodi)

    client = Client(KODI_CONNECT_URL, kodi, handler)
    client_thread = ClientThread(client)
    client_thread.start()

    try:
        while not monitor.abortRequested():
            # Sleep/wait for abort for 3 seconds
            if monitor.waitForAbort(3):
                # Abort was requested while waiting. We should exit
                break
    except KeyboardInterrupt:
        logger.debug('Interrupted')

    logger.debug('Stopping Tunnel')
    client_thread.stop()
    logger.debug('Joining Tunnel Thread')
    client_thread.join()
    logger.debug('Exit')


