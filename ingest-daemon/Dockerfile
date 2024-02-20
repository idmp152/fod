FROM python:3.11 as requirements-stage
 
WORKDIR /tmp
 
RUN pip install poetry
 
COPY ./ingest-daemon/pyproject.toml ./ingest-daemon/poetry.lock* /tmp/
 
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
 
FROM python:3.11
 
WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

COPY ./fod_common /code/fod_common

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/fod_common/requirements.txt

ENV PYTHONPATH /code

COPY ./ingest-daemon/ingest_daemon /code/ingest_daemon

CMD ["python", "ingest_daemon/main.py"]