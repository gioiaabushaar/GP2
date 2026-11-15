FROM python:3.12-alpine
RUN addgroup -g 10001 nexis && adduser -D -u 10001 -G nexis nexis
USER 10001:10001
CMD ["python", "-c", "import time; print('NEXIS isolated demo lab'); time.sleep(3600)"]