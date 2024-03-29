ifdef DOCKER_TAG
    BUILD_VERSION	:= $(DOCKER_TAG)
else
    BUILD_VERSION=latest
endif
IMAGE_BASE		:= reversinglabs/rl-scanner-cloud
IMAGE_NAME		:= $(IMAGE_BASE):$(BUILD_VERSION)
REPORT_DIR		:= reports

LINE_LENGTH	:=	120

# testing parameters
ARTIFACT_OK		:=	vim
ARTIFACT_ERR	:=	eicarcom2.zip

RL_PORTAL_SERVER:= test
RL_PORTAL_ORG	:= Test
RL_PORTAL_GROUP	:= Default

RL_PACKAGE_URL	:= pkg:rl/test-project/test-package@v0.0.1
RL_PACKAGE_URL2	:= test-project/test-package@v0.0.1

VOLUMES 		:= -v ./input:/input
USER_GROUP		:= $(shell id -u):$(shell id -u )
COMMON_DOCKER	:= -i --rm -u $(USER_GROUP) --env-file=$(HOME)/.envfile_rl-scanner-cloud.docker

# -- replace --force , currently not supported: Error: Something went wrong while validating force and replace parameters
TEST_PARAMS_SCAN:= --rl-portal-server $(RL_PORTAL_SERVER) \
	--rl-portal-org $(RL_PORTAL_ORG) \
	--rl-portal-group $(RL_PORTAL_GROUP) \
	--purl $(RL_PACKAGE_URL2) \
	--replace --timeout 20
# {'error': 'Invalid token.'} if the token expired

# the make rules

all: clean format pycheck build test

build:
	mkdir -p tmp
	docker build -t $(IMAGE_NAME) -f Dockerfile .
	docker image ls $(IMAGE_NAME) | tee ./tmp/image_ls.txt
	docker image inspect $(IMAGE_NAME) --format '{{ .Config.Labels }}'
	docker image inspect $(IMAGE_NAME) --format '{{ .RepoTags }}'

test: testFail test_ok test_err test_ok_with_report test_err_with_report

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

test_ok_with_report:
	rm -rf output input
	mkdir -m 777 -p input output
	cp /bin/$(ARTIFACT_OK) ./input/$(ARTIFACT_OK)
	rm -rf $(REPORT_DIR) && mkdir $(REPORT_DIR)
	docker run $(COMMON_DOCKER) $(VOLUMES) -v ./$(REPORT_DIR):/$(REPORT_DIR) $(IMAGE_NAME) \
		rl-scan \
			$(TEST_PARAMS_SCAN) --file-path=/input/$(ARTIFACT_OK) --report-path /$(REPORT_DIR) --report-format all
	ls -laR input >./tmp/list_in_out_ok.txt
	ls -laR $(REPORT_DIR)

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

test_err_with_report:
	rm -rf output input
	mkdir -m 777 -p input output
	curl -o $(ARTIFACT_ERR) -sS https://secure.eicar.org/$(ARTIFACT_ERR)
	cp $(ARTIFACT_ERR) ./input/$(ARTIFACT_ERR)
	rm -rf $(REPORT_DIR) && mkdir $(REPORT_DIR)
	# as we are now scanning a item that makes the scan fail (non zero exit code) we have to ignore the error in the makefile
	-docker run $(COMMON_DOCKER) $(VOLUMES) -v ./$(REPORT_DIR):/$(REPORT_DIR) $(IMAGE_NAME) \
		rl-scan \
			$(TEST_PARAMS_SCAN) --file-path=/input/$(ARTIFACT_ERR) --report-path /$(REPORT_DIR) --report-format all
	ls -laR input >./tmp/list_in_out_err.txt

clean:
	-docker rmi $(IMAGE_NAME)
	rm -rf input output tmp
	rm -f eicarcom2.zip
	rm -rf .mypy_cache */.mypy_cache

format:
	black --line-length $(LINE_LENGTH) scripts/*

pycheck:
	-pylama --max-line-length $(LINE_LENGTH) -l "eradicate,mccabe,pycodestyle,pyflakes" scripts/
