import os
from contextlib import asynccontextmanager
from datetime import timedelta

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from pydantic import BaseModel
from tortoise import Tortoise
from tortoise.queryset import QuerySet
from urllib import parse

from fod_common import models


class Post(BaseModel):
    id: int
    name: str
    description: str
    image_url: str
    author_id: int
    created_timestamp: int

class User(BaseModel):
    id: int
    name: str
    bio: str
    avatar_url: str

class Comment(BaseModel):
    id: int
    content: str
    author_id: int
    post_id: int

shared_pool: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(
        db_url="postgres://user:password@postgres_replica:5432/postgres", #TODO: get from env
        modules={"models": ["fod_common.models"]}
    )

    shared_pool["redis"] = redis.Redis(host="redis", port=6379, decode_responses=True)
    await shared_pool["redis"].config_set("maxmemory-policy", "allkeys-lru")

    yield

    await shared_pool["redis"].aclose()
    await Tortoise.close_connections()

app = FastAPI(lifespan=lifespan, root_path="/serving")
s3_client = Minio("minio:9000", access_key=os.getenv("AWS_ACCESS_KEY_ID"), secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"), secure=False)


CACHE_EXPIRATION = timedelta(hours=2)
def map_db_post_to_response(post: models.Post) -> Post:
    url = s3_client.presigned_get_object(post.bucket, post.filename, expires=CACHE_EXPIRATION)
    parsed_url = parse.urlparse(url)
    url = parsed_url._replace(netloc=parsed_url.netloc.replace(parsed_url.hostname, os.getenv("PRESIGNED_URL_HOSTNAME")).replace(str(parsed_url.port), os.getenv("PRESIGNED_URL_PORT"))).geturl()
    return Post(id=post.id, name=post.name, description=post.description, image_url=url, created_timestamp=int(post.created_timestamp.timestamp()), author_id=post.author_id)


@app.get("/requestPost", response_model=Post)
async def request_post(post_id: int) -> Post:
    post = await models.Post.filter(id=post_id, pending_upload=False, pending_delete=False).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    
    cache: redis.Redis = shared_pool["redis"]

    result = await cache.hgetall(f"posts:{post_id}")

    if not result:
        result = map_db_post_to_response(post).model_dump()
        await cache.hset(f"posts:{post_id}", mapping=result)
        await cache.expire(f"posts:{post_id}", CACHE_EXPIRATION)

    return result

MAX_LIMIT = 100
@app.get("/requestFeed")
async def request_feed(limit: int = 20, page: int = 1) -> list[Post]:
    if limit > MAX_LIMIT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Feed limit must not be bigger than {MAX_LIMIT}.")
    
    result = []
    posts = await QuerySet(models.Post).order_by("-created_timestamp").limit(limit).offset(limit * (page - 1))
    for post in posts:
        result.append(map_db_post_to_response(post))

    return result

@app.get("/searchPosts")
async def search_posts(name: str = "", description: str = "", author_id: int = 0, limit: int = 20, page: int = 1) -> list[Post]:
    if not any((name, description, author_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one search parameter must be present.")
    
    kwargs = dict()
    if name:
        kwargs["name__icontains"] = name
    if description:
        kwargs["description__icontains"] = description
    if author_id:
        kwargs["author_id"] = author_id

    posts = await models.Post.filter(**kwargs).order_by("-created_timestamp").limit(limit).offset(limit * (page - 1))
    result = []
    for post in posts:
        result.append(map_db_post_to_response(post))

    return result


@app.get("/requestUser", response_model=User)
async def request_user(user_id: int) -> User:
    user = await models.User.filter(id=user_id, pending_upload=False, pending_delete=False).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    cache: redis.Redis = shared_pool["redis"]

    result = await cache.hgetall(f"users:{user_id}")

    if not result:
        result = User(id=user_id, name=user.username, bio=user.bio, avatar_url=user.avatar_url).model_dump()
        await cache.hset(f"users:{user_id}", mapping=result)
        await cache.expire(f"users:{user_id}", CACHE_EXPIRATION)

    return result

@app.get("/requestComment", response_model=Comment)
async def request_comment(comment_id: int) -> Comment:
    comment = await models.Comment.filter(id=comment_id, pending_upload=False, pending_delete=False).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    
    cache: redis.Redis = shared_pool["redis"]

    result = await cache.hgetall(f"comments:{comment_id}")

    if not result:
        result = Comment(id=comment_id, content=comment.content, author_id=comment.author_id, post_id=comment.post_id).model_dump()
        await cache.hset(f"comments:{comment_id}", mapping=result)
        await cache.expire(f"comments:{comment_id}", CACHE_EXPIRATION)

    return result


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin",
                   "Authorization"],
)