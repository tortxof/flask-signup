FROM python:3.4
MAINTAINER Daniel Jones <tortxof@gmail.com>

RUN groupadd -r docker && useradd -r -g docker docker

RUN wget https://github.com/Yelp/dumb-init/releases/download/v1.0.2/dumb-init_1.0.2_amd64.deb && \
    dpkg -i dumb-init_1.0.2_amd64.deb && \
    rm dumb-init_1.0.2_amd64.deb

COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt
COPY . /app/

RUN mkdir /data && chown docker:docker /data

USER docker

VOLUME ["/data"]

EXPOSE 5000

ENTRYPOINT ["dumb-init"]
CMD ["python3", "app.py"]
