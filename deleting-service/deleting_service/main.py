from contextlib import asynccontextmanager

import aio_pika
import redis
from fastapi import FastAPI, HTTPException, status
from tortoise import Tortoise

from fod_common import models, authentication

shared_pool: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    shared_pool["rmq_conn"] = await aio_pika.connect_robust("amqp://rmuser:rmpassword@rabbitmq/") #TODO: get userpass from the config
    shared_pool["rmq_channel"] = await shared_pool["rmq_conn"].channel()
    shared_pool["rmq_master"] = aio_pika.patterns.Master(shared_pool["rmq_channel"])

    await Tortoise.init(
        db_url="postgres://user:password@postgres_primary:5432/postgres", #TODO: get from env
        modules={"models": ["fod_common.models"]}
    )
    await Tortoise.generate_schemas()

    yield

    await Tortoise.close_connections()
    await shared_pool["rmq_conn"].close()
    shared_pool.clear()

app = FastAPI(lifespan=lifespan, root_path="/deleting")

@app.post("/requestDelete")
async def request_upload(user: authentication.user_dependency, post_id: int):
    post = await models.Post.filter(id=post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    if post.author_id != user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not the author.")
    
    cache: redis.Redis = shared_pool["redis"]
    cache.delete(f"posts:{post_id}")
    post.pending_delete = True
    await post.save()
    await shared_pool["rmq_master"].proxy.request_delete(post_id=post_id)