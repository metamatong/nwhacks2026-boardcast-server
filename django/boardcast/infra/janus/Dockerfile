FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        autoconf \
        automake \
        libtool \
        build-essential \
        pkg-config \
        openssl \
        libmicrohttpd-dev \
        libjansson-dev \
        libnice-dev \
        libssl-dev \
        libsofia-sip-ua-dev \
        libglib2.0-dev \
        libopus-dev \
        libogg-dev \
        libini-config-dev \
        libcollection-dev \
        libconfig-dev \
        libavutil-dev \
        libavcodec-dev \
        libavformat-dev \
        libsrtp2-dev \
        gengetopt \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN git clone --depth 1 https://github.com/meetecho/janus-gateway.git
WORKDIR /tmp/janus-gateway
RUN sh autogen.sh \
    && ./configure --prefix=/opt/janus --disable-docs --disable-data-channels \
    && make -j"$(nproc)" \
    && make install \
    && make configs

RUN mkdir -p /janus
COPY infra/janus/janus.jcfg /opt/janus/etc/janus/janus.jcfg
COPY infra/janus/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8088 8188 10000-10200/udp

ENTRYPOINT ["/entrypoint.sh"]
