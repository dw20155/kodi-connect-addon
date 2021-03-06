from tornado.ioloop import IOLoop

import xbmc
from log import logger

class Handler(object):
    def __init__(self, kodi):
        self.kodi = kodi

    def search_and_play_handler(self, video_filter):
        logger.debug('search_and_play_handler: {}'.format(str(video_filter)))
        IOLoop.instance().add_callback(self.kodi.find_and_play, video_filter)

    def search_and_display_handler(self, video_filter):
        logger.debug('search_and_display_handler: {}'.format(str(video_filter)))
        IOLoop.instance().add_callback(self.kodi.find_and_display, video_filter)

    def next_handler(self):
        logger.debug('next_handler')
        IOLoop.instance().add_callback(self.kodi.next_item)

    def previous_handler(self):
        logger.debug('previous_handler')
        IOLoop.instance().add_callback(self.kodi.previous_item)

    def start_over_handler(self):
        logger.debug('start_over_handler')
        IOLoop.instance().add_callback(self.kodi.start_over)

    def pause_handler(self):
        logger.debug('pause_handler')
        IOLoop.instance().add_callback(self.kodi.pause)

    def resume_handler(self):
        logger.debug('resume_handler')
        IOLoop.instance().add_callback(self.kodi.resume)

    def stop_handler(self):
        logger.debug('stop_handler')
        IOLoop.instance().add_callback(self.kodi.stop)

    def handler(self, data):
        logger.debug('handler data: {}'.format(str(data)))
        responseData = { 'status': 'ok' }
        if data['type'] == 'command':
            if data['commandType'] == 'searchAndPlay':
                self.search_and_play_handler(data.get('filter', {}))
            elif data['commandType'] == 'searchAndDisplay':
                self.search_and_display_handler(data.get('filter', {}))
            elif data['commandType'] == 'next':
                self.next_handler()
            elif data['commandType'] == 'previous':
                self.previous_handler()
            elif data['commandType'] == 'startOver':
                self.start_over_handler()
            elif data['commandType'] == 'pause':
                self.pause_handler()
            elif data['commandType'] == 'resume':
                self.resume_handler()
            elif data['commandType'] == 'stop':
                self.stop_handler()
            else:
                responseData = { 'status': 'error', 'error': 'unknown_command' }
        else:
            responseData = { 'status': 'error', 'error': 'unknown_command' }

        logger.debug('handler responseData: {}'.format(str(responseData)))

        return responseData
