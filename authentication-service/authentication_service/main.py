import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from tortoise import Tortoise

from fod_common import models
from fod_common.authentication import ALGORITHM, SECRET_KEY

bcrypt_context = CryptContext(schemes=["bcrypt"])

class CreateUserRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(
        db_url="postgres://user:password@postgres_primary:5432/postgres", #TODO: get from env
        modules={"models": ["fod_common.models"]}
    )
    await Tortoise.generate_schemas()

    yield

    await Tortoise.close_connections()

app = FastAPI(lifespan=lifespan, root_path="/auth")

@app.post("/createUser")
async def create_user(create_user_request: CreateUserRequest):
    user = models.User()
    user.username = create_user_request.username
    user.password_hash = bcrypt_context.hash(create_user_request.password)
    await user.save()
    

async def authenticate_user(username: str, password: str) -> models.User | None:
    user = await models.User.filter(username=username).first()
    if not user:
        return None
    if not bcrypt_context.verify(password, user.password_hash):
        return None
    return user


TOKEN_EXPIRATION = timedelta(minutes=1)
def create_access_token(username: str, user_id: int, expiration: timedelta):
    encode = {"sub": username, "id": user_id}
    expires = datetime.utcnow() + expiration
    encode["exp"] = expires
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/requestToken", response_model=Token)
async def request_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user.")
    
    token = create_access_token(user.username, user.id, TOKEN_EXPIRATION)
    return Token(access_token=token, token_type="bearer")
