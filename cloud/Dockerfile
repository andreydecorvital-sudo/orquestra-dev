FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r orquestra && useradd -r -g orquestra -m orquestra
WORKDIR /srv/orquestra
# Explicit allowlist: config files and secrets must never enter Docker build.
COPY gateway/__init__.py gateway/engine.py gateway/hermes_bridge.py ./gateway/
COPY orchestration/__init__.py orchestration/autonomy.py orchestration/mission_loop.py orchestration/quality.py ./orchestration/
COPY runner/agent_worker.py runner/worker.py ./runner/
COPY cloud/__init__.py cloud/diagnostic_runner.py cloud/hermes_smoke.py ./cloud/
USER orquestra
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-m", "cloud.diagnostic_runner"]
