#
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

# Specify all Docker arguments for the Dockerfile
ARG BASE_IMAGE=ubuntu:22.04
FROM ${BASE_IMAGE} AS bor-server
LABEL description="Business Offer Recommender Server" 
LABEL vendor="Intel Corporation"

ARG BOR_VERSION=0.1.0

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

RUN \
    apt-get update && \
    apt-get install -y -q --no-install-recommends gnupg=\* ca-certificates=\* wget=\* libtbb-dev=\* git=\* git-lfs=\* vim=\* numactl=\* && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python, pip and venv
RUN export no_proxy= && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3=\* python3-venv=\*  python3-pip=\*  && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG DEBIAN_FRONTEND=noninteractive

RUN export no_proxy= && \
    apt-get update -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash boruser && \
    chown -R boruser: /opt && \
    chmod -R u+rw /opt

RUN \
    mkdir /python3venv && \
    chown -R boruser: /python3venv && \
    chmod -R u+w /python3venv

ENV PATH=/python3venv/bin:$PATH
ENV TERM=xterm

WORKDIR /home/boruser
USER boruser

RUN \
    python3 -m venv /python3venv && \
    /python3venv/bin/pip3 install --no-cache-dir --upgrade pip


######################## Update required packages ################################
USER root

WORKDIR /home/boruser

ARG USER
ARG UID

RUN useradd -ms /bin/bash -G users,plugdev ${USER} -o -u $UID && \
    chown ${USER}:${USER} -R /root

RUN mkdir -p /home/${USER}/ && chown -R ${USER}:${USER} /home/${USER}

WORKDIR /home/bor-server
USER $USER

# Copy source code
COPY ./docker/run.sh .
COPY ./src/ ./src

# Install server requirements
USER boruser
RUN pip3 install --no-cache-dir -r  /home/bor-server/src/requirements.txt 

USER ${USER}
ENTRYPOINT ["./run.sh"]