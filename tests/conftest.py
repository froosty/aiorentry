import uuid

import pytest
from aiohttp import web

from aiorentry.client import Client
from aiorentry.models import Page

CSRF_COOKIE_NAME = 'csrftoken'
CSRF_POST_BODY_NAME = 'csrfmiddlewaretoken'
SECRET_RAW_ACCESS_CODE_HEADER_NAME = 'rentry-auth'


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
def valid_raw_access_code():
    return uuid.uuid4().hex


@pytest.fixture
def invalid_raw_access_code(valid_raw_access_code):
    invalid = valid_raw_access_code

    while invalid == valid_raw_access_code:
        invalid = uuid.uuid4().hex

    return invalid


@pytest.fixture
def fake_server_db(randomstr):
    class Registry:
        def __init__(self):
            self.__pages = {}

        def exists(self, url: str) -> bool:
            return url in self.__pages

        def get(self, url: str) -> Page:
            if url not in self.__pages:
                raise ValueError

            return self.__pages[url]

        def add(self, page: Page):
            if page.url in self.__pages:
                raise ValueError

            self.__pages[page.url] = page

        def update(self, page: Page):
            if page.url not in self.__pages:
                raise ValueError

            self.__pages[page.url] = page

        def delete(self, url):
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
    fake_server_db,
    randomstr,
    valid_raw_access_code,
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

        if fake_server_db.exists(url):
            return web.json_response({
                'status': '400',
                'content': 'Invalid data',
                'errors': 'This URL is already in use.',
            })

        fake_server_db.add(
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

        if not fake_server_db.exists(url):
            return web.json_response({
                'status': '404',
                'content': f'Entry {url} does not exist',
            })

        old_page = fake_server_db.get(url)

        if edit_code != old_page.edit_code:
            return web.json_response({
                'status': '400',
                'content': 'Invalid data',
                'errors': 'Invalid edit code.',
            })

        fake_server_db.update(
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

        if not fake_server_db.exists(url):
            return web.json_response({
                'status': '404',
                'content': f'Entry {url} does not exist',
            })

        old_page = fake_server_db.get(url)

        if edit_code != old_page.edit_code:
            return web.json_response({
                'status': '400',
                'content': 'Invalid data',
                'errors': 'Invalid edit code.',
            })

        fake_server_db.delete(url)

        return web.Response(
            status=web.HTTPFound.status_code,
        )

    async def raw(request: web.Request):
        url = request.match_info['url']

        if not fake_server_db.exists(url):
            return web.json_response({
                'status': '404',
                'content': f'Entry {url} does not exist',
            })

        access_code = request.headers.get(
            SECRET_RAW_ACCESS_CODE_HEADER_NAME,
            None,
        )

        if access_code is None:
            return web.json_response({
                'status': '403',
                'content': (
                    'This page does not have a SECRET_RAW_ACCESS_CODE set. '
                    'You may still view it over raw by obtaining your own '
                    'code from Rentry admins and setting it as a '
                    'custom header: rentry-auth'
                ),
            })

        if access_code != valid_raw_access_code:
            return web.json_response({
                'status': '403',
                'content': (
                    'Value for SECRET_RAW_ACCESS_CODE not found. '
                    'Please ensure you are using one given to you by '
                    'Rentry admins.'
                ),
            })

        page = fake_server_db.get(url)

        return web.json_response({
            'status': '200',
            'content': page.text,
        })

    async def file(request: web.Request, content_type: str):
        url = request.match_info['url']

        if not fake_server_db.exists(url):
            raise web.HTTPNotFound

        page = fake_server_db.get(url)

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
def cleanup_registry():
    class CleanupRegistry:
        def __init__(self):
            self.pages = {}

        def add(self, url, edit_code):
            self.pages[url] = edit_code

        def remove(self, url):
            del self.pages[url]

        async def cleanup(self, callback):
            pairs = list(self.pages.items())

            for url, edit_code in pairs:
                await callback(url=url, edit_code=edit_code)

        def check_empty(self):
            assert self.pages == {}

    return CleanupRegistry()


@pytest.fixture
def fake_pages_registry(fake_server_db, cleanup_registry):
    class Registry:
        async def exists(self, url):
            return fake_server_db.exists(url)

        async def get_text(self, url):
            page = fake_server_db.get(url)

            return page.text

        async def add(self, page):
            fake_server_db.add(page)
            cleanup_registry.add(page.url, page.edit_code)

    return Registry()


@pytest.fixture
async def client(fake_server_url, cleanup_registry):
    class PatchedClient(Client):
        async def new_page(self, *args, **kwargs):
            page = await super().new_page(*args, **kwargs)

            cleanup_registry.add(page.url, page.edit_code)

            return page

        async def delete_page(self, *args, **kwargs):
            is_deleted = await super().delete_page(*args, **kwargs)

            if is_deleted:
                cleanup_registry.remove(kwargs.get('url'))

            print(f'\n Remove page {kwargs.get("url")}: {is_deleted}')

            return is_deleted

    async with PatchedClient(
        base_url=fake_server_url,
    ) as client:
        yield client

        await cleanup_registry.cleanup(client.delete_page)

        cleanup_registry.check_empty()


@pytest.fixture
def pages_registry(fake_pages_registry):
    return fake_pages_registry
