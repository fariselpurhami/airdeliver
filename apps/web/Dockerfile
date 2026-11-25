# Build from the repository root: one canonical workspace dependency graph.
FROM node:22-bookworm-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@12.6.0 --activate

FROM base AS deps
WORKDIR /workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .pnpmfile.cjs ./
COPY apps/web/package.json apps/web/.npmrc ./apps/web/
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --ignore-scripts --config.minimum-release-age=0
# Resolve the same application dependencies from the existing dev mount path.
FROM base AS development
WORKDIR /app
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
COPY --from=deps /workspace/node_modules /node_modules
COPY --from=deps /workspace/apps/web/node_modules ./node_modules
COPY apps/web/ ./
EXPOSE 3000
CMD ["pnpm", "dev"]

FROM base AS builder
WORKDIR /workspace
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}
COPY --from=deps /workspace/node_modules ./node_modules
COPY --from=deps /workspace/apps/web/node_modules ./apps/web/node_modules
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .pnpmfile.cjs ./
COPY apps/web/ ./apps/web/
WORKDIR /workspace/apps/web
RUN --mount=type=cache,target=/workspace/apps/web/.next/cache \
    AUTH_SECRET=offline-build-only-not-a-user-secret pnpm build

FROM base AS runner
WORKDIR /app/apps/web
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ARG APP_USER=nextjs
ARG APP_GROUP=nodejs
ARG APP_UID=1001
ARG APP_GID=1001
RUN addgroup --system --gid $APP_GID $APP_GROUP && \
    adduser --system --uid $APP_UID --ingroup $APP_GROUP $APP_USER
COPY --from=builder --chown=$APP_UID:$APP_GID /workspace/apps/web/.next/standalone /app
COPY --from=builder --chown=$APP_UID:$APP_GID /workspace/apps/web/public ./public
COPY --from=builder --chown=$APP_UID:$APP_GID /workspace/apps/web/.next/static ./.next/static
USER $APP_USER
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/logo.png || exit 1
CMD ["node", "server.js"]
