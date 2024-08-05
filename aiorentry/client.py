from types import TracebackType
from typing import Any, Type

from aiohttp import (
    ClientResponse, ClientResponseError, ClientSession, DummyCookieJar, web,
)
from typing_extensions import Self
from yarl import URL

from aiorentry.models import Page

DEFAULT_BASE_URL = 'https://rentry.org'
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_POST_BODY_NAME = 'csrfmiddlewaretoken'


class Client:

    __base_url: URL
    __session: ClientSession
    __custom_session: bool = False

    def __init__(
        self,
        base_url: str | None = None,
        *,
        session: ClientSession | None = None,
    ):
        if base_url is None:
            base_url = DEFAULT_BASE_URL

        self.__base_url = URL(base_url)
        self.__headers = {'Referer': str(self.__base_url)}

        if session is not None:
            self.__session = session
            self.__custom_session = True

    async def setup(self) -> None:
        if not self.__custom_session:
            jar = DummyCookieJar()
            self.__session = ClientSession(cookie_jar=jar)

    async def close(self) -> None:
        if not self.__custom_session:
            await self.__session.close()

    async def __aenter__(self) -> Self:
        await self.setup()

        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        await self.close()

    async def __get_csrf_token(self) -> str:
        api_url = self.__base_url

        async with self.__session.get(
            api_url,
            raise_for_status=True,
        ) as response:
            return response.cookies[CSRF_COOKIE_NAME].value

    async def __handle_response(self, response: ClientResponse) -> Any:
        data = await response.json(content_type=None)
        status = int(data['status'])

        if status == 200:
            return data

        raise ClientResponseError(
            response.request_info,
            response.history,
            status=status,
            message=data.get('errors', data['content']),
            headers=response.headers,
        )

    async def new_page(
        self,
        text: str,
        *,
        url: str | None = None,
        edit_code: str | None = None,
    ) -> Page:
        token = await self.__get_csrf_token()

        payload = {
            CSRF_POST_BODY_NAME: token,
            'url': url or '',
            'edit_code': edit_code or '',
            'text': text,
        }

        cookies = {
            CSRF_COOKIE_NAME: token,
        }

        api_url = self.__base_url.with_path('/api/new')

        async with self.__session.post(
            api_url,
            headers=self.__headers,
            cookies=cookies,
            data=payload,
            raise_for_status=True,
        ) as response:
            data = await self.__handle_response(response)
            page_url = URL(data['url'])

            return Page(
                url=page_url.parts[1],
                edit_code=data['edit_code'],
                text=text,
            )

    async def edit_page(
        self,
        text: str,
        *,
        url: str,
        edit_code: str,
    ) -> Page:
        token = await self.__get_csrf_token()

        payload = {
            CSRF_POST_BODY_NAME: token,
            'edit_code': edit_code,
            'text': text,
        }

        cookies = {
            CSRF_COOKIE_NAME: token,
        }

        api_url = self.__base_url.with_path(f'/api/edit/{url}')

        async with self.__session.post(
            api_url,
            headers=self.__headers,
            cookies=cookies,
            data=payload,
            raise_for_status=True,
        ) as response:
            await self.__handle_response(response)

            return Page(
                url=url,
                edit_code=edit_code,
                text=text,
            )

    async def delete_page(
        self,
        *,
        url: str,
        edit_code: str,
    ) -> bool:
        token = await self.__get_csrf_token()

        payload = {
            CSRF_POST_BODY_NAME: token,
            'text': '',
            'edit_code': edit_code,
            'new_edit_code': '',
            'new_url': '',
            'new_modify_code': '',
            'delete': 'delete',
        }

        cookies = {
            CSRF_COOKIE_NAME: token,
        }

        api_url = self.__base_url.with_path(f'/{url}/edit')

        async with self.__session.post(
            api_url,
            headers=self.__headers,
            cookies=cookies,
            data=payload,
            raise_for_status=True,
            allow_redirects=False,
        ) as response:
            return response.status == web.HTTPFound.status_code

    async def raw(
        self,
        url: str,
    ) -> str:
        api_url = self.__base_url.with_path(f'/api/raw/{url}')

        async with self.__session.get(
            api_url,
            raise_for_status=True,
        ) as response:
            data = await self.__handle_response(response)

            return data['content']

    async def png(
        self,
        url: str,
    ) -> bytes:
        api_url = self.__base_url.with_path(f'/{url}/png')

        async with self.__session.get(
            api_url,
            raise_for_status=True,
        ) as response:
            return await response.read()

    async def pdf(
        self,
        url: str,
    ) -> bytes:
        api_url = self.__base_url.with_path(f'/{url}/pdf')

        async with self.__session.get(
            api_url,
            raise_for_status=True,
        ) as response:
            return await response.read()
