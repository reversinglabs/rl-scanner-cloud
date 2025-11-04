SHELL := /bin/bash

ifdef DOCKER_TAG
    BUILD_VERSION := $(DOCKER_TAG)
else
    BUILD_VERSION := latest
endif

# ======================================

IMAGE_BASE	:= reversinglabs/rl-scanner-cloud
IMAGE_NAME	:= $(IMAGE_BASE):$(BUILD_VERSION)

# ======================================
# Rules
# ======================================
all: clean prep build test

prep:
	make -f Makefile.prep
	mkdir -m 777 -p input output tmp

clean:
	rm -rf $(DIST) reports tmp input output vtmp
	-docker rmi $(IMAGE_NAME)
	docker image ls | grep rl-scanner-cloud || exit 0

# =============================
# build of reversinglabs/rl-scanner-cloud
# this will be used by docker via hooks
# =============================
build:
	mkdir -p tmp
	docker build -t $(IMAGE_NAME) -f Dockerfile .
	docker image ls $(IMAGE_NAME) | tee ./tmp/image_ls.txt
	docker image inspect $(IMAGE_NAME) --format '{{ .Config.Labels }}'
	docker image inspect $(IMAGE_NAME) --format '{{ .RepoTags }}'

test:
	make -f Makefile.tests # the default test
	TEST_PLAYGROUND1=1 	make -f Makefile.tests
	TEST_PLAYGROUND2=1 	make -f Makefile.tests
	TEST_CANADA=1		make -f Makefile.tests
