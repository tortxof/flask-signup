FROM python:3.4
MAINTAINER Daniel Jones <tortxof@gmail.com>

RUN groupadd -r docker && useradd -r -g docker docker

COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt
COPY . /app/

RUN mkdir /data && chown docker:docker /data

USER docker

VOLUME ["/data"]

EXPOSE 5000

ENTRYPOINT ["python3", "app.py"]
