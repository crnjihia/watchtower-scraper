.PHONY: up down logs ps lint test clean

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

ps:
	docker-compose ps

lint:
	poetry run black .
	poetry run isort .
	poetry run ruff check .

test:
	poetry run pytest -vv --cov=angalia

clean:
	rm -rf .venv .pytest_cache .mypy_cache build dist *.egg-info
