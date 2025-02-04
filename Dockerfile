FROM python:3.13
WORKDIR /code
RUN pip install --no-cache-dir --upgrade \
  pydantic \
  fastapi[standard] \
  psycopg[binary] \
  arrow \
  git+https://github.com/PeteyPii/cassiopeia.git \
  git+https://github.com/PeteyPii/cassiopeia-datastores.git#egg=cassiopeia_diskstore\&subdirectory=cassiopeia-diskstore

COPY app /code/app

# Container is expected to mount their settings.json to /code/settings.json

CMD ["fastapi", "run", "--port", "80"]
