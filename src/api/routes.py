from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from aiohttp import web
from aiohttp.web import Response

from utils.cors import add_cors_routes
from utils.limiter import Limiter
from utils.sf3d import generate

if TYPE_CHECKING:
  from utils.extra_request import Request

with open("config.toml") as f:
  config = tomllib.loads(f.read())
  frontend_version = config["pages"]["frontend_version"]
  exempt_ips = config["srv"]["ratelimit_exempt"]
  api_version = config["srv"]["api_version"]

limiter = Limiter(exempt_ips=exempt_ips)
routes = web.RouteTableDef()

@routes.get("/srv/get/")
@limiter.limit("60/m")
async def get_lp_get(request: Request) -> Response:
  packet = {
    "frontend_version": frontend_version,
    "api_version": api_version,
  }

  if request.app.POSTGRES_ENABLED:
    database_size_record = await request.conn.fetchrow("SELECT pg_size_pretty ( pg_database_size ( current_database() ) );")
    packet["db_size"] = database_size_record.get("pg_size_pretty","-1 kB")

  return web.json_response(packet)

@routes.post("/sf3d/")
@limiter.limit("10/m")
async def post_sf3d(request: Request) -> Response:
  png_bytes = await request.read()
  filename = request.query.get("filename", "converted.stl")
  filename = ".".join(filename.split(".")[:-1])

  try:
    result = await generate(png_bytes)
  except Exception as e:
    return Response(status=500, text=str(e))
  
  resp: web.StreamResponse = web.StreamResponse()
  resp.headers["Content-Type"] = "model/stl"
  resp.headers["Content-Disposition"] = f"attachment; filename*={filename}.stl"
  await resp.prepare(request)
  await resp.write(result)
  return resp

async def setup(app: web.Application) -> None:
  for route in routes:
    app.LOG.info(f"  ↳ {route}")
  app.add_routes(routes)
  add_cors_routes(routes, app)