# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    JEVSCOUT_DATA_DIR=/data

WORKDIR /app

RUN groupadd --system --gid 10001 jevscout \
    && useradd --system --uid 10001 --gid jevscout --home-dir /home/jevscout jevscout \
    && install -d -o jevscout -g jevscout /data

COPY pyproject.toml README.md ./
COPY --chown=10001:10001 src ./src

RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -s /run/secrets/proxy_ca ]; then \
      PIP_CERT=/run/secrets/proxy_ca python -m pip install --no-cache-dir '.[crawl,postgres]'; \
    else \
      python -m pip install --no-cache-dir '.[crawl,postgres]'; \
    fi

USER 10001:10001
VOLUME ["/data"]
ENTRYPOINT ["jevscout"]
CMD ["--help"]

FROM runtime AS test
COPY --chown=10001:10001 tests ./tests
ENTRYPOINT ["python", "-m", "unittest"]
CMD ["discover", "-s", "tests", "-v"]

FROM runtime AS final
