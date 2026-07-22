FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y rtl-sdr && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 1234

ENTRYPOINT ["rtl_tcp"]