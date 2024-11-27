from __future__ import annotations

import asyncio
import logging
import random
import string

import aiofiles
import aiofiles.os
import trimesh

MODEL_LOCK = asyncio.Lock()
SF3D_PATH = "sf3d/run.py"
LOG = logging.getLogger(__name__)


def make_job_id() -> str:
  pool: str = string.ascii_letters + string.digits
  return "".join(random.choices(pool, k=16))


async def generate(png_data: bytes) -> bytes:
  "Take a png image, return an STL"
  async with MODEL_LOCK:
    job_id = make_job_id()
    await aiofiles.os.makedirs("/tmp/sf3d", exist_ok=True)
    async with aiofiles.open(f"/tmp/sf3d/{job_id}.png", "wb") as f:
      await f.write(png_data)
    proc = await asyncio.create_subprocess_shell(
      f"venv/bin/python {SF3D_PATH} /tmp/sf3d/{job_id}.png --output-dir /tmp/sf3d/",
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )
    returncode = await proc.wait()

    if returncode != 0:
      LOG.error("SF3D Failure!")
      LOG.error((await proc.stderr.read()).decode())
      LOG.error((await proc.stdout.read()).decode())
      return

    # Now convert to STL
    # This is also why we need the lock, the program only outputs to "mesh.glb", no option for specifying a name.
    mesh = trimesh.load("/tmp/sf3d/mesh.glb")
    mesh.export(f"/tmp/sf3d/{job_id}.stl")

    async with aiofiles.open(f"/tmp/sf3d/{job_id}.stl", "rb") as f:
      stl_bytes = await f.read()
  try:
    await aiofiles.os.remove(f"/tmp/sf3d/{job_id}.png")
    await aiofiles.os.remove(f"/tmp/sf3d/{job_id}.stl")
    await aiofiles.os.remove("/tmp/sf3d/mesh.glb")
  except Exception:
    pass

  return stl_bytes