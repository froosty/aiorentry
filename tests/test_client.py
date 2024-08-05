import pytest
from aiohttp import ClientResponseError


@pytest.mark.anyio
async def test_new_page(client, pages_registry):
    page = await client.new_page('##Hello')

    created_page = await pages_registry.get(page.url)

    assert created_page == page


@pytest.mark.anyio
async def test_new_page_custom_url_edit_code(
    client,
    pages_registry,
    randomstr,
):
    url = randomstr()
    edit_code = randomstr()

    page = await client.new_page(
        '##Hello',
        url=url,
        edit_code=edit_code,
    )

    created_page = await pages_registry.get(page.url)

    assert created_page == page


@pytest.mark.anyio
async def test_new_page_url_exists(client, pages_registry, generate_page):
    page = generate_page()
    await pages_registry.add(page)

    with pytest.raises(ClientResponseError) as exc_info:
        await client.new_page(
            page.text,
            url=page.url,
        )

    assert exc_info.value.status == 400
    assert exc_info.value.message == 'This URL is already in use.'


@pytest.mark.anyio
async def test_edit_page(client, pages_registry, generate_page):
    page = generate_page()
    await pages_registry.add(page)

    page.text = f'Updated {page.text}'

    await client.edit_page(
        page.text,
        url=page.url,
        edit_code=page.edit_code,
    )

    updated_page = await pages_registry.get(page.url)

    assert updated_page == page


@pytest.mark.anyio
async def test_edit_page_not_found(client, generate_page):
    page = generate_page()

    with pytest.raises(ClientResponseError) as exc_info:
        await client.edit_page(
            page.text,
            url=page.url,
            edit_code=page.edit_code,
        )

    assert exc_info.value.status == 404
    assert exc_info.value.message == f'Entry {page.url} does not exist'


@pytest.mark.anyio
async def test_edit_page_bad_edit_code(client, pages_registry, generate_page):
    page = generate_page()
    await pages_registry.add(page)

    with pytest.raises(ClientResponseError) as exc_info:
        await client.edit_page(
            page.text,
            url=page.url,
            edit_code=page.edit_code * 2,
        )

    assert exc_info.value.status == 400
    assert exc_info.value.message == 'Invalid edit code.'


@pytest.mark.anyio
async def test_delete_page(client, pages_registry, generate_page):
    page = generate_page()
    await pages_registry.add(page)

    is_deleted = await client.delete_page(
        url=page.url,
        edit_code=page.edit_code,
    )

    assert not await pages_registry.exists(page.url)
    assert is_deleted


@pytest.mark.anyio
async def test_delete_page_not_found(client, generate_page):
    page = generate_page()

    is_deleted = await client.delete_page(
        url=page.url,
        edit_code=page.edit_code,
    )

    assert not is_deleted


@pytest.mark.anyio
async def test_delete_page_bad_edit_code(
    client,
    pages_registry,
    generate_page,
):
    page = generate_page()
    await pages_registry.add(page)

    is_deleted = await client.delete_page(
        url=page.url,
        edit_code=page.edit_code * 2,
    )

    assert await pages_registry.exists(page.url)
    assert not is_deleted


@pytest.mark.anyio
async def test_raw(client, pages_registry, generate_page):
    page = generate_page()
    await pages_registry.add(page)

    text = await client.raw(page.url)

    assert text == page.text


@pytest.mark.anyio
async def test_raw_not_found(client, generate_page):
    page = generate_page()

    with pytest.raises(ClientResponseError) as exc_info:
        await client.raw(page.url)

    assert exc_info.value.status == 404
    assert exc_info.value.message == f'Entry {page.url} does not exist'


@pytest.mark.anyio
async def test_png(client, pages_registry, generate_page):
    page = generate_page()
    await pages_registry.add(page)

    file_content = await client.png(page.url)

    assert file_content == page.text.encode('utf-8')


@pytest.mark.anyio
async def test_png_not_found(client, generate_page):
    page = generate_page()

    with pytest.raises(ClientResponseError):
        await client.png(page.url)


@pytest.mark.anyio
async def test_pdf(client, pages_registry, generate_page):
    page = generate_page()
    await pages_registry.add(page)

    file_content = await client.pdf(page.url)

    assert file_content == page.text.encode('utf-8')


@pytest.mark.anyio
async def test_pdf_not_found(client, generate_page):
    page = generate_page()

    with pytest.raises(ClientResponseError):
        await client.pdf(page.url)
