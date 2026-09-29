# Marina's Wisdom — backend image (Render).
#
# Two stages: build the venv with the compiler toolchain available, then ship a
# runtime image that has no toolchain at all.
#
# Everything the backend shells out to is baked in here: fabric (+ its patterns),
# ffmpeg/ffprobe, and yt-dlp with curl_cffi for --impersonate. The app resolves
# all three from PATH, so their absence would only surface at analysis time.

# --- Stage 1: build the virtualenv ------------------------------------------
FROM python:3.14-slim-trixie AS builder

# Only needed if a dependency has no wheel for this Python. Pinned against
# backend/.venv (3.14.7) where asyncpg 0.31, bcrypt 5.0 and curl_cffi 0.16 all
# install from wheels, so this is normally unused.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /tmp/requirements.txt

# --- Stage 2: runtime -------------------------------------------------------
FROM python:3.14-slim-trixie

# ffmpeg covers everything the pipelines need: libmp3lame for the 32 kbps mono
# mp3 encodes, the HLS demuxer for m3u8 streams, and https/TLS for remote inputs.
# curl+xz are for the fabric download below.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg \
      ca-certificates \
      curl \
      xz-utils \
 && rm -rf /var/lib/apt/lists/*

# fabric, pinned by version AND checksum. An unpinned build would silently
# change prompt/model handling between deploys.
ARG FABRIC_VERSION=1.4.473
ARG TARGETARCH=amd64
RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) tarball="fabric_Linux_x86_64.tar.gz";  sha="c74b451557cdd5d00dc4b14c7adcc1e4c87455f543d84ce1e69c76922fb27076" ;; \
      arm64) tarball="fabric_Linux_arm64.tar.gz";   sha="896d4dff71b3d3a49ff2132e9fc5184d5c4b84971e9f678101c81e6d880fc06b" ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/fabric.tgz \
      "https://github.com/danielmiessler/fabric/releases/download/v${FABRIC_VERSION}/${tarball}"; \
    echo "${sha}  /tmp/fabric.tgz" | sha256sum -c -; \
    tar -xzf /tmp/fabric.tgz -C /usr/local/bin fabric; \
    chmod +x /usr/local/bin/fabric; \
    rm /tmp/fabric.tgz; \
    fabric --version

COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# fabric resolves patterns from $HOME/.config/fabric/patterns/<name>/system.md.
# It ignores XDG_CONFIG_HOME entirely (verified against the 1.4.473 binary), so
# HOME is the only thing that matters here — get it wrong and every analysis
# fails with a pattern-not-found that looks like a fabric bug.
RUN useradd -u 10001 -m -d /home/app app
ENV HOME=/home/app
# The patterns are vendored in the repo rather than fetched at build time: they
# are the app's behavioural contract, and CURATED_PATTERNS is derived from this
# same directory. Fetching from a mutable upstream branch could ship a UI that
# advertises a pattern which is not on disk.
COPY --chown=app:app backend/fabric_patterns/ /home/app/.config/fabric/patterns/

# fabric REQUIRES $HOME/.config/fabric/.env to exist — it tolerates the file being
# empty but not absent. With it missing, `fabric -p <pattern>` prints two
# "error loading .env file" lines and exits 0 with NO output, so every analysis
# would fail with an empty result rather than an error. Deliberately empty: the
# API key arrives as a real environment variable, which fabric prefers over this
# file, so no secret is ever baked into the image.
RUN touch /home/app/.config/fabric/.env && chown app:app /home/app/.config/fabric/.env

# tiktoken otherwise downloads its BPE file on first use into /tmp, which is
# per-container — so it would re-download on every deploy, and silently fall back
# to a len(text)//4 estimate if egress were ever blocked.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken
RUN mkdir -p ${TIKTOKEN_CACHE_DIR} \
 && python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" \
 && chmod -R a+rX ${TIKTOKEN_CACHE_DIR}

WORKDIR /app
COPY backend/ /app/backend/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MARINA_TMP_DIR=/tmp/marina \
    APP_ENV=production

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT:-8000}/health" || exit 1

# --workers 1 is deliberate, not an oversight. The job registry
# (_jobs: dict[job_id, asyncio.Task]) and the boot sweeper are per-process state;
# a job started on one worker is invisible to another. main.py refuses to boot
# with more than one worker while the sweeper is enabled.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
