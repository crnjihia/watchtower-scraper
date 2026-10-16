#!/usr/bin/env bash
set -e

# Watchtower Scraper - Container Entrypoint
# Default command is Celery worker; subcommands route to run.py.

if [ "$#" -eq 0 ]; then
    exec python run.py worker
fi

case "$1" in
    worker|beat|crawl|status|alerts|test|demo)
        exec python run.py "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
