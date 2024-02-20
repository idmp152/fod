FROM python:3.11 as requirements-stage
 
WORKDIR /tmp
 
RUN pip install poetry
 
COPY ./hangref-daemon/pyproject.toml ./hangref-daemon/poetry.lock* /tmp/
 
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
 
FROM python:3.11
 
WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

COPY ./fod_common /code/fod_common

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/fod_common/requirements.txt

ENV PYTHONPATH /code

COPY ./hangref-daemon/hangref_daemon /code/hangref_daemon

CMD ["python", "hangref_daemon/main.py"]