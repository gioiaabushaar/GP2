FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup -S -g 10001 nexis \
    && adduser -S -D -H -u 10001 -G nexis nexis

WORKDIR /app

COPY --chown=10001:10001 proxy.py /app/proxy.py

USER 10001:10001

EXPOSE 8080

CMD ["python", "/app/proxy.py"]