.PHONY: up down logs ps lint test clean status crawl alerts demo worker beat

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

ps:
	docker-compose ps

lint:
	ruff check .

test:
	pytest -v

status:
	python run.py status

crawl:
	python run.py crawl jobs --limit 5

alerts:
	python run.py alerts --dry-run

demo:
	python run.py demo

worker:
	python run.py worker

beat:
	python run.py beat

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
