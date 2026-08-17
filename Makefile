# TenderAI — Cross-platform Makefile (Mac + Windows via WSL2)
.PHONY: setup dev down migrate seed crawl logs shell test

# ── Setup ─────────────────────────────────────────────────────────
setup:
	cp .env.example .env
	docker compose build

# ── Dev ───────────────────────────────────────────────────────────
dev:
	docker compose up

dev-bg:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart backend worker beat

# ── Database ──────────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

migrate-create:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

migrate-down:
	docker compose exec backend alembic downgrade -1

# ── Tasks ─────────────────────────────────────────────────────────
crawl:
	docker compose exec backend python -c "from workers.crawl_worker import crawl_all_sources; crawl_all_sources.delay()"

embed:
	docker compose exec backend python -c "from workers.embed_worker import embed_pending; embed_pending.delay()"

# ── Shell ─────────────────────────────────────────────────────────
shell:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U tenderai -d tenderai

# ── Logs ──────────────────────────────────────────────────────────
logs:
	docker compose logs -f backend worker

logs-all:
	docker compose logs -f

# ── Test ──────────────────────────────────────────────────────────
test:
	docker compose exec backend pytest tests/ -v

# ── Cleanup ───────────────────────────────────────────────────────
clean:
	docker compose down -v --remove-orphans
	docker system prune -f
