# Avocado — Django + HTMX + Tailwind/DaisyUI
# ============================================

PYTHON     := python3
VENV       := .venv
BIN        := $(VENV)/bin
PIP        := $(BIN)/pip
MANAGE     := $(BIN)/python manage.py
TAILWIND   := ./static/css/tailwindcss
CSS_IN     := static/css/input.css
CSS_OUT    := static/css/output.css

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

.PHONY: install
install: venv deps tailwind-install css migrate ## Full first-time setup

.PHONY: venv
venv: ## Create virtualenv if missing
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)

.PHONY: deps
deps: venv ## Install Python dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

.PHONY: tailwind-install
tailwind-install: ## Download Tailwind standalone + DaisyUI bundles
	@mkdir -p static/css
	@cd static/css && curl -sL daisyui.com/fast | bash

.PHONY: migrate
migrate: ## Run Django migrations
	$(MANAGE) migrate

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

.PHONY: run
run: css ## Build CSS then start Django dev server
	$(MANAGE) runserver

.PHONY: dev
dev: ## Run Django server + Tailwind watcher in parallel
	@$(TAILWIND) -i $(CSS_IN) -o $(CSS_OUT) --watch=always & \
	TAILWIND_PID=$$!; \
	trap "kill $$TAILWIND_PID 2>/dev/null" EXIT; \
	$(MANAGE) runserver

.PHONY: css
css: ## One-shot Tailwind build
	$(TAILWIND) -i $(CSS_IN) -o $(CSS_OUT)

.PHONY: css-watch
css-watch: ## Tailwind build in watch mode
	$(TAILWIND) -i $(CSS_IN) -o $(CSS_OUT) --watch=always

.PHONY: css-minify
css-minify: ## Tailwind production build (minified)
	$(TAILWIND) -i $(CSS_IN) -o $(CSS_OUT) --minify

# ---------------------------------------------------------------------------
# Django helpers
# ---------------------------------------------------------------------------

.PHONY: shell
shell: ## Django shell
	$(MANAGE) shell

.PHONY: superuser
superuser: ## Create Django superuser
	$(MANAGE) createsuperuser

.PHONY: makemigrations
makemigrations: ## Generate migration files
	$(MANAGE) makemigrations

# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove build artifacts
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@rm -f $(CSS_OUT)

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	    awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help