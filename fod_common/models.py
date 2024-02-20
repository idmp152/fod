from tortoise import fields
from tortoise.contrib.postgres.indexes import HashIndex
from tortoise.models import Model


class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=128, unique=True)
    bio = fields.TextField(default="")
    avatar_url = fields.TextField(default="")
    password_hash = fields.TextField()

    def __str__(self):
        return self.username

class Post(Model):
    id = fields.BigIntField(pk=True)
    name = fields.TextField(default="")
    description = fields.TextField(default="")
    bucket = fields.TextField(default="")
    filename = fields.TextField(default="")
    author = fields.ForeignKeyField("models.User", related_name="posts", null=True)
    pending_upload = fields.BooleanField(default=True)
    pending_delete = fields.BooleanField(default=False)
    created_timestamp = fields.DatetimeField(auto_now_add=True)
    upload_correlation = fields.TextField(default="")
    upload_expiration = fields.IntField(null=True)

    class Meta:
        indexes = [
            HashIndex(fields=("upload_correlation",))
        ]

    def __str__(self):
        return self.name
    
class Comment(Model):
    id = fields.BigIntField(pk=True)
    content = fields.TextField()
    author = fields.ForeignKeyField("models.User", related_name="comments")
    post = fields.ForeignKeyField("models.Post", related_name="comments")

class PostLike(Model):
    id = fields.BigIntField(pk=True)
    author = fields.ForeignKeyField("models.User", related_name="postlikes")
    post = fields.ForeignKeyField("models.Post", related_name="postlikes")

class CommentLike(Model):
    id = fields.BigIntField(pk=True)
    author = fields.ForeignKeyField("models.User", related_name="commentlikes")
    comment = fields.ForeignKeyField("models.Comment", related_name="commentlikes")

