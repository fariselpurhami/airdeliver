.PHONY: up down restart logs

# تجهيز البيئة وتشغيل المشروع
up:
	@echo "Checking network airdeliver-global-net..."
	@docker network inspect airdeliver-global-net >/dev/null 2>&1 || docker network create airdeliver-global-net
	@echo "Starting containers..."
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev up -d

# إيقاف المشروع
down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev down

# عرض اللوجز
logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev logs -f
