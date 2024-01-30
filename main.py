
from datetime import datetime, timedelta
import asyncio
import platform
import argparse
import json
from timing import async_timed
from time import time
from concurrent.futures import ProcessPoolExecutor


import aiohttp
from aiofile import async_open

# RESULT = []

parser = argparse.ArgumentParser(description="Currency_Info")
parser.add_argument("--days", "-d", help="Days ago", required=True)
parser.add_argument("--addCurrency", "-c",
                    help="Add one more currency to the final list (comma-separated). Example USD,EUR,KZT,CAD,CNY", default=None)

print(parser.parse_args())
args = vars(parser.parse_args())
print(args)
days_ago = args.get("days")

try:
    added_currencies = args.get('addCurrency')
    if added_currencies:
        added_currencies = added_currencies.split(',')
        added_currencies = [currency.upper() for currency in added_currencies]
        print(added_currencies)
except Exception as ex:
    print(ex)

# async def producer(q: asyncio.Queue, url):
#     await asyncio.sleep(0.1)
#     await q.put(url)


# async def consumer(q: asyncio.Queue):
#     global RESULT
#     while True:
#         num = await q.get()
#         res = await request_to(num)
#         RESULT.append(res)
#         q.task_done()


class HTTPerror(Exception):
    pass


async def parsing_data(data: list[dict]):

    await asyncio.sleep(0)
    date = data['date']
    new_dict = {date: {}}

    for item in data["exchangeRate"]:
        currency = item["currency"]
        sale = item["saleRateNB"]
        purchase = item["purchaseRateNB"]

        if currency in ("EUR", "USD") or (added_currencies and currency in added_currencies):
            if sale is not None:
                new_dict[date][currency] = {"sale": sale}

            if purchase is not None:
                new_dict[date][currency]["purchase"] = purchase

    return new_dict


async def request_to(url: str = None):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    return await parsing_data(result)
                    # return result
                else:
                    raise HTTPerror(
                        f"Error code raised: {response.status} on url: {url}")
        except:
            raise HTTPerror(
                f"Error code raised: {response.status} on url: {url}")


# @async_timed("____________________****____________________")
async def main(days_ago: int):

    requests = []
    # urls = []
    if days_ago > 10 or days_ago < 0:
        print(
            f"Entered days - {days_ago}.\nSorry but script can only provide data not more than 10 days ago and greater than '0'.")
        days_ago = 10

    for day in range(days_ago, -1, -1):
        date = datetime.now() - timedelta(days=day)
        embed = date.strftime("%d.%m.%Y")
        # urls.append(
        #     f"https://api.privatbank.ua/p24api/exchange_rates?json&date={embed}")
        requests.append(request_to(
            f"https://api.privatbank.ua/p24api/exchange_rates?json&date={embed}"))

        # task = asyncio.create_task(request_to(
        #     f"https://api.privatbank.ua/p24api/exchange_rates?json&date={embed}"))
        # requests.append(task)

    try:
        # 1
        # loop = asyncio.get_running_loop()
        # with ProcessPoolExecutor(10) as pool:
        #     futures = [loop.run_in_executor(
        #         pool, request_to, url) for url in urls]
        #     print(futures)
        # result = await asyncio.gather(*futures, return_exceptions=True)
        # print(result)

        # 2
        # queue = asyncio.Queue()
        # loop = asyncio.get_running_loop()
        # consumer_tasks = [loop.create_task(consumer(queue)) for _ in range(5)]
        # producer_tasks = [loop.create_task(
        #     producer(queue, url)) for url in urls]
        # await asyncio.gather(*producer_tasks)
        # await queue.join()
        # [task.cancel() for task in consumer_tasks]

        # 3
        result = await asyncio.gather(*requests)
        async with async_open("result.json", "w+") as afh:
            await afh.write(json.dumps(result, indent=4))
    except HTTPerror as ex:
        print(ex)
        return None


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main(int(days_ago)))
    except ValueError:
        print(
            f"Not valid entered data '{days_ago}'. You must enter a number. Try again later!")
