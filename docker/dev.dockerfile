FROM ubuntu:22.04 AS base

USER root

# coloring syntax for headers
ENV CYAN='\033[0;36m'
ENV CLEAR='\033[0m'
ENV DEBIAN_FRONTEND='noninteractive'

# setup ubuntu user
ARG UID_='1000'
ARG GID_='1000'
RUN echo "\n${CYAN}SETUP UBUNTU USER${CLEAR}"; \
    addgroup --gid $GID_ ubuntu && \
    adduser \
        --disabled-password \
        --gecos '' \
        --uid $UID_ \
        --gid $GID_ ubuntu && \
    usermod -aG root ubuntu

# setup sudo
RUN echo "\n${CYAN}SETUP SUDO${CLEAR}"; \
    apt update && \
    apt install -y sudo && \
    usermod -aG sudo ubuntu && \
    echo '%ubuntu    ALL = (ALL) NOPASSWD: ALL' >> /etc/sudoers && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /home/ubuntu

# update ubuntu and install basic dependencies
RUN echo "\n${CYAN}INSTALL GENERIC DEPENDENCIES${CLEAR}"; \
    apt update && \
    apt install -y \
        curl \
        git \
        graphviz \
        npm \
        pandoc \
        parallel \
        software-properties-common \
        tree \
        vim \
        wget && \
    rm -rf /var/lib/apt/lists/*

RUN echo "\n${CYAN}INSTALL PYTHON${CLEAR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y \
        python3-pydot \
        python3.10-dev \
        python3.10-venv \
        python3.10-distutils \
        python3.9-dev \
        python3.9-venv \
        python3.9-distutils \
        python3.8-dev \
        python3.8-venv \
        python3.8-distutils \
        python3.7-dev \
        python3.7-venv \
        python3.7-distutils && \
    rm -rf /var/lib/apt/lists/*

RUN echo "\n${CYAN}INSTALL PIP${CLEAR}"; \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3.10 get-pip.py && \
    pip3.10 install --upgrade pip && \
    rm -rf get-pip.py

# install zsh
RUN echo "\n${CYAN}SETUP ZSH${CLEAR}"; \
    apt update && \
    apt install -y zsh && \
    rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh \
        -o install-oh-my-zsh.sh && \
    echo y | sh install-oh-my-zsh.sh && \
    mkdir -p /root/.oh-my-zsh/custom/plugins && \
    cd /root/.oh-my-zsh/custom/plugins && \
    git clone https://github.com/zdharma-continuum/fast-syntax-highlighting && \
    git clone https://github.com/zsh-users/zsh-autosuggestions && \
    npm i -g zsh-history-enquirer --unsafe-perm && \
    cd /home/ubuntu && \
    cp -r /root/.oh-my-zsh /home/ubuntu/ && \
    chown -R ubuntu:ubuntu .oh-my-zsh && \
    rm -rf install-oh-my-zsh.sh && \
    echo 'UTC' > /etc/timezone

USER ubuntu
ENV PATH="/home/ubuntu/.local/bin:$PATH"
COPY ./config/henanigans.zsh-theme .oh-my-zsh/custom/themes/henanigans.zsh-theme

ENV LANG "C.UTF-8"
ENV LANGUAGE "C.UTF-8"
ENV LC_ALL "C.UTF-8"
# ------------------------------------------------------------------------------

FROM base AS dev

USER ubuntu
WORKDIR /home/ubuntu

RUN echo "\n${CYAN}INSTALL PDM${CLEAR}"; \
    curl -sSL \
        https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py \
    | python3.10 - && \
    pip3.10 install --upgrade pdm && \
    mkdir -p /home/ubuntu/.oh-my-zsh/custom/completions && \
    pdm completion zsh > /home/ubuntu/.oh-my-zsh/custom/completions/_pdm

USER root
RUN echo "\n${CYAN}CREATE DEV AND PROD DIRECTORIES${CLEAR}"; \
    mkdir dev prod && \
    chown ubuntu:ubuntu dev prod
USER ubuntu

# install python dependencies
COPY --chown=ubuntu:ubuntu dev/pyproject.toml /home/ubuntu/dev/
COPY --chown=ubuntu:ubuntu dev/pdm.lock /home/ubuntu/dev/
COPY --chown=ubuntu:ubuntu dev/.pdm.toml /home/ubuntu/dev/.pdm.toml
RUN echo "\n${CYAN}INSTALL PYTHON DEV ENVIRONMENT${CLEAR}"; \
    cd dev && \
    pdm install --no-self --dev -v && \
    pdm export \
        --no-default \
        -dG lab \
        --without-hashes \
        --format requirements \
        --output lab_requirements.txt && \
    pip3.10 install --user -r lab_requirements.txt

# install prod dependencies
COPY --chown=ubuntu:ubuntu prod/pyproject.toml /home/ubuntu/prod/
COPY --chown=ubuntu:ubuntu prod/pdm.lock /home/ubuntu/prod/
COPY --chown=ubuntu:ubuntu prod/.pdm.toml /home/ubuntu/prod/.pdm.toml
RUN echo "\n${CYAN}INSTALL PYTHON PROD ENVIRONMENT${CLEAR}"; \
    cd prod && \
    pdm use /usr/bin/python3.7  && pdm install --no-self --dev -v && \
    pdm use /usr/bin/python3.8  && pdm install --no-self --dev -v && \
    pdm use /usr/bin/python3.9  && pdm install --no-self --dev -v && \
    pdm use /usr/bin/python3.10 && pdm install --no-self --dev -v

RUN echo "\n${CYAN}CREATE SYMBOLIC LINK${CLEAR}"; \
    find /home/ubuntu/dev  -type f -maxdepth 1 | parallel 'rm -rf {}' && \
    find /home/ubuntu/prod -type f -maxdepth 1 | parallel 'rm -rf {}' && \
    ln -s /home/ubuntu/dev/__pypackages__ /home/ubuntu/

ENV REPO='rolling-pin'
ENV REPO_ENV=True
ENV PYTHONPATH ":/home/ubuntu/$REPO/python:/home/ubuntu/.local/share/pdm/venv/lib/python3.10/site-packages/pdm/pep582:/home/ubuntu/.local/lib"
