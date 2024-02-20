from contextlib import asynccontextmanager
from mimetypes import guess_extension

import aio_pika
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from tortoise import Tortoise

from fod_common.enums import RPCStatus
from fod_common import authentication, models

class Post(BaseModel):
    name: str
    description: str
    correlation_id: str


class UserUpdateRequest(BaseModel):
    avatar_url: str = ""
    bio: str = ""

shared_pool: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(
        db_url="postgres://user:password@postgres_primary:5432/postgres", #TODO: get from env
        modules={"models": ["fod_common.models"]}
    )
    await Tortoise.generate_schemas()

    shared_pool["rmq_conn"] = await aio_pika.connect_robust(
        "amqp://rmuser:rmpassword@rabbitmq/", #TODO: get userpass from the config
        client_properties={"connection_name": "caller"}
    )
    shared_pool["rmq_channel"] = await shared_pool["rmq_conn"].channel()
    shared_pool["rmq_rpc"] = await aio_pika.patterns.RPC.create(shared_pool["rmq_channel"])
    shared_pool["rmq_rpc"].host_exceptions = True

    yield

    await Tortoise.close_connections()
    await shared_pool["rmq_conn"].close()
    shared_pool.clear()

app = FastAPI(lifespan=lifespan, root_path="/ingest")


PENDING_UPLOAD_EXPIRATION = 600000
@app.get("/requestUpload")
async def request_upload(user: authentication.user_dependency, content_type: str):
    if (content_type.split("/")[0] != "image") or not guess_extension(content_type):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable image content type.")

    result = await shared_pool["rmq_rpc"].proxy.request_upload(expiration=PENDING_UPLOAD_EXPIRATION, user_id=user["user_id"], content_type=content_type)

    return result

@app.post("/ackUpload")
async def ack_upload(user: authentication.user_dependency, post: Post):
    result = await shared_pool["rmq_rpc"].proxy.ack_upload(name=post.name,
                                user_id=user["user_id"],
                                description=post.description,
                                correlation_id=post.correlation_id)
    
    if result["status"] == RPCStatus.BAD_REQUEST:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
    
    if result["status"] == RPCStatus.UNAUTHORIZED:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result["message"])

@app.post("/requestUserUpdate")
async def update_user(user: authentication.user_dependency, update_request: UserUpdateRequest):
    if not update_request.bio and not update_request.avatar_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one parameter must be present.")
    
    user_model = await models.User.filter(id=user["user_id"]).first()
    if update_request.bio:
        user_model.bio = update_request.bio
    if update_request.avatar_url:
        user_model.avatar_url = update_request.avatar_url

    await user_model.save()
