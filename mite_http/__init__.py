from collections import deque
from acurl import EventLoop
import logging
import asyncio

from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class SessionPool:
    """No longer actually goes pooling as this is built into acurl.

    API just left in place. TODO: Will need a refactor"""
    def __init__(self):
        self._el = EventLoop()
        self._pool = deque()

    @asynccontextmanager
    async def session_context(self, context):
        context.http = await self._checkout(context)
        yield
        await self._checkin(context.http)
        del context.http

    def decorator(self, func):
        async def wrapper(ctx, *args, **kwargs):
            async with self.session_context(ctx):
                return await func(ctx, *args, **kwargs)
        return wrapper

    async def _checkout(self, context):
        session = self._el.session()

        def response_callback(r):
            context.send(
                'http_curl_metrics',
                start_time=r.start_time,
                effective_url=r.url,
                response_code=r.status_code,
                dns_time=r.namelookup_time,
                connect_time=r.connect_time,
                tls_time=r.appconnect_time,
                transfer_start_time=r.pretransfer_time,
                first_byte_time=r.starttransfer_time,
                total_time=r.total_time,
                primary_ip=r.primary_ip,
                method=r.request.method
            )
        session.set_response_callback(response_callback)
        return session

    async def _checkin(self, session):
        pass


def get_session_pool():
    # We memoize the function by event loop.  This is because, in unit tests,
    # there are multiple event loops in circulation.
    try:
        return get_session_pool._session_pools[asyncio.get_event_loop()]
    except KeyError:
        sp = SessionPool()
        get_session_pool._session_pools[asyncio.get_event_loop()] = sp
        return sp
get_session_pool._session_pools = {}


def mite_http(func):
    return get_session_pool().decorator(func)
