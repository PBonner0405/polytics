FROM python:alpine3.6
WORKDIR /app
COPY requirements.txt ./
RUN apk add --update build-base && \
  pip install --no-cache-dir -r requirements.txt && \
  apk del build-base && \
  rm -rf /var/cache/apk/*
COPY . .
CMD gunicorn -w 4 -b 0.0.0.0:8000 web_app:app
