SHELL := /bin/bash

ifdef DOCKER_TAG
    BUILD_VERSION	:= $(DOCKER_TAG)
else
    BUILD_VERSION=latest
endif

# -----------------------------------------------------
# venv stuff to pin a specific python version
# note: pylama breaks on 3.12 if you dont install setuptools
# rockylinux-9 has python 3.9.xx
MIN_PYTHON_VERSION := python3.9
export MIN_PYTHON_VERSION

VENV := ./vtmp/
export VENV

PIP_INSTALL := pip3 -q \
	--require-virtualenv \
	--disable-pip-version-check \
	--no-color install

COMMON_VENV := rm -rf $(VENV); \
	$(MIN_PYTHON_VERSION) -m venv $(VENV); \
	source ./$(VENV)/bin/activate;

# -----------------------------------------------------
IMAGE_BASE	:= reversinglabs/rl-scanner-cloud
IMAGE_NAME	:= $(IMAGE_BASE):$(BUILD_VERSION)

LINE_LENGTH	:= 120
PL_LINTERS	:= "eradicate,mccabe,pycodestyle,pyflakes,pylint"
PL_IGNORE	:= C0114,C0115,C0116,C0301,E203

SCRIPTS		:= scripts/

MYPY_INSTALL := \
	types-requests

# ======================================
# Rules
# ======================================

all: prep build

# ==========================
# Code format and verify
# ==========================
prep: clean black pylama mypy

clean:
	rm -rf reports tmp input output $(VENV)
	-docker rmi $(IMAGE_NAME)
	rm -f $(ARTIFACT_ERR)
	rm -rf .mypy_cache */.mypy_cache
	mkdir -m 777 -p input output
	docker image ls

black:
	$(COMMON_VENV) \
	$(PIP_INSTALL) black; \
	black \
		--line-length $(LINE_LENGTH) \
		$(SCRIPTS)/*

pylama:
	$(COMMON_VENV) \
	$(PIP_INSTALL) setuptools pylama; \
	pylama \
		--max-line-length $(LINE_LENGTH) \
		--linters "${PL_LINTERS}" \
		--ignore "${PL_IGNORE}" \
		$(SCRIPTS)/*

mypy:
	$(COMMON_VENV) \
	$(PIP_INSTALL) mypy $(MYPY_INSTALL); \
	mypy \
		--strict \
		--no-incremental \
		$(SCRIPTS)

# =============================
# build of reversinglabs/rl-scanner-cloud
# =============================
build:
	mkdir -p tmp
	docker build -t $(IMAGE_NAME) -f Dockerfile .
	docker image ls $(IMAGE_NAME) | tee ./tmp/image_ls.txt
	docker image inspect $(IMAGE_NAME) --format '{{ .Config.Labels }}'
	docker image inspect $(IMAGE_NAME) --format '{{ .RepoTags }}'
