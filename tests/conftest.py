import uuid

import pytest
from aiohttp import web

from aiorentry.client import Client
from aiorentry.models import Page

CSRF_COOKIE_NAME = 'csrftoken'
CSRF_POST_BODY_NAME = 'csrfmiddlewaretoken'


@pytest.fixture
def anyio_backend(request):
    return 'asyncio'


@pytest.fixture
def randomstr():
    def factory():
        return uuid.uuid4().hex

    return factory


@pytest.fixture
def generate_page(randomstr):
    def factory():
        return Page(
            url=randomstr(),
            edit_code=randomstr(),
            text=f'##Existing page {randomstr()}',
        )

    return factory


@pytest.fixture
def pages_registry(randomstr):
    class Registry:
        def __init__(self):
            self.__pages = {}

        async def exists(self, url: str) -> bool:
            return url in self.__pages

        async def get(self, url: str) -> Page:
            if url not in self.__pages:
                raise ValueError

            return self.__pages[url]

        async def add(self, page: Page):
            if page.url in self.__pages:
                raise ValueError

            self.__pages[page.url] = page

        async def update(self, page: Page):
            if page.url not in self.__pages:
                raise ValueError

            self.__pages[page.url] = page

        async def delete(self, url):
            if url not in self.__pages:
                raise ValueError

            del self.__pages[url]

    return Registry()


@pytest.fixture
def csrf_token(randomstr):
    return randomstr()


@pytest.fixture
async def fake_server(
    aiohttp_server,
    csrf_token,
    pages_registry,
    randomstr,
):
    async def index(*agrs, **kwargs):
        resp = web.Response()
        resp.set_cookie(CSRF_COOKIE_NAME, csrf_token)

        return resp

    async def new(request: web.Request):
        data = await request.post()

        if data[CSRF_POST_BODY_NAME] != request.cookies[CSRF_COOKIE_NAME]:
            raise web.HTTPForbidden

        url = data['url']

        if not url:
            url = randomstr()

        edit_code = data['edit_code']

        if not edit_code:
            edit_code = randomstr()

        if await pages_registry.exists(url):
            return web.json_response({
                'status': '400',
                'content': 'Invalid data',
                'errors': 'This URL is already in use.',
            })

        await pages_registry.add(
            Page(
                url=url,
                edit_code=edit_code,
                text=data['text'],
            ),
        )

        return web.json_response({
            'status': '200',
            'content': 'OK',
            'url': f'https://rentry.co/{url}',
            'edit_code': edit_code,
        })

    async def edit(request: web.Request):
        data = await request.post()

        if data[CSRF_POST_BODY_NAME] != request.cookies[CSRF_COOKIE_NAME]:
            raise web.HTTPForbidden

        url = request.match_info['url']
        edit_code = data['edit_code']

        if not await pages_registry.exists(url):
            return web.json_response({
                'status': '404',
                'content': f'Entry {url} does not exist',
            })

        old_page = await pages_registry.get(url)

        if edit_code != old_page.edit_code:
            return web.json_response({
                'status': '400',
                'content': 'Invalid data',
                'errors': 'Invalid edit code.',
            })

        await pages_registry.update(
            Page(
                url=url,
                edit_code=edit_code,
                text=data['text'],
            ),
        )

        return web.json_response({
            'status': '200',
            'content': 'OK',
        })

    async def delete(request: web.Request):
        data = await request.post()

        if data[CSRF_POST_BODY_NAME] != request.cookies[CSRF_COOKIE_NAME]:
            raise web.HTTPForbidden

        url = request.match_info['url']
        edit_code = data['edit_code']

        if not await pages_registry.exists(url):
            return web.json_response({
                'status': '404',
                'content': f'Entry {url} does not exist',
            })

        old_page = await pages_registry.get(url)

        if edit_code != old_page.edit_code:
            return web.json_response({
                'status': '400',
                'content': 'Invalid data',
                'errors': 'Invalid edit code.',
            })

        await pages_registry.delete(url)

        return web.Response(
            status=web.HTTPFound.status_code,
        )

    async def raw(request: web.Request):
        url = request.match_info['url']

        if not await pages_registry.exists(url):
            return web.json_response({
                'status': '404',
                'content': f'Entry {url} does not exist',
            })

        page = await pages_registry.get(url)

        return web.json_response({
            'status': '200',
            'content': page.text,
        })

    async def file(request: web.Request, content_type: str):
        url = request.match_info['url']

        if not await pages_registry.exists(url):
            raise web.HTTPNotFound

        page = await pages_registry.get(url)

        return web.Response(
            status=web.HTTPOk.status_code,
            body=page.text.encode('utf-8'),
            content_type=content_type,
        )

    async def pdf(request: web.Request):
        return await file(request, 'application/pdf')

    async def png(request: web.Request):
        return await file(request, 'image/png')

    app = web.Application()
    app.add_routes([
        web.get('/', index),
        web.post('/api/new', new),
        web.post('/api/edit/{url}', edit),
        web.post('/{url}/edit', delete),
        web.get('/api/raw/{url}', raw),
        web.get('/{url}/png', png),
        web.get('/{url}/pdf', pdf),
    ])

    return await aiohttp_server(app)


@pytest.fixture
async def fake_server_url(fake_server):
    return fake_server.make_url('/')


@pytest.fixture
async def client(fake_server_url):
    async with Client(base_url=fake_server_url) as client:
        yield client
