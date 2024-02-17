import aio_pika
from pydantic import BaseModel
from fastapi import FastAPI, Response, status

from fod_common.enums import RPCStatus

app = FastAPI()

class Post(BaseModel):
    name: str
    description: str
    correlation_id: str

async def get_rmq_session() -> aio_pika.Connection:
    connection = await aio_pika.connect_robust(
        "amqp://rmuser:rmpassword@rabbitmq/", #TODO: get userpass from the config
        client_properties={"connection_name": "caller"}
    )

    return connection


PENDING_UPLOAD_EXPIRATION = 600000
@app.get("/api/requestUpload")
async def request_upload():
    connection = await get_rmq_session()

    async with connection:
        channel = await connection.channel()

        rpc = await aio_pika.patterns.RPC.create(channel)

        response = await rpc.proxy.request_upload(expiration=PENDING_UPLOAD_EXPIRATION)

    return response

@app.post("/api/ackUpload")
async def ack_upload(post: Post, response: Response):
    connection = await get_rmq_session()

    async with connection:
        channel = await connection.channel()

        rpc = await aio_pika.patterns.RPC.create(channel)

        result = await rpc.proxy.ack_upload(name=post.name,
                                   description=post.description,
                                   correlation_id=post.correlation_id)
    
    if result["status"] == RPCStatus.OK:
        return
    if result["status"] == RPCStatus.BAD_REQUEST:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return result["message"]