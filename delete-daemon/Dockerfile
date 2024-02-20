FROM python:3.11 as requirements-stage
 
WORKDIR /tmp
 
RUN pip install poetry
 
COPY ./delete-daemon/pyproject.toml ./delete-daemon/poetry.lock* /tmp/
 
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
 
FROM python:3.11
 
WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

COPY ./fod_common /code/fod_common

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/fod_common/requirements.txt

ENV PYTHONPATH /code

COPY ./delete-daemon/delete_daemon /code/delete_daemon

CMD ["python", "delete_daemon/main.py"]