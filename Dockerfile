# syntax=docker/dockerfile:1
FROM rockylinux:9-minimal

# LABEL info from: https://github.com/opencontainers/image-spec/blob/main/annotations.md

LABEL org.opencontainers.image.authors=secure.software@reversinglabs.com
LABEL org.opencontainers.image.url=https://www.secure.software/
LABEL org.opencontainers.image.vendor=ReversingLabs

RUN microdnf upgrade -y && \
    microdnf install -y --nodocs python3-pip &&  \
    pip3 install requests &&  \
    pip3 uninstall setuptools -y &&  \
    microdnf remove pip -y &&  \
    microdnf clean all

COPY scripts/* /opt/rl-scanner-cloud/

RUN chmod 755 /opt/rl-scanner-cloud/entrypoint \
              /opt/rl-scanner-cloud/rl-scan

ENV PATH="/opt/rl-scanner-cloud:${PATH}"

ENTRYPOINT ["/opt/rl-scanner-cloud/entrypoint"]
