FROM debian:bookworm-slim AS builder

ARG PGBOUNCER_VERSION=1.24.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        autoconf \
        automake \
        build-essential \
        ca-certificates \
        libevent-dev \
        libpq-dev \
        libssl-dev \
        libtool \
        pkg-config \
        python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

COPY . /src

RUN ./configure --prefix=/usr/local \
    && make -j"$(nproc)" \
    && make install DESTDIR=/tmp/install

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libevent-2.1-7 \
        libpq5 \
        libssl3 \
        net-tools \
    && rm -rf /var/lib/apt/lists/*

ENV PGBOUNCER_CONFIG_DIR=/etc/pgbouncer \
    PGBOUNCER_RUN_DIR=/var/run/pgbouncer \
    PGBOUNCER_LOG_DIR=/var/log/pgbouncer \
    PGBOUNCER_DATA_DIR=/var/lib/pgbouncer

RUN useradd --system --home "$PGBOUNCER_DATA_DIR" --shell /usr/sbin/nologin pgbouncer \
    && mkdir -p "$PGBOUNCER_CONFIG_DIR" "$PGBOUNCER_RUN_DIR" "$PGBOUNCER_LOG_DIR" "$PGBOUNCER_DATA_DIR" \
    && chown -R pgbouncer:pgbouncer "$PGBOUNCER_CONFIG_DIR" "$PGBOUNCER_RUN_DIR" "$PGBOUNCER_LOG_DIR" "$PGBOUNCER_DATA_DIR"

COPY --from=builder /tmp/install/ /

COPY --chown=pgbouncer:pgbouncer docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER pgbouncer

EXPOSE 6432

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD ["pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]

