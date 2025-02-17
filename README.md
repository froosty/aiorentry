# aiorentry

Asynchronous API client for [rentry.co](https://rentry.co) (mirror: [rentry.org](https://rentry.org))

[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/froosty/aiorentry/lint_and_test.yml)](https://github.com/froosty/aiorentry/actions/workflows/lint_and_test.yml)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/froosty/aiorentry/daily_test.yml?label=daily%20check)](https://github.com/froosty/aiorentry/actions/workflows/daily_test.yml)
[![codecov](https://codecov.io/gh/froosty/aiorentry/graph/badge.svg?token=FJBRTOQ2HR)](https://codecov.io/gh/froosty/aiorentry)
[![PyPI - Version](https://img.shields.io/pypi/v/aiorentry)](https://pypi.org/project/aiorentry/)
[![GitHub License](https://img.shields.io/github/license/froosty/aiorentry)](https://github.com/froosty/aiorentry/blob/main/LICENSE)

## About

This package allows you to interact with the [rentry.co](https://rentry.co) (or [rentry.org](https://rentry.org)) service.

Rentry.co is a markdown pastebin and publishing service that offers features such as previews, custom URLs, and editing.

**Please note** that this library is not developed by the official authors of rentry.co. It replicates the functionality of the [official console utility](https://github.com/radude/rentry), but provides it as an asynchronous API client. With this package you can manage your pages: create, edit and delete, as well as get raw text. All directly from your asynchronous Python application.

## Installation

```bash
pip install aiorentry
```

## Setup client

You can setup client in 2 ways:

### As classic object

> [!CAUTION]
> If you prefer the classic way, you should call `await client.setup()` during initialization and `await client.close()` during completion

```python
import asyncio

from aiorentry.client import Client


async def main():
    client = Client('https://rentry.co')
    await client.setup()

    # Your code here

    await client.close()


asyncio.run(main())
```

### As async context manager

```python
import asyncio

from aiorentry.client import Client


async def main():
    async with Client('https://rentry.co') as client:
        # Your code here


asyncio.run(main())
```

## Examples

### Create new page

```python
...
# Create new page
page = await client.new_page(
    '## Hello world from awesome API',
)

print(page)
...
```

```bash
Page(url='m2e2wpe8', edit_code='hUHeRUei', text='## Hello world from awesome API')
```

```python
...
# Create new page with custom url and edit_code
awesome_page = await client.new_page(
    '## Hello world from awesome API',
    url='awesome-url',
    edit_code='qwerty=)'
)

print(awesome_page)
...
```

```bash
Page(url='awesome-url', edit_code='qwerty=)', text='## Hello world from awesome API')
```

### Edit page

```python
...
# Edit page
await client.edit_page(
    '### Updated Hello world',
    url='awesome-url',
    edit_code='qwerty=)',
)
...
```

### Delete page

```python
...
# Delete page
await client.delete_page(
    url='awesome-url',
    edit_code='qwerty=)',
)
...
```

### Get raw page text

> [!NOTE]
> This rentry functionality has limitations now. You can't just view the source text of any page.

```python
...
# Get raw content
content = await client.raw(
    'awesome-url',
    secret_raw_access_code='YOUR_CODE_HERE',  # optional
)
print(content)
...
```

```
### Updated Hello world
```

To view the source text you have 2 options:
1. Specify your personal code inside page metadata. In this case, everyone will have access to the source text of the page through the API.
2. Specify your personal code when trying to get the source text of any page. In this case, you will be able to get the source text, regardless of the metadata of the target page

### Get PDF file

> [!NOTE]
> This functionality has been removed from the library as it is no longer available in the original service via API. This method will be completely removed in the next version.

### Get PNG

> [!NOTE]
> This functionality has been removed from the library as it is no longer available in the original service via API. This method will be completely removed in the next version.

## Custom ClientSession

> [!NOTE]
> By default, a new instance of `aiohttp.ClientSession` will be created automatically. So normally you don't need to worry about this.

If you don't want to automatically create the session object inside the client, you can pass an existing `aiohttp.ClientSession` to the client constructor.

> [!CAUTION]
> If you pass an existing session object to the client constructor, then you should care about releasing resources yourself. \
> **The session will not be closed automatically!** Even if the asynchronous context manager was used.

```python
from aiohttp import ClientSession, TCPConnector
from aiorentry.client import Client

connector = TCPConnector(
    limit=5,  # Just for example
)

session = ClientSession(
    connector=connector,
)


async with Client('https://rentry.co', session=session) as client:
    # Your code here

async with session.get(...) as response:
    # You can still use this session object

```
