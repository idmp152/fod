import asyncio
import os
from itertools import groupby

from minio import Minio, deleteobjects
from tortoise import Tortoise
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from fod_common import models

CLEANUP_DELAY = 5
async def main() -> None:
    await Tortoise.init(
        db_url="postgres://user:password@postgres_primary:5432/postgres", #TODO: get from env
        modules={"models": ["fod_common.models"]}
    )
    await Tortoise.generate_schemas()

    try:
        client = Minio("minio:9000", access_key=os.getenv("AWS_ACCESS_KEY_ID"), secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"), secure=False)
        while True:
            async with in_transaction() as conn:
                records = (await conn.execute_query("SELECT id, bucket, filename FROM post WHERE EXTRACT(EPOCH FROM CURRENT_TIMESTAMP-created_timestamp)*1000 > upload_expiration AND pending_upload = TRUE"))[1]
                records.sort(key=lambda x: x["bucket"])
                for bucket, files in groupby(records, lambda x: x["bucket"]):
                    client.remove_objects(
                        bucket,
                        [deleteobjects.DeleteObject(str(x["filename"])) for x in files],
                    )
                ids = [i["id"] for i in records]
                await models.Post.filter(Q(id__in=ids)).delete()
                
            await asyncio.sleep(CLEANUP_DELAY)
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())