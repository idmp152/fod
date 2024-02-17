import asyncio
from itertools import groupby

import boto3
from tortoise import Tortoise
from tortoise.transactions import in_transaction
from tortoise.expressions import Q

from fod_common import models

CLEANUP_DELAY = 5
async def main() -> None:
    await Tortoise.init(
        db_url="postgres://user:password@postgres_primary:5432/postgres", #TODO: get from env
        modules={"models": ["fod_common.models"]}
    )
    await Tortoise.generate_schemas()

    try:
        client = boto3.client("s3", endpoint_url="http://cloudserver-front:8000") #TODO: get from env
        while True:
            async with in_transaction() as conn:
                records = (await conn.execute_query("SELECT id, bucket FROM post WHERE EXTRACT(EPOCH FROM CURRENT_TIMESTAMP-created_timestamp)*1000 > upload_expiration AND pending_upload = TRUE"))[1]
                records.sort(key=lambda x: x["bucket"])
                for bucket, files in groupby(records, lambda x: x["bucket"]):
                    client.delete_objects(
                        Bucket=bucket,
                        Delete={
                            "Objects": [{"Key": str(x["id"])} for x in files],
                            "Quiet": True
                        }
                    )
                ids = [i["id"] for i in records]
                await models.Post.filter(Q(id__in=ids)).delete()
                
            await asyncio.sleep(CLEANUP_DELAY)
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())