FROM python:3.8.1-slim

# User ID for the django user we're creating. The builder can set this to the
# host user's ID to avoid file permissions problems.
ARG USER_ID=1000
ARG SSH_KEY_PUB
ARG SSH_KEY

ENV PYTHONUNBUFFERED 1
ENV HOME=/home/django

RUN apt-get -qq update \
    && apt-get -qq -y install libpq-dev gcc vim gettext curl ffmpeg openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -qq -y clean

# Create the user and group to run the Django application as
RUN addgroup --system --gid $USER_ID django \
    && adduser --system --home $HOME --uid $USER_ID --ingroup django django

RUN mkdir /root/.ssh
RUN mkdir /home/django/.ssh
RUN echo "${SSH_KEY}" | base64 -d > "/root/.ssh/id_rsa"
RUN echo "${SSH_KEY_PUB}" > "/root/.ssh/id_rsa.pub"
RUN echo "${SSH_KEY}" | base64 -d > "/home/django/.ssh/id_rsa"
RUN echo "${SSH_KEY_PUB}" > "/home/django/.ssh/id_rsa.pub"
RUN chmod 400 /root/.ssh/id_rsa

COPY ./docker/entrypoint_backend.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh \
    && chmod +x /entrypoint.sh

COPY ./docker/local/backend/start.sh /start.sh
RUN sed -i 's/\r//' /start.sh \
    && chmod +x /start.sh


RUN usermod -u 1000 django
RUN usermod -G staff django

COPY ./shared/ /app/shared/
COPY ./backend /app
RUN chown -R django /app
RUN chown -R django /app/shared/

USER django
ENV PATH "${PATH}:${PYTHONUSERBASE:-/home/django/.local}/bin"

RUN pip install --no-cache-dir --user -r /app/requirements/local.txt

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start.sh"]
