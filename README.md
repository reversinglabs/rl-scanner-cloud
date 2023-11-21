# reversinglabs/rl-scanner-cloud

![Header image](https://github.com/reversinglabs/rl-scanner-cloud/raw/main/armando-docker-cloud.png)

`reversinglabs/rl-scanner-cloud` is the official Docker image created by ReversingLabs
for users who want to automate their workflows on the secure.software Portal and integrate it with CI/CD tools.

The image provides access to the main Portal Projects workflows - uploading package versions to a project,
scanning them, and generating analysis reports.
You can also compare different package versions in a project, analyze reproducible build artifacts for a package version, and save analysis reports to local storage.
All successfully analyzed files are visible in the Portal interface, and accessible by you and any other Portal users who can access your projects.

This Docker image is based on Rocky Linux 9.


## What is the secure.software Portal?

The secure.software Portal is a SaaS solution that's part of the secure.software platform - a new ReversingLabs solution for software supply chain security.
More specifically, the Portal is a web-based application for improving and managing the security of your software releases and verifying third-party software used in your organization.

With the secure.software Portal, you can:

- Scan your software packages to detect potential risks before release.
- Improve your SDLC by applying actionable advice from security scan reports to all phases of software development.
- Organize your software projects and automatically compare package versions to detect potentially dangerous behavior changes in the code.
- Manage software quality policies on the fly to ensure compliance and achieve maturity in your software releases.


## Difference between rl-scanner and rl-scanner-cloud

If you're already familiar with the ReversingLabs secure.software platform, you've likely come across another official Docker image: [rl-scanner](https://hub.docker.com/r/reversinglabs/rl-scanner).
You may be wondering how that Docker image is different from `rl-scanner-cloud`.

In short:

- `rl-scanner` is primarily intended for secure.software CLI users, as it closely aligns with the CLI workflows and makes it easier to deploy the CLI in various environments.
- `rl-scanner-cloud` is mainly for secure.software Portal users who want to build their own integrations on top of the Portal features.

The following table lists more detailed differences between these two Docker images that should help you choose the most appropriate image for your use-case.

|             | **rl-scanner** | **rl-scanner-cloud** |
|:----        |:----           | :----                |
| Scanning | Software packages are scanned inside the Docker container, on the local system where the container is running. | Software packages are scanned in the cloud, on the Portal instance to which they are uploaded. |
| Reports  | Users can choose the report format(s) they want to generate, and automatically save the reports to local storage. | Users can choose the report format(s) they want to generate and save them to local storage. The HTML report (rl-html format) is always generated and displayed in the Portal web interface. |
| Accounts and licensing | A valid `rl-secure` license with site key is required to use the Docker image. The size of analyzed files is deducted from the quota allocated to the user's `rl-secure` account. | An active secure.software Portal account with a Personal Access Token is required to use the Docker image. The size of analyzed files is deducted from the analysis capacity that is allocated to the user's group and reserved for projects. |


# Quick reference

**Maintained by:**

- [ReversingLabs](https://www.reversinglabs.com/) as part of the [secure.software platform](https://www.secure.software/)

**Where to get help:**

- [Official documentation](https://docs.secure.software/portal/)
- [ReversingLabs Support](mailto:support@reversinglabs.com)

**Where to file issues:**

- [GitHub repository](https://github.com/reversinglabs/rl-scanner-cloud/issues)


## Versioning and tags

Unversioned Docker image will have the tag `reversinglabs/rl-scanner-cloud:latest`. This tag will always point to the latest published image.

Versioned tags will be structured as `reversinglabs/rl-scanner-cloud:X`, where X is an incrementing version number. We will increment the major version number to signify a breaking change. If changes to the image are such that no existing functionality will be broken (small bug fixes or new helper tools), we will not increment the version number.

This makes it easier for cautious customers to use versioned tag images and migrate to a new version at their own convenience.


# How to use this image

The most common workflow for this Docker image is to upload a file for analysis to a secure.software Portal instance, where it is added as a package version to a new or an existing project and package.
Portal users can then view the analysis report and [manage the analyzed file](https://docs.secure.software/portal/projects#work-with-package-versions-releases) like any other package version.

Access to input data (files you want to scan) and the reports destination directory (to optionally save analysis reports) is provided by using [Docker volume mounts](https://docs.docker.com/storage/volumes/).
To prevent issues with file ownership and access, the `-u` option is used to provide current user identification to the container.

The image wraps the functionality of several Portal Public API endpoints into a single command with [configurable parameters](#configuration-parameters).
As a result, users don't have to send multiple API requests, because the whole workflow can be completed in a single run.

To use the provided Portal functionality, an active account on a Portal instance is required, together with a Personal Access Token for API authentication.
Before you start using the image, make sure all [prerequisites](#prerequisites) are satisfied.

In some cases, a proxy server may be required to access the internet and connect to ReversingLabs servers.
This optional proxy configuration can be provided to the Docker container through [environment variables](#environment-variables).


## Prerequisites

To successfully use this Docker image, you need:

1. **A working Docker installation** on the system where you want to use the image. Follow [the official Docker installation instructions](https://docs.docker.com/engine/install/) for your platform.

2. **An active secure.software Portal account and a Personal Access Token generated for it**. If you don't already have a Portal account, you may need to contact the administrator of your Portal organization to [invite you](https://docs.secure.software/portal/members#invite-a-new-member). Alternatively, if you're not a secure.software customer yet, you can [contact ReversingLabs](https://docs.secure.software/portal/#get-access-to-securesoftware-portal) to sign up for a Portal account. When you have an account set up, follow the instructions to [generate a Personal Access Token](https://docs.secure.software/api/generate-api-token).

3. **One or more software packages to analyze**. Your packages must be stored in a location that Docker will be able to access.


## Environment variables

The following environment variables can be used with this image.

| Environment variable    | Required | Description |
| :---------              | :--- | :--- |
| `RLPORTAL_ACCESS_TOKEN` | **Yes** | A Personal Access Token for authenticating requests to the secure.software Portal. Before you can use this Docker image, you must [create the token](https://docs.secure.software/api/generate-api-token) in your Portal settings. Tokens can expire and be revoked, in which case you'll have to update the value of this environment variable. It's strongly recommended to treat this token as a secret and manage it according to your organization's security best practices. |
| `RLSECURE_PROXY_SERVER` | No | Server name for proxy configuration (IP address or DNS name). |
| `RLSECURE_PROXY_PORT`   | No | Network port on the proxy server for proxy configuration. Required if `RLSECURE_PROXY_SERVER` is used. |
| `RLSECURE_PROXY_USER`   | No | User name for proxy authentication. |
| `RLSECURE_PROXY_PASSWORD` | No | Password for proxy authentication. Required if `RLSECURE_PROXY_USER` is used. |


## Configuration parameters

The `rl-scanner-cloud` image supports the following parameters.

| Parameter            | Required | Description     |
|:-------------------- |:--- | :---- |
| `--rl-portal-server` | **Yes** | Name of the secure.software Portal instance to use for the scan. The Portal instance name usually matches the subdirectory of `my.secure.software` in your Portal URL. For example, if your portal URL is `my.secure.software/demo`, the instance name to use with this parameter is `demo`. |
| `--rl-portal-org`    | **Yes** | The name of a secure.software Portal organization to use for the scan. The organization must exist on the Portal instance specified with `--rl-portal-server`. The user account authenticated with the token must be a member of the specified organization and have the appropriate permissions to upload and scan a file. Organization names are case-sensitive. |
| `--rl-portal-group`  | **Yes** | The name of a secure.software Portal group to use for the scan. The group must exist in the Portal organization specified with `--rl-portal-org`. Group names are case-sensitive. |
| `--purl`             | **Yes** | The package URL (PURL) used to associate the file with a project and package on the Portal. PURLs are unique identifiers in the format `[pkg:type/]<project></package><@version>`. When scanning a file, you must assign a PURL to it, so that it can be placed into the specified project and package as a version. If the project and package you specified don't exist in the Portal, they will be automatically created. The `pkg:type/` part of the PURL can be freely omitted, because the default value `pkg:rl/` is always automatically added. To analyze a reproducible build artifact of a package version, you must append the `?build=repro` parameter to the PURL of the artifact when scanning it, in the format `<project></package><@version?build=repro>`. |
| `--file-path`        | **Yes** | Path to the file you want to scan. The specified file must exist in the **package source** directory mounted to the Docker container. The file must be in any of the [formats supported by secure.software](https://docs.secure.software/concepts/reference). The file size on disk must not exceed 10 GB. |
| `--filename`         | No  | Optional name for the file you want to scan. If omitted, defaults to the file name specified with `--file-path`. When the file is uploaded and analyzed on the Portal, this file name is visible in the reports. |
| `--replace`          | No  | Replace (overwrite) an already existing package version with the file you're uploading. |
| `--force`            | No  | In secure.software Portal, a package can only have a limited amount of versions. If a package already has the maximum number of versions, you can use this optional parameter to delete the oldest version of the package and make space for the version you're uploading. |
| `--diff-with`        | No  | This optional parameter lets you specify a previous package version against which you want to compare (diff) the version you're uploading. The specified version must exist in the package. This parameter is ignored when analyzing reproducible build artifacts. |
| `--submit-only`      | No | By default, the Docker container runs until the uploaded file is analyzed on the Portal and returns the result in the output. This optional parameter lets you skip waiting for the analysis result. |
| `--timeout`          | No | This optional parameter lets you specify how long the container should wait for analysis to complete before exiting (in minutes). The parameter accepts any integer from 10 to 1440. The default timeout is 20 minutes. |
| `--message-reporter` | No  | Optional parameter that changes the format of output messages (STDOUT) for easier integration with CI tools. Supported values: `text`, `teamcity` |
| `--report-path`      | No  | Path to the location where you want to store analysis reports. The specified path must exist in the reports destination directory mounted to the container. |
| `--report-format`    | No  | A comma-separated list of report formats to generate. Supported values: cyclonedx, sarif, spdx, rl-json, rl-checks, all |


## Return codes

The Docker container can exit with the following return codes:

- `0` in cases when: the `--submit-only` parameter is used; the file is successfully analyzed on the Portal with CI status `PASS`
- `1` in cases when: the default or user-configured timeout expires; the file is successfully analyzed on the Portal with CI status `FAIL`; there is a problem with file scanning on the Portal
- any of the [standard chroot exit codes](https://docs.docker.com/engine/reference/run/#exit-status) in cases when there is a problem with Docker itself


## Scanning packages

### Scan a package version and add it to a Portal project

1. Prepare the file you want to scan and store it in a directory that will be mounted as your input (`/packages` directory - read-only).

2. On your Portal instance, check that the group to which you want to upload the file has enough reserved quota.

3. Start the container with the input directory mounted as a volume and your Personal Access Token provided as an environment variable.

The following command runs the container and uploads a file to the specified secure.software Portal instance for analysis. In our example, the portal URL is `my.secure.software/demo`, so the instance name is `demo`.

The file is added to the specified organization and group, and assigned as a version to the project and package specified in the PURL.
After the file is uploaded to the Portal, it's visible in the web interface while the analysis is pending.


    docker run \
      -u $(id -u):$(id -g) \
      -v "$(pwd)/packages:/packages:ro" \
      -e RLPORTAL_ACCESS_TOKEN=exampletoken \
      reversinglabs/rl-scanner-cloud \
      rl-scan \
        --rl-portal-server demo \
        --rl-portal-org ExampleOrg \
        --rl-portal-group demo-group \
        --purl my-project/my-package@1.0 \
        --file-path /packages/demo-packages/MyPackage_1.exe



4. The container exits automatically when the analysis is complete. You can then access the analysis report in the Portal web interface and continue to work with the package version you just uploaded.


### Scan a package version and download analysis reports

To download analysis reports, you can use the `--report-path` and `--report-format` parameters when scanning a file.
These parameters are optional, but they must be used together.

To store the reports to a specific location, you must use an additional volume and make sure Docker can write to it.
In this example, we're adding the volume with `-v "$(pwd)/reports:/reports"`, so the destination directory is going to be called `reports`. 
This destination directory must be created empty before starting the container.
You will then specify it in the Docker command with the `--report-path` parameter.

The `--report-format` parameter accepts any of the [supported report formats](https://docs.secure.software/cli/commands/report).
To request multiple formats at once, specify them as a comma-separated list.
The special value `all` will download all supported report formats.

The following command will scan a package version (1.0) and save all supported report formats into the `/reports` directory on the mounted volume.
Other configuration parameters are the same in this example as in the other examples in this text.


    docker run \
      -u $(id -u):$(id -g) \
      -v "$(pwd)/packages:/packages:ro" \
      -v "$(pwd)/reports:/reports" \
      -e RLPORTAL_ACCESS_TOKEN=exampletoken \
      reversinglabs/rl-scanner-cloud \
      rl-scan \
        --rl-portal-server demo \
        --rl-portal-org ExampleOrg \
        --rl-portal-group demo-group \
        --purl my-project/my-package@1.0 \
        --file-path /packages/demo-packages/MyPackage_1.exe \
        --report-path /reports \
        --report-format all 


### Compare package versions in a Portal project

To compare a new version of a package against a previously scanned version, you can use the `--diff-with` parameter when scanning the new version.
Both versions must be in the same Portal project and package.

The following command will scan a new package version (1.1) and generate a report with difference information against a previously analyzed package version (1.0).
Other configuration parameters are the same in this example as in the other examples in this text.


    docker run \
      -u $(id -u):$(id -g) \
      -v "$(pwd)/packages:/packages:ro" \
      -e RLPORTAL_ACCESS_TOKEN=exampletoken \
      reversinglabs/rl-scanner-cloud \
      rl-scan \
        --rl-portal-server demo \
        --rl-portal-org ExampleOrg \
        --rl-portal-group demo-group \
        --purl my-project/my-package@1.1 \
        --file-path /packages/demo-packages/MyPackage_1-1.exe \
        --diff-with=1.0


The analysis report of the new version will contain the **Diff** tab with all the differences between the two versions.
In the Portal web interface, the new version will be marked as "Derived" from the previous version.


### Perform reproducibility checks for a package version

To perform a [build reproducibility check](https://docs.secure.software/concepts/reproducibility), you need two build artifacts of the same package version.

If there is a previously scanned package version (for example, `my-project/my-package@1.0`), you can perform a reproducibility check by associating another build artifact with that version.
To do this, scan a new file with the `?build=repro` parameter appended to the PURL of the same version (for example, `my-project/my-package@1.0?build=repro`).
The previously scanned file is used as the reference against which the new build artifact we're scanning will be compared.

Every package version can have only one reproducible build artifact at a time.
If a version already has a reproducible build artifact and you want to scan another one, you must first remove the existing reproducible build artifact, or use the `--replace` parameter when scanning the new artifact.

The following command will scan the new artifact and perform a build reproducibility check for the version `my-project/my-package@1.0`.
Other configuration parameters are the same in this example as in the other examples in this text.


    docker run \
      -u $(id -u):$(id -g) \
      -v "$(pwd)/packages:/packages:ro" \
      -e RLPORTAL_ACCESS_TOKEN=exampletoken \
      reversinglabs/rl-scanner-cloud \
      rl-scan \
        --rl-portal-server demo \
        --rl-portal-org ExampleOrg \
        --rl-portal-group demo-group \
        --purl my-project/my-package@1.0?build=repro \
        --file-path /packages/demo-packages/MyPackage_1-build1.exe 


The analysis report will contain the **Reproducibility** tab with the reproducibility check status and a summary of differences between the reproducible build artifact and the main artifact ("Reference Version" in the report).
In the Portal web interface, you can expand the package version details to find *Reproducible build check* in the summary of checks and select *Details* to open the report.
