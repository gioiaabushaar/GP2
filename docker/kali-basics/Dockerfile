FROM kalilinux/kali-rolling:latest

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    nmap curl iproute2 iputils-ping ca-certificates libcap2-bin \
 && setcap -r /usr/lib/nmap/nmap \
 && groupadd -g 10001 nexis \
 && useradd -m -u 10001 -g 10001 -s /bin/bash nexis \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /home/nexis
USER 10001:10001
CMD ["sleep", "3600"]