import asyncio
import os

import aio_pika
from minio import Minio
from tortoise import Tortoise

from fod_common import models


async def request_delete(post_id: int):
    post = await models.Post.filter(id=post_id).first()
    s3_client = Minio("minio:9000", access_key=os.getenv("AWS_ACCESS_KEY_ID"), secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"), secure=False)
    s3_client.remove_object(post.bucket, post.filename)
    await post.delete()


async def main() -> None:
    await Tortoise.init(
        db_url="postgres://user:password@postgres_primary:5432/postgres", #TODO: get from env
        modules={"models": ["fod_common.models"]}
    )
    await Tortoise.generate_schemas()

    rmq_connection = await aio_pika.connect_robust("amqp://rmuser:rmpassword@rabbitmq/") #TODO: get from env 

    channel = await rmq_connection.channel()

    master = aio_pika.patterns.Master(channel)
    await master.create_worker("request_delete", request_delete, auto_delete=True)

    try:
        await asyncio.Future()
    finally:
        await rmq_connection.close()
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())