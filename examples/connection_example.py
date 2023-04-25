import argparse
import asyncio
import logging
from os.path import abspath, dirname
from sys import path

path.insert(1, dirname(dirname(abspath(__file__))))

from aiotaika import TaikaClient  # NOQA

parser = argparse.ArgumentParser(description="Taika AIO library example")
parser.add_argument("host", help="hostname of Taika centralunit")
parser.add_argument("username", help="Username for centralunit login")
parser.add_argument("password", help="Password for centralunit login")
parser.add_argument("--debug", help="enable debug logging", action="store_true")
args = parser.parse_args()


async def main() -> None:
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)-15s %(levelname)-5s %(name)s -- %(message)s",
        )
    async with TaikaClient(
        host=args.host, username=args.username, password=args.password
    ) as taika:
        print(f"Connection success to {taika}!")


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
