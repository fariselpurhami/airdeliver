# ------------------------------------------------------------------------------------
# 🏢 AIRDELIVER ARCHITECTURAL STANDARD: C2-GATEWAY
# 🚀 ULTRA PRODUCTION READY | GLOBAL SCALE | AGGRESSIVE CACHING
# ------------------------------------------------------------------------------------

# 1️⃣ Base Stage: The Immutable Foundation
FROM python:3.11-slim-bookworm AS base

# Optimization Flags for Python & Pip
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    # توحيد إصدار Poetry مع باقي المشروع لضمان التوافق
    POETRY_VERSION=2.0.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/poetry/bin:$VIRTUAL_ENV/bin:$PATH"

# 2️⃣ Builder Stage: The Factory (Heavy Lifting happens here)
FROM base AS builder

WORKDIR /app

# ⚡ Network-Resilient System Install (Google Style)
# بنستخدم Caching Mounts عشان منحملش الـ apt packages كل مرة
RUN --mount=type=cache,target=/var/cache/apt/archives,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 update && \
    apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 install -y --no-install-recommends \
    build-essential \
    curl \
    git

# ⚡ Smart Poetry Install
# بنسطب Poetry + Export Plugin عشان نعرف نطلع requirements.txt نضيف
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=600 "poetry==$POETRY_VERSION" poetry-plugin-export && \
    poetry config installer.max-workers 10

# Create the clean Virtual Environment
RUN python -m venv $VIRTUAL_ENV

# 💎 THE GOLDEN LAYER: Dependency Caching
# بننسخ ملفات التعريف الأول بس. لو الملفات دي ماتغيرتش، الدوكر هيستخدم الكاش ومش هينفذ السطر اللي بعده
COPY pyproject.toml poetry.lock ./

# ⚡ Export & Install Logic
# بنحول Poetry لـ standard requirements وبنسطب بـ pip لاستغلال سرعته وتوافقه الكامل
RUN poetry export --format=requirements.txt --output=requirements.txt --without-hashes && \
    pip install --no-cache-dir -r requirements.txt

# 3️⃣ Production Stage: The Lightweight Runner
FROM base AS production

WORKDIR /app

ARG APP_USER=airdeliver
ARG APP_UID=1001
ARG APP_GID=1001

# 🛡️ Security: Create Non-Root User
RUN groupadd -g $APP_GID $APP_USER || true && \
    useradd -u $APP_UID -g $APP_GID -d /home/$APP_USER -s /bin/bash -m $APP_USER

# ⚡ Runtime Dependencies Only
# بنسطب بس اللي محتاجينه للتشغيل (زي curl للـ Healthcheck)
RUN --mount=type=cache,target=/var/cache/apt/archives,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 update && \
    apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 🚚 Copy Artifacts (The Handover)
# بننقل الـ Venv الجاهز من مرحلة الـ Builder
COPY --from=builder --chown=$APP_USER:$APP_USER $VIRTUAL_ENV $VIRTUAL_ENV

# بننسخ كود المشروع في الآخر عشان لو عدلت كود بس، البناء يبقى طيارة
COPY --chown=$APP_USER:$APP_USER ./app ./app

# Switch to Safe User
USER $APP_USER
EXPOSE 8001

# 💓 Heartbeat Monitor
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8001/ws/health || exit 1

# 🏁 Launch Sequence
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8001", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
