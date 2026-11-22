# Manual local-development shortcuts. Never invoked automatically by Compose.
COMPOSE = docker compose -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev

.PHONY: help up down restart logs

help:
	@printf '%s\n' 'make up      Start combined local-development stack' 'make down    Stop stack, retaining data volumes' 'make restart Restart existing containers' 'make logs    Follow stack logs'

up:
	@docker network inspect airdeliver-global-net || docker network create airdeliver-global-net
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f
