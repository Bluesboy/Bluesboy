# =============================================================================
# CONFIGURATION
# =============================================================================
SHELL        := /usr/bin/env bash
.SHELLFLAGS  := -eu -o pipefail -c
.DELETE_ON_ERROR:

PROJECT_NAME ?= Bluesboy
BUILD_DIR    ?= build
SITE_DIR     ?= $(BUILD_DIR)/site
PDF_DIR      ?= $(BUILD_DIR)/pdf
VERSION      ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)

HUGO         ?= hugo
TYPST        ?= typst
TYPST_FLAGS  ?= --font-path assets/fonts --package-path vendor/typst --ignore-system-fonts
COG          ?= cog
GH           ?= gh
PYTHON       ?= python3
PORT         ?= 1313
PIP_PACKAGES ?= jsonschema[format-nongpl] PyYAML yamllint
ACTIONLINT_VERSION ?= v1.7.7
TYPSTYLE_VERSION   ?= 0.15.1

PDF_EN := $(PDF_DIR)/shamil-sattarov-resume-en.pdf
PDF_RU := $(PDF_DIR)/shamil-sattarov-resume-ru.pdf

# =============================================================================
# HELP
# =============================================================================
.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS=":|##"} \
	/^#--/ {gsub(/^#--[ \t]*/, "", $$0); printf "\033[33m%s\033[0m\n", $$0; next} \
	/^[A-Za-z0-9_.\/\-]+:.*##/ { \
		target = $$1; gsub(/[ \t]+$$/, "", target); \
		deps = $$2; gsub(/^[ \t]+|[ \t]+$$/, "", deps); \
		desc = $$3; gsub(/^[ \t]+|[ \t]+$$/, "", desc); \
		if (deps == "") deps = "(no deps)"; \
		printf "\033[32m %-30s\033[0m %-25s %s\n", target, deps, desc; \
	}' $(MAKEFILE_LIST)

# =============================================================================
# BUILD
# =============================================================================
.PHONY: build build/site build/pdf build/pdf/en build/pdf/ru build/release

#-- Build
build: build/site build/pdf ## Build CV website and both resumes

build/pdf/en: ## Build English PDF
	@mkdir -p $(PDF_DIR)
	$(TYPST) compile $(TYPST_FLAGS) --input lang=en --input version=$(VERSION) resume.typ $(PDF_EN)

build/pdf/ru: ## Build Russian PDF
	@mkdir -p $(PDF_DIR)
	$(TYPST) compile $(TYPST_FLAGS) --input lang=ru --input version=$(VERSION) resume.typ $(PDF_RU)

build/pdf: build/pdf/en build/pdf/ru ## Build both resumes
	@cd $(PDF_DIR) && sha256sum $$(basename $(PDF_EN)) $$(basename $(PDF_RU)) > SHA256SUMS

build/site: ## Build production Hugo website
	@rm -rf $(SITE_DIR)
	$(HUGO) --destination $(abspath $(SITE_DIR))
# English lives at /, but Hugo still writes a meta-refresh page at /en/, and
# disableAliases does not cover it: that page comes from the multilingual
# layout, not from front-matter aliases. sitemap.xml still indexes
# /en/sitemap.xml, so only the redirect goes.
	@rm -f $(SITE_DIR)/en/index.html

build/release: build ## Build release artifacts
	@echo "Release artifacts: $(PDF_DIR), $(SITE_DIR)"

# =============================================================================
# DEVELOPMENT
# =============================================================================
.PHONY: preview watch/pdf/en watch/pdf/ru open/pdf/en open/pdf/ru

#-- Development
preview: ## Run Hugo preview server
	$(HUGO) server --buildDrafts --port $(PORT)

watch/pdf/en: ## Rebuild English PDF on changes
	$(TYPST) watch $(TYPST_FLAGS) --input lang=en --input version=$(VERSION) resume.typ $(PDF_EN)

watch/pdf/ru: ## Rebuild Russian PDF on changes
	$(TYPST) watch $(TYPST_FLAGS) --input lang=ru --input version=$(VERSION) resume.typ $(PDF_RU)

open/pdf/en: build/pdf/en ## Open English PDF
	xdg-open $(PDF_EN)

open/pdf/ru: build/pdf/ru ## Open Russian PDF
	xdg-open $(PDF_RU)

# =============================================================================
# TESTS
# =============================================================================
.PHONY: test test/schema test/build test/ci

#-- Tests
test/schema: ## Validate CV YAML against JSON Schema
	$(PYTHON) scripts/validate_cv.py

test/build: build ## Verify generated artifacts
	test -s $(PDF_EN)
	test -s $(PDF_RU)
	test -s $(PDF_DIR)/SHA256SUMS
	test -s $(SITE_DIR)/index.html
	test -s $(SITE_DIR)/ru/index.html

test/ci: test/schema test/build ## Run CI test suite

test: test/ci ## Run all tests

# =============================================================================
# LINT / FORMAT / CHECK
# =============================================================================
.PHONY: lint fmt check

