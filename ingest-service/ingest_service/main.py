from contextlib import asynccontextmanager

import aio_pika
from pydantic import BaseModel
from fastapi import FastAPI, Response, status

from fod_common.enums import RPCStatus

class Post(BaseModel):
    name: str
    description: str
    correlation_id: str

shared_pool: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    shared_pool["rmq_conn"] = await aio_pika.connect_robust(
        "amqp://rmuser:rmpassword@rabbitmq/", #TODO: get userpass from the config
        client_properties={"connection_name": "caller"}
    )
    shared_pool["rmq_channel"] = await shared_pool["rmq_conn"].channel()
    shared_pool["rmq_rpc"] = await aio_pika.patterns.RPC.create(shared_pool["rmq_channel"])

    yield

    await shared_pool["rmq_conn"].close()
    shared_pool.clear()

app = FastAPI(lifespan=lifespan)


PENDING_UPLOAD_EXPIRATION = 600000
@app.get("/api/requestUpload")
async def request_upload():
    result = await shared_pool["rmq_rpc"].proxy.request_upload(expiration=PENDING_UPLOAD_EXPIRATION)

    return result

@app.post("/api/ackUpload")
async def ack_upload(post: Post, response: Response):
    result = await shared_pool["rmq_rpc"].proxy.ack_upload(name=post.name,
                                description=post.description,
                                correlation_id=post.correlation_id)
    
    if result["status"] == RPCStatus.OK:
        return
    if result["status"] == RPCStatus.BAD_REQUEST:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return result["message"]