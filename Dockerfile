ARG python_version=3.8
ARG baseimage=python:${python_version}-slim
FROM ${baseimage} as build

ARG poetry_version=1.2.2
ARG pyinstaller_version=5.7.0
# don't check for pip upgrade
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # don't care for pip caching
    PIP_NO_CACHE_DIR=1 \
    # non interactive poetry
    POETRY_NO_INTERACTION=1
# install pyinstaller dependencies
RUN apt-get update && apt-get install -y binutils
# setup poetry and pyinstaller
RUN pip install poetry==${poetry_version} pyinstaller==${pyinstaller_version}

# copy code
WORKDIR /code
COPY . .

# # disable virtualenv in docker
RUN poetry config virtualenvs.create false
# install libgeos required by one dependency
RUN apt-get install -y libgeos-dev
# install project dependencies
RUN poetry install --only main
# # add stub for pyinstaller to find executable package entrypoint
RUN echo "from neogit.__main__ import main\nmain()" >> stub.py
# # build standalone neogit
RUN pyinstaller \
    --onefile \
    --name neogit \
    --add-data neogit/logging.yaml:neogit \
    --add-data neogit/config/default_settings.toml:neogit/config \
    --add-data neogit/config/settings.toml:neogit/config \
    stub.py

FROM ${baseimage} as run
WORKDIR /app
COPY --from=build /code/dist/neogit .

# env var to run Dockerized Python app
ENV LANG C.UTF-8 \
    LC_ALL C.UTF-8 \
    # dump Python stacktrace on fault
    PYTHONFAULTHANDLER=1 \
    # always flush output to container logs
    PYTHONUNBUFFERED=1 \
    # prevents python from creating .pyc files
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["./neogit"]
