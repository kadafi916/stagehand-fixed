# -----------------------------------------------------------------------------
# net.py - Miscellaneous network helper functions
# -----------------------------------------------------------------------------
import sys
import os
import io
import re
import logging
import asyncio
import aiohttp

log = logging.getLogger('http')


async def _download(url, target=None, resume=True, progress=None, **kwargs):
    if not target:
        target = io.BytesIO()
    elif not hasattr(target, 'write'):
        target = open(target, 'ab+' if resume else 'wb')

    try:
        headers = kwargs.setdefault('headers', {})
        if resume:
            pos = target.seek(0, io.SEEK_END)
            if pos > 0:
                headers['Range'] = 'bytes={}-'.format(pos)
            expected_pos = pos
        else:
            target.seek(0, io.SEEK_SET)
            target.truncate()
            expected_pos = 0

        log.info('fetching %s', url)
        method = kwargs.pop('method', 'GET')
        data = kwargs.pop('data', None)
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, data=data, **kwargs) as response:
                if response.status >= 300:
                    raise aiohttp.ClientResponseError(
                        response.request_info, response.history, status=response.status)

                m = re.search(r'bytes +(\d+).*/(\d+|\*)', response.headers.get('content-range', ''))
                if m:
                    pos, size = m.groups()
                    pos = int(pos)
                    if progress:
                        if size != '*':
                            progress.set(pos=pos, max=int(size))
                        else:
                            progress.set(pos=pos)
                    if pos < expected_pos:
                        target.seek(pos, io.SEEK_SET)
                        target.truncate()
                else:
                    if expected_pos > 0:
                        raise aiohttp.ClientResponseError(
                            response.request_info, response.history, status=416)
                    if progress:
                        progress.set(max=int(response.headers.get('content-length', 0)))

                while True:
                    chunk = await response.content.read(65536)
                    if not chunk:
                        break
                    if progress:
                        progress.update(diff=len(chunk))
                    target.write(chunk)

                if isinstance(target, io.BytesIO):
                    return response.status, target.getvalue()
                else:
                    return response.status, response
    finally:
        if not isinstance(target, io.BytesIO):
            target.close()


async def download(url, target=None, resume=True, retry=0, progress=None, noraise=True, **kwargs):
    while retry >= 0:
        status = 0
        try:
            status, response = await _download(url, target, resume, progress, **kwargs)
            return status, response
        except aiohttp.ClientResponseError as e:
            status = e.status
            if status == 416 and resume:
                resume = False
                continue
            elif retry == 0:
                if noraise:
                    return 0, str(e)
                else:
                    raise
            errmsg = str(e)
        except (aiohttp.ClientConnectionError, OSError) as e:
            if retry == 0:
                if noraise:
                    return 0, str(e)
                else:
                    raise
            errmsg = str(e)

        if status != 0:
            errmsg = 'status %d' % status
            if status < 500 or status >= 600:
                return status, None

        log.warning('download failed (%d retries left): %s', retry, errmsg)
        retry -= 1

    log.warning('BUG: download retry loop did not terminate properly')
    return 0, None
