ifdef DOCKER_TAG
    BUILD_VERSION	:= $(DOCKER_TAG)
else
    BUILD_VERSION=latest
endif
IMAGE_BASE		:= reversinglabs/rl-scanner-cloud
IMAGE_NAME		:= $(IMAGE_BASE):$(BUILD_VERSION)

LINE_LENGTH	:=	120
DIST		:=	dist

# testing parameters
ARTIFACT_OK		:=	vim
ARTIFACT_ERR	:=	eicarcom2.zip
RL_PORTAL_SERVER:= guidedTour
RL_PORTAL_ORG	:= ReversingLabs
RL_PORTAL_GROUP	:= Demo
RL_PACKAGE_URL	:= pkg:rl/test-project/test-package@v0.0.1
RL_PACKAGE_URL2	:= test-project/test-package@v0.0.1
VOLUMES 		:= -v ./input:/input
USER_GROUP		:= $(shell id -u):$(shell id -u )
COMMON_DOCKER	:= -i --rm -u $(USER_GROUP) --env-file=../.envfile
TEST_PARAMS_SCAN:= --rl-portal-server $(RL_PORTAL_SERVER) \
	--rl-portal-org $(RL_PORTAL_ORG) \
	--rl-portal-group $(RL_PORTAL_GROUP) \
	--purl $(RL_PACKAGE_URL2) \
	--force --replace --timeout 20

# the make rules

all: clean format pycheck build test

build:
	mkdir -p tmp
	docker build -t $(IMAGE_NAME) -f Dockerfile .
	docker image ls $(IMAGE_NAME) | tee ./tmp/image_ls.txt
	docker image inspect $(IMAGE_NAME) --format '{{ .Config.Labels }}'
	docker image inspect $(IMAGE_NAME) --format '{{ .RepoTags }}'

test: testFail test_ok test_err

testFail:
	# we know that specifying no arguments alt all should print "Valid commands are" and fail
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) # will fail but we will ignore that
	# we know that specifying no arguments to rl-scan should print usage() and fail
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) rl-scan # will fail but we will ignore that
	# specify al params except file path, this will fail
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) rl-scan $(TEST_PARAMS_SCAN)

test_ok:
	rm -rf output input
	mkdir -m 777 -p input output
	cp /bin/$(ARTIFACT_OK) ./input/$(ARTIFACT_OK)
	docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) \
		rl-scan \
			$(TEST_PARAMS_SCAN) --file-path=/input/$(ARTIFACT_OK)
	ls -laR input >./tmp/list_in_out_ok.txt

test_err:
	rm -rf output input
	mkdir -m 777 -p input output
	curl -o $(ARTIFACT_ERR) -sS https://secure.eicar.org/$(ARTIFACT_ERR)
	cp $(ARTIFACT_ERR) ./input/$(ARTIFACT_ERR)
	# as we are now scanning a item that makes the scan fail (non zero exit code) we have to ignore the error in the makefile
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) \
		rl-scan \
			$(TEST_PARAMS_SCAN) --file-path=/input/$(ARTIFACT_ERR)
	ls -laR input >./tmp/list_in_out_err.txt

clean:
	rm -rf dist
	-docker rmi $(IMAGE_NAME)
	rm -rf input output tmp
	rm -f eicarcom2.zip
	rm -rf .mypy_cache */.mypy_cache

format:
	black --line-length $(LINE_LENGTH) scripts/*

pycheck:
	# pylama -l "eradicate,mccabe,mypy,pycodestyle,pyflakes,pylint" -i E501,C0114,C0115,C0116,C0301,R1705,R0903,W0603,W1510 scripts/
	pylama -l "eradicate,mccabe,pycodestyle,pyflakes" scripts/

dist: format pycheck
	rm -rf $(DIST) && mkdir -p $(DIST) && mkdir -p $(DIST)/scripts
	#copy release files
	cp -a release/* $(DIST)/
	# copy Python scripts
	for src in scripts/*; do \
		[ -f "$$src" ] && { \
			echo "$$src"; \
			sed "/# BEGIN DEVELOP/,/# END DEVELOP/d" "$$src" > "$(DIST)/$$src"; \
		} \
	done
	$(MAKE) -C $(DIST) format
	$(MAKE) -C $(DIST) pycheck