#-- Lint/Format
lint: ## Run available linters
	@if command -v yamllint >/dev/null; then yamllint data .github; else echo "yamllint not installed; skipped"; fi
	@if command -v actionlint >/dev/null; then actionlint; else echo "actionlint not installed; skipped"; fi
	@if command -v typstyle >/dev/null; then typstyle --check resume.typ; else echo "typstyle not installed; skipped"; fi

fmt: ## Format Typst source when typstyle is installed
	@if command -v typstyle >/dev/null; then typstyle --inplace resume.typ; else echo "typstyle not installed; skipped"; fi

check: lint test/schema ## Run static checks

# =============================================================================
# DEPENDENCIES
# =============================================================================
.PHONY: deps deps/install deps/verify deps/versions

#-- Dependencies
deps/install: ## Install Python validation and lint dependencies
	@$(PYTHON) -m pip install --user $(PIP_PACKAGES) \
		|| $(PYTHON) -m pip install --user --break-system-packages $(PIP_PACKAGES)
	@command -v actionlint >/dev/null || go install github.com/rhysd/actionlint/cmd/actionlint@$(ACTIONLINT_VERSION)
	@command -v typstyle >/dev/null || cargo install typstyle --version $(TYPSTYLE_VERSION) --locked

deps/verify: ## Verify required build and lint dependencies
	@for tool in $(HUGO) $(TYPST) $(COG) $(GH) $(PYTHON) sha256sum yamllint actionlint typstyle; do command -v $$tool >/dev/null || { echo "Missing dependency: $$tool" >&2; exit 1; }; done
	@$(PYTHON) -c 'import jsonschema, yaml'

deps/versions: ## Print pinned tool versions (CI builds its cache key from this)
	@echo "actionlint-$(ACTIONLINT_VERSION)-typstyle-$(TYPSTYLE_VERSION)"

deps: deps/install deps/verify ## Install and verify dependencies

# =============================================================================
# ASSETS
# =============================================================================
.PHONY: fonts/build

#-- Assets
fonts/build: ## Regenerate bundled IBM Plex Sans faces (needs fonttools, brotli)
	$(PYTHON) -m pip install --quiet --disable-pip-version-check fonttools brotli
	$(PYTHON) scripts/build_fonts.py

# =============================================================================
# VERSIONING / RELEASE
# =============================================================================
.PHONY: version version/next version/plan version/patch version/minor version/major version/release release

#-- Versioning
version: ## Show current version
	@echo $(VERSION)

version/next: ## Preview automatic semantic version bump
	$(COG) bump --auto --dry-run

version/patch: ## Preview patch version bump
	$(COG) bump --patch --dry-run

version/minor: ## Preview minor version bump
	$(COG) bump --minor --dry-run

version/major: ## Preview major version bump
	$(COG) bump --major --dry-run

version/plan: ## Print the tag the next release would carry, or nothing
	@if git describe --tags --abbrev=0 >/dev/null 2>&1; then \
		$(COG) bump --auto --dry-run 2>/dev/null | grep -E '^v[0-9]' || true; \
	else \
		echo v1.0.0; \
	fi

version/release: ## Create and push the next tag when commits warrant one
	@if git describe --tags --abbrev=0 >/dev/null 2>&1; then \
		before=$$(git describe --tags --abbrev=0); \
		$(COG) bump --auto >&2 || true; \
		if [ "$$before" = "$$(git describe --tags --abbrev=0)" ]; then \
			echo "no bump-worthy commits since $$before; skipping release" >&2; \
			printf 'tag=\n'; \
			exit 0; \
		fi; \
	else \
		git tag v1.0.0; \
	fi; \
	tag=$$(git describe --tags --abbrev=0); \
	git push origin "$$tag" >&2; \
	printf 'tag=%s\n' "$$tag"

release: ## Publish built PDFs and checksums to GitHub Release
	@test "$(VERSION)" != "dev" || { echo "VERSION must be a release tag" >&2; exit 1; }
	@test -s $(PDF_DIR)/SHA256SUMS
	@if $(GH) release view "$(VERSION)" >/dev/null 2>&1; then \
		$(GH) release upload "$(VERSION)" $(PDF_EN) $(PDF_RU) $(PDF_DIR)/SHA256SUMS --clobber; \
	else \
		$(GH) release create "$(VERSION)" $(PDF_EN) $(PDF_RU) $(PDF_DIR)/SHA256SUMS --title "$(VERSION)" --generate-notes; \
	fi

# =============================================================================
# CLEANUP
# =============================================================================
.PHONY: clean

#-- Cleanup
clean: ## Remove generated artifacts
	rm -rf $(BUILD_DIR) public static/downloads resources/_gen

# =============================================================================
# CI/CD
# =============================================================================
.PHONY: ci

#-- CI/CD
ci: deps/verify lint test/ci ## Run full local CI pipeline
	@echo "CI pipeline complete"

# =============================================================================
# DEFAULT
# =============================================================================
.DEFAULT_GOAL := help
