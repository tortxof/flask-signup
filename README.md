# flask-signup

This is a minimal flask app to receive sign up form data.

## Deploy with Docker

### Build a docker image.

First, clone the git repo and run `bower install`.

    git clone https://github.com/tortxof/flask-signup.git
    cd flask-signup
    bower install

Then, build the image.

    docker build --pull -t tortxof/flask-signup .

### Start a container.

The container needs a directory to store the database. Create a directory and
change the group ownership to `docker`.

    mkdir /srv/flask-signup
    chgrp docker /srv/flask-signup

Now the container can be started. You will need to provide 2 environment
variables. `SECRET_KEY` is used as the flask secret key. `APP_URL` is the url
where the app is hosted.

    docker run -d --restart always --name flask-signup \
      -e SECRET_KEY=A_UNIQUE_SECRET_KEY \
      -e APP_URL=https://signup.example.com \
      -v /srv/flask-signup:/data \
      -p 5000:5000 \
      tortxof/flask-signup
