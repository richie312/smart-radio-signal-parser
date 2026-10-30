FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gpsd \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 2947
ENTRYPOINT ["gpsd"]
CMD ["-N", "-n", "-G", "/dev/gps"]
