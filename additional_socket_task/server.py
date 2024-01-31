import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp
import websockets
import names
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK
from aiofile import async_open
from aiopath import AsyncPath
# from aiopath import AsyncPath

logging.basicConfig(level=logging.INFO)


async def logging_request():
    apath = AsyncPath("log.txt")
    date = datetime.now()

    parametr = 'a' if await apath.exists() else 'w'
    async with async_open(apath, parametr) as afp:
        await afp.write(f"{date} - command exchange was executed\n")


async def get_data_from_tasks(num: int):

    requests = []
    if num > 10 or num < 0:
        print(
            f"Entered days - {num}.\nSorry but script can only provide data not more than 10 days ago and greater than '0'.")
        num = 10

    for day in range(num, -1, -1):
        date = datetime.now() - timedelta(days=day)
        embed = date.strftime("%d.%m.%Y")
        requests.append(request_to(
            f"https://api.privatbank.ua/p24api/exchange_rates?json&date={embed}"))

    try:
        result = await asyncio.gather(*requests)
        return result
    except Exception as ex:
        print(ex)
        return None


async def parsing_data(data: list[dict]):

    await asyncio.sleep(0)
    date = data['date']
    new_dict = {date: {}}

    for item in data["exchangeRate"]:
        currency = item["currency"]
        sale = item["saleRateNB"]
        purchase = item["purchaseRateNB"]

        if currency in ("EUR", "USD"):
            if sale is not None:
                new_dict[date][currency] = {"sale": sale}

            if purchase is not None:
                new_dict[date][currency]["purchase"] = purchase

    return new_dict


async def request_to(url: str = None, ):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    return await parsing_data(result)
                else:
                    print(f"Exited with code: {response.status} on url: {url}")
        except:
            print(f"Exited with code: {response.status} on url: {url}")


async def get_exchange():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5') as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    print(f"Exited with code: {response.status} on p24api.")
        except:
            print(f"Exited with code: {response.status} on p24api.")


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message == "exchange":
                await logging_request()
                exchange = await get_exchange()
                for item in exchange:
                    await self.send_to_clients(f"{item['ccy']} to {item['base_ccy']}: Buy - {item['buy']}, Sale - {item['sale']}")

            elif message.__contains__("exchange") and len(message) > 9:
                await logging_request()
                temp_l = message.split()
                days_ago = int(temp_l[1])

                try:
                    result = await get_data_from_tasks(days_ago)
                    for item in result:
                        for date, currency in item.items():
                            await self.send_to_clients(f"Date: {date}")
                            for currency, rate in currency.items():
                                await self.send_to_clients(f"{currency}: Sale - {rate['sale']}, Purchase - {rate['purchase']}")
                except Exception as ex:
                    await self.send_to_clients(ex)
            else:
                await self.send_to_clients(f"{ws.name}: {message}")


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
