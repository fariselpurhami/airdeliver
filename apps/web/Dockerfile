# apps/web/Dockerfile 

FROM node:20-alpine AS base
RUN apk add --no-cache libc6-compat
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.24.0 --activate

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./

RUN pnpm config set store-dir /root/.pnpm-store
RUN pnpm install --frozen-lockfile --prefer-offline

FROM base AS development
WORKDIR /app
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME="0.0.0.0"

RUN apk add --no-cache dos2unix

COPY --from=deps /app/node_modules ./node_modules
COPY package.json ./package.json
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN dos2unix /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

COPY . .

EXPOSE 3000
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["pnpm", "dev"]

FROM base AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN pnpm build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

ARG APP_USER=nextjs
ARG APP_GROUP=nodejs
ARG APP_UID=1001
ARG APP_GID=1001

RUN existing_group=$(getent group $APP_GID | cut -d: -f1) && \
    if [ -n "$existing_group" ]; then \
       echo "Cleaning conflict for GID $APP_GID"; \
       delgroup $existing_group; \
    fi && \
    addgroup --system --gid $APP_GID $APP_GROUP && \
    adduser --system --uid $APP_UID --ingroup $APP_GROUP $APP_USER

RUN mkdir .next && chown $APP_USER:$APP_GROUP .next

COPY --from=builder --chown=$APP_USER:$APP_GROUP /app/public ./public
COPY --from=builder --chown=$APP_USER:$APP_GROUP /app/.next/standalone ./
COPY --from=builder --chown=$APP_USER:$APP_GROUP /app/.next/static ./.next/static

USER $APP_USER

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
