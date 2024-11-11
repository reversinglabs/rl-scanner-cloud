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

REPORT_DIR	:= reports

LINE_LENGTH	:= 120
PL_LINTERS	:= "eradicate,mccabe,pycodestyle,pyflakes,pylint"
PL_IGNORE	:= C0114,C0115,C0116,C0301,E203

SCRIPTS		:= scripts/

# testing parameters
ARTIFACT_OK		:= bash
ARTIFACT_ERR	:= eicarcom2.zip

USE_PLAYGROUND = $$( grep -i '^RLPORTAL_SERVER=' $(HOME)/.envfile_rl-scanner-cloud.docker | grep -i  -q 'playground' && echo '1' )

ifeq ( USE_PLAYGROUND, 1)
	RL_PORTAL_SERVER	=	playground
	RL_PORTAL_ORG		=	ReversingLabs
	RL_PORTAL_GROUP		=	hello
else
	RL_PORTAL_SERVER	=	test
	RL_PORTAL_ORG		=	Test
	RL_PORTAL_GROUP		=	Default
endif

RL_PACKAGE_URL	:= pkg:rl/test-project/test-package@v0.0.1
RL_PACKAGE_URL2	:= test-project/test-package@v0.0.1

VOLUMES 		:= -v ./input:/input
USER_GROUP		:= $(shell id -u):$(shell id -u )

COMMON_DOCKER	:= -i --rm -u $(USER_GROUP) --env-file=$(HOME)/.envfile_rl-scanner-cloud.docker

TEST_PARAMS_SCAN:= \
	--rl-portal-server $(RL_PORTAL_SERVER) \
	--rl-portal-org $(RL_PORTAL_ORG) \
	--rl-portal-group $(RL_PORTAL_GROUP) \
	--purl $(RL_PACKAGE_URL2) \
	--timeout 20 --replace --force

MYPY_INSTALL := \
	types-requests

# ======================================
# Rules
# ======================================

all: prep build test $(DIST)

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
		$(SCRIPTS)

pylama:
	$(COMMON_VENV) \
	$(PIP_INSTALL) setuptools pylama; \
	pylama \
		--max-line-length $(LINE_LENGTH) \
		--linters "${PL_LINTERS}" \
		--ignore "${PL_IGNORE}" \
		$(SCRIPTS)

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

# ==========================
# Testing
# ==========================

test: testFail test_err test_err_with_report test_ok test_ok_with_report

./input/$(ARTIFACT_ERR):
	mkdir -m 777 -p input output
	curl -o ./input/$(ARTIFACT_ERR) -sS https://secure.eicar.org/$(ARTIFACT_ERR)

./input/$(ARTIFACT_OK):
	mkdir -m 777 -p input output
	cp /bin/$(ARTIFACT_OK) ./input/

testFail:
	# we know that specifying no arguments alt all should print "Valid commands are" and fail
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) # will fail but we will ignore that
	# we know that specifying no arguments to rl-scan should print usage() and fail
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) \
		rl-scan # will fail but we will ignore that
	# specify al params except file path, this will fail
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) \
		rl-scan $(TEST_PARAMS_SCAN)

test_ok: ./input/$(ARTIFACT_OK)
	echo $@
	docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) \
		rl-scan \
			$(TEST_PARAMS_SCAN) \
			--file-path=/input/$(ARTIFACT_OK) 2>&1 | tee tmp/$@.out
	ls -laR input >./tmp/list_in_out_ok.txt

test_ok_with_report: ./input/$(ARTIFACT_OK)
	echo $@
	rm -rf $(REPORT_DIR) && mkdir $(REPORT_DIR)
	docker run $(COMMON_DOCKER) $(VOLUMES) -v ./$(REPORT_DIR):/$(REPORT_DIR) $(IMAGE_NAME) \
		rl-scan \
			$(TEST_PARAMS_SCAN) \
			--file-path=/input/$(ARTIFACT_OK) \
			--report-path /$(REPORT_DIR) \
			--report-format all  2>&1 | tee tmp/$@.out
	ls -laR input >./tmp/list_in_out_ok.txt
	ls -laR $(REPORT_DIR)

test_err: ./input/$(ARTIFACT_ERR)
	echo $@
	# as we are now scanning a item that makes the scan fail (non zero exit code) we have to ignore the error in the makefile
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) \
		rl-scan \
			$(TEST_PARAMS_SCAN) \
			--file-path=/input/$(ARTIFACT_ERR)  2>&1 | tee tmp/$@.out
	ls -laR input >./tmp/list_in_out_err.txt

test_err_with_report: ./input/$(ARTIFACT_ERR)
	echo $@
	rm -rf $(REPORT_DIR) && mkdir $(REPORT_DIR)
	# as we are now scanning a item that makes the scan fail (non zero exit code) we have to ignore the error in the makefile
	-docker run $(COMMON_DOCKER) $(VOLUMES) -v ./$(REPORT_DIR):/$(REPORT_DIR) $(IMAGE_NAME) \
		rl-scan \
			$(TEST_PARAMS_SCAN) \
			--file-path=/input/$(ARTIFACT_ERR) \
			--report-path /$(REPORT_DIR) \
			--report-format all  2>&1 | tee tmp/$@.out
	ls -laR input >./tmp/list_in_out_err.txt
