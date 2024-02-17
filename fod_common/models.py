from tortoise.models import Model
from tortoise.contrib.postgres.indexes import HashIndex
from tortoise import fields

class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.TextField()
    bio = fields.TextField(default="")
    avatar_url = fields.TextField(default="")

    def __str__(self):
        return self.username

class Post(Model):
    id = fields.BigIntField(pk=True)
    name = fields.TextField(default="")
    description = fields.TextField(default="")
    bucket = fields.TextField(default="")
    author_id = fields.ForeignKeyField("models.User", related_name="posts", null=True)
    pending_upload = fields.BooleanField(default=True)
    created_timestamp = fields.DatetimeField(auto_now_add=True)
    upload_corr_id = fields.TextField(default="")
    upload_expiration = fields.IntField(null=True)

    class Meta:
        indexes = [
            HashIndex(fields=("upload_corr_id",))
        ]

    def __str__(self):
        return self.name
    
class Comment(Model):
    id = fields.BigIntField(pk=True)
    content = fields.TextField()
    author_id = fields.ForeignKeyField("models.User", related_name="comments")
    post_id = fields.ForeignKeyField("models.Post", related_name="comments")

class PostLike(Model):
    id = fields.BigIntField(pk=True)
    author_id = fields.ForeignKeyField("models.User", related_name="postlikes")
    post_id = fields.ForeignKeyField("models.Post", related_name="postlikes")

class CommentLike(Model):
    id = fields.BigIntField(pk=True)
    author_id = fields.ForeignKeyField("models.User", related_name="commentlikes")
    comment_id = fields.ForeignKeyField("models.Comment", related_name="commentlikes")

