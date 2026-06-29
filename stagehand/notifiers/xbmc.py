import json
import socket
import urllib
import logging
import re
import os
import time
import asyncio

from ..config import config
from ..toolbox import tobytes, tostr
from ..toolbox.net import download
from .base import NotifierBase, NotifierError
from .xbmc_config import config as modconfig

__all__ = ['Notifier']

log = logging.getLogger('stagehand.notifiers.xbmc')

class Notifier(NotifierBase):
    def __init__(self, loop=None):
        super().__init__(loop)
        self._rpcver = 0

    async def _jsonrpc(self, method, params):
        request = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': 1
        }
        log.debug2('issuing JSON-RPC method=%s params=%s', method, params)
        buf = tobytes(json.dumps(request))
        self._rpcwriter.write(buf)
        data = await asyncio.wait_for(self._rpcreader.read(2048), timeout=5)
        try:
            response = json.loads(tostr(data))
            return response['result']
        except (ValueError, KeyError):
            log.error('unexpected response from JSON-RPC: %s...', data[:1000])


    async def _wait_for_idle(self, timeout=120):
        t0 = time.time()
        while time.time() - t0 < timeout:
            result = await self._jsonrpc('XBMC.GetInfoBooleans', {'booleans': ['library.isscanning']})
            if not result or result.get('library.isscanning') != True:
                return True
            log.debug2('XBMC busy scanning, waiting')
            await asyncio.sleep(1)
        return False


    async def _send_notification(self, title, msg):
        result = await self._jsonrpc('GUI.ShowNotification', [title, msg])
        return result


    async def _update_library(self, path=""):
        path = path + '/' if path and not path.endswith('/') else path
        result = await self._jsonrpc('VideoLibrary.scan', [path])
        return result


    async def _do_notify(self, episodes):
        self._rpcreader, self._rpcwriter = await asyncio.open_connection(str(modconfig.hostname), int(modconfig.tcp_port))
        result = await self._jsonrpc('JSONRPC.Version', [])
        self._rpcver = result.get('version', {'major': 0})['major']
        log.warning('rpc version %d', self._rpcver)

        notify_config = {
            'Application': False,
            'GUI': False,
            'System': False,
            'Player': False,
            'AudioLibrary': False,
            'VideoLibrary': False,
            'Other': False
        }
        await self._jsonrpc('JSONRPC.SetConfiguration', {'notifications': notify_config})

        dirs = set(ep.series.path for ep in episodes)

        if modconfig.tvdir:
            frm = os.path.normpath(config.misc.tvdir) + '/'
            to = os.path.normpath(modconfig.tvdir) + '/'
            dirs = [re.sub(r'^' + frm, to, dir) for dir in dirs]

        await self._wait_for_idle()
        if modconfig.individual:
            for dir in dirs:
                await self._update_library(dir)
                await self._wait_for_idle()
        else:
            await self._update_library()

        if modconfig.notify:
            if len(episodes) == 1:
                msg = 'New episode for {} available.'.format(episodes[0].series.name)
            else:
                msg = '{} new episodes added to library.'.format(len(episodes))
            await self._send_notification('New TV Episodes', msg)

        self._rpcwriter.close()
        log.debug('updated library with %d episodes', len(episodes))


    async def _notify(self, episodes):
        try:
            await self._do_notify(episodes)
        except asyncio.TimeoutError:
            log.error('timed out waiting for XBMC server')
        else:
            log.info('send xbmc notification')
