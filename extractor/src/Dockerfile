FROM python:alpine3.6
WORKDIR /app
COPY requirements.txt ./
RUN apk add --update build-base && \
  pip install --no-cache-dir -r requirements.txt && \
  apk del build-base && \
  rm -rf /var/cache/apk/*

COPY . .
CMD [ "python", "./main.py" ]
