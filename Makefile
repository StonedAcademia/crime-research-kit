MOON ?= moon
PROJECT ?= crk

.PHONY: check-os install install-minimum install-dev install-governance install-linux install-windows \
	docker-build docker-up docker-down docker-logs docker-shell docker-pull-model \
	docker-smoke docker-config check test test-unit test-integration test-e2e \
	test-governance test-smoke audit-secrets audit-deps audit-licenses audit-links \
	sbom build-dist init-sample validate-sample export-sample

check-os:
	@echo "moon/proto handle cross-platform task routing for this repository."

install: install-minimum

install-minimum:
	$(MOON) run $(PROJECT):install

install-dev:
	$(MOON) run $(PROJECT):install-dev

install-governance:
	$(MOON) run $(PROJECT):install-governance

install-linux: install-minimum

install-windows: install-minimum

docker-config:
	$(MOON) run $(PROJECT):docker-config

docker-build:
	$(MOON) run $(PROJECT):docker-build

docker-up:
	$(MOON) run $(PROJECT):docker-up

docker-down:
	$(MOON) run $(PROJECT):docker-down

docker-logs:
	$(MOON) run $(PROJECT):docker-logs

docker-shell:
	$(MOON) run $(PROJECT):docker-shell

docker-pull-model:
	$(MOON) run $(PROJECT):docker-pull-model

docker-smoke:
	$(MOON) run $(PROJECT):docker-smoke

check:
	$(MOON) run $(PROJECT):check

test:
	$(MOON) run $(PROJECT):test

test-unit:
	$(MOON) run $(PROJECT):test-unit

test-integration:
	$(MOON) run $(PROJECT):test-integration

test-e2e:
	$(MOON) run $(PROJECT):test-e2e

test-governance:
	$(MOON) run $(PROJECT):test-governance

test-smoke:
	$(MOON) run $(PROJECT):test-smoke

audit-secrets:
	$(MOON) run $(PROJECT):audit-secrets

audit-deps:
	$(MOON) run $(PROJECT):audit-deps

audit-licenses:
	$(MOON) run $(PROJECT):audit-licenses

audit-links:
	$(MOON) run $(PROJECT):audit-links

sbom:
	$(MOON) run $(PROJECT):sbom

build-dist:
	$(MOON) run $(PROJECT):build-dist

init-sample:
	$(MOON) run $(PROJECT):init-sample

validate-sample:
	$(MOON) run $(PROJECT):validate-sample

export-sample:
	$(MOON) run $(PROJECT):export-sample
