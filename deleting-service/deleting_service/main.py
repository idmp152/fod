from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI

from fod_common import models


conn_pool: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn_pool["rmq_conn"] = await aio_pika.connect_robust(
        "amqp://rmuser:rmpassword@rabbitmq/", #TODO: get userpass from the config
        client_properties={"connection_name": "caller"}
    )
    print("connection initialized")
    yield
    print("connection deinitialized")
    await conn_pool["rmq_conn"].close()
    conn_pool.clear()

app = FastAPI(lifespan=lifespan)

PENDING_UPLOAD_EXPIRATION = 600000
@app.get("/api/requestDelete")
async def request_upload(post_id: int):
    async with conn_pool["rmq_conn"]:
        channel = await conn_pool["rmq_conn"].channel()

        master = aio_pika.patterns.Master(channel)

        await master.proxy.request_delete(post_id=post_id)