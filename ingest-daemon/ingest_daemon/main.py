import asyncio
import os
import uuid
from datetime import timedelta
from mimetypes import guess_extension
from urllib import parse

import aio_pika
from minio import Minio
from tortoise import Tortoise

from fod_common import models
from fod_common.enums import RPCStatus

BUCKET_NAME = "images"
async def request_upload(expiration: int, user_id: int, content_type: str) -> dict:
    client = Minio("minio:9000", access_key=os.getenv("AWS_ACCESS_KEY_ID"), secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"), secure=False)
    if not client.bucket_exists(BUCKET_NAME):
        client.make_bucket(BUCKET_NAME)

    post = await models.Post.create()

    extension = guess_extension(content_type)
    url = client.presigned_put_object(BUCKET_NAME, str(post.id) + extension, timedelta(milliseconds=expiration))
    post.filename = str(post.id) + extension
    post.bucket = BUCKET_NAME
    correlation_id = uuid.uuid4()
    post.upload_correlation = correlation_id
    post.upload_expiration = expiration
    post.author_id = user_id

    await post.save()

    parsed_url = parse.urlparse(url)
    url = parsed_url._replace(netloc=parsed_url.netloc.replace(parsed_url.hostname, os.getenv("PRESIGNED_URL_HOSTNAME")).replace(str(parsed_url.port), os.getenv("PRESIGNED_URL_PORT"))).geturl()

    return {"url": url, "correlation-id": correlation_id}

async def ack_upload(name: str, description: str, user_id: int, correlation_id: str) -> None:
    if not correlation_id:
        return {"status": RPCStatus.BAD_REQUEST, "message": "Correlation ID must not be empty."}

    post = await models.Post.filter(upload_correlation=correlation_id).first()
    if not post:
        return {"status": RPCStatus.BAD_REQUEST, "message": "Post not found by correlation ID."}
    
    if post.author_id != user_id:
        return {"status": RPCStatus.UNAUTHORIZED, "message": "User ID of the pending upload post does not match your user ID."}

    post.name = name
    post.description = description
    post.pending_upload = False
    post.upload_correlation = ""
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
    rpc.host_exceptions = True
    await rpc.register("request_upload", request_upload, auto_delete=True)
    await rpc.register("ack_upload", ack_upload, auto_delete=True)

    try:
        await asyncio.Future()
    finally:
        await rmq_connection.close()
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())