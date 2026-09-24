import asyncio
import httpx


async def main():
    url = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"

    data = {
        "accion": "consPorRuc",
        "razSoc": "",
        "nroRuc": "20371672151",
        "nrodoc": "",
        "token": "42qbxo7i9t8zdva1im6geolkygf3gmirpcl9s8wv49lmt5qndmoq",
        "contexto": "ti-it",
        "modo": "1",
        "rbtnTipo": "1",
        "search1": "20371672151",
        "tipdoc": "1",
        "search2": "",
        "search3": "",
        "codigo": "",
    }

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-language": "es,es-ES;q=0.9,en;q=0.8",
        "content-type": "application/x-www-form-urlencoded",
        "referer": "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp",
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.post(
            url,
            headers=headers,
            data=data,
        )

        response.raise_for_status()

        html = response.text
        print(html)


asyncio.run(main())