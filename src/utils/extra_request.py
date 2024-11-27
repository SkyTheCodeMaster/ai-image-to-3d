from __future__ import annotations

from typing import TYPE_CHECKING

from aiohttp.web import Application as BaseApplication
from aiohttp.web import Request as BaseRequest

if TYPE_CHECKING:
  from logging import Logger
  from aiohttp import ClientSession

class Application(BaseApplication):
  LOG: Logger
  cs: ClientSession

class Request(BaseRequest):
  app: Application
  LOG: Logger
  session: ClientSession