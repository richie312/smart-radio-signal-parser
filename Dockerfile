# Pinned upstream readsb release image with RTL-SDR support.
# Update this tag deliberately when upgrading the decoder.
FROM ghcr.io/wiedehopf/readsb:sha-c01e01d

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg rtl-sdr python3 git cmake build-essential libusb-1.0-0-dev pkg-config && \
    git clone https://github.com/rtlsdrblog/rtl-sdr-blog.git /tmp/rtl-sdr-blog && \
    git -C /tmp/rtl-sdr-blog fetch --depth 1 origin aed0ea1 && \
    git -C /tmp/rtl-sdr-blog checkout --detach FETCH_HEAD && \
    cmake -S /tmp/rtl-sdr-blog -B /tmp/rtl-sdr-blog/build -DINSTALL_UDEV_RULES=OFF && \
    cmake --build /tmp/rtl-sdr-blog/build --parallel "$(nproc)" && \
    cmake --install /tmp/rtl-sdr-blog/build && \
    ldconfig && \
    rm -rf /tmp/rtl-sdr-blog && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/radio_control.py ./radio_control.py
COPY backend/stations.json ./stations.json

EXPOSE 30006 8090
ENTRYPOINT ["python3", "/app/radio_control.py"]
