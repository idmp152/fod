import asyncio
import os
import uuid
from urllib import parse
from datetime import timedelta

import aio_pika
from minio import Minio
from tortoise import Tortoise

from fod_common import models
from fod_common.enums import RPCStatus

BUCKET_NAME = "images"
async def request_upload(expiration: int) -> dict:
    client = Minio("minio:9000", access_key=os.getenv("AWS_ACCESS_KEY_ID"), secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"), secure=False)
    if not client.bucket_exists(BUCKET_NAME):
        client.make_bucket(BUCKET_NAME)

    post = await models.Post.create()

    url = client.presigned_put_object(BUCKET_NAME, str(post.id), timedelta(milliseconds=expiration))
    post.bucket = BUCKET_NAME
    correlation_id = uuid.uuid4()
    post.upload_corr_id = correlation_id
    post.upload_expiration = expiration

    await post.save()

    parsed_url = parse.urlparse(url)
    url = parsed_url._replace(netloc=parsed_url.netloc.replace(parsed_url.hostname, os.getenv("PRESIGNED_URL_HOSTNAME")).replace(str(parsed_url.port), os.getenv("PRESIGNED_URL_PORT"))).geturl()

    return {"url": url, "correlation-id": correlation_id}

async def ack_upload(name: str, description: str, correlation_id: str) -> None:
    if not correlation_id:
        return {"status": RPCStatus.BAD_REQUEST, "message": "Correlation ID must not be empty."}

    post = await models.Post.filter(upload_corr_id=correlation_id).first()
    if not post:
        return {"status": RPCStatus.BAD_REQUEST, "message": "Post not found by correlation ID."}

    post.name = name
    post.description = description
    post.pending_upload = False
    post.upload_corr_id = ""
    await post.save()

    return {"status": RPCStatus.OK}


async def main() -> None:
    await Tortoise.init(
        db_url="postgres://user:password@postgres_primary:5432/postgres", #TODO: get from env
        modules={"models": ["fod_common.models"]}
    )
    await Tortoise.generate_schemas()

    rmq_connection = await aio_pika.connect_robust(
        "amqp://rmuser:rmpassword@rabbitmq/", #TODO: get from env 
        client_properties={"connection_name": "callee"},
    )

    channel = await rmq_connection.channel()

    rpc = await aio_pika.patterns.RPC.create(channel)
    await rpc.register("request_upload", request_upload, auto_delete=True)
    await rpc.register("ack_upload", ack_upload, auto_delete=True)

    try:
        await asyncio.Future()
    finally:
        await rmq_connection.close()
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())