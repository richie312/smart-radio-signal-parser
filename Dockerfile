# Pinned upstream readsb release image with RTL-SDR support.
# Update this tag deliberately when upgrading the decoder.
FROM ghcr.io/wiedehopf/readsb:sha-c01e01d

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg rtl-sdr python3 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/radio_control.py ./radio_control.py
COPY backend/stations.json ./stations.json

EXPOSE 30006 8090
ENTRYPOINT ["python3", "/app/radio_control.py"]
