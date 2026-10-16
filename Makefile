.PHONY: up down logs ps lint test clean status crawl alerts demo worker beat docker-build ghcr-up ghcr-down dist tag

up:
	docker-compose up -d

down:
	docker-compose down

ghcr-up:
	docker-compose -f docker-compose.ghcr.yml up -d

ghcr-down:
	docker-compose -f docker-compose.ghcr.yml down

docker-build:
	docker build -t ghcr.io/crnjihia/watchtower-scraper:latest .

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

dist: clean
	python -m build

tag:
	@if [ -z "$(TAG)" ]; then echo "Error: TAG is required. Usage: make tag TAG=v0.1.0"; exit 1; fi
	git tag -a $(TAG) -m "Release $(TAG)"
	@echo "Tag $(TAG) created. Push to GitHub with: git push origin $(TAG)"

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
