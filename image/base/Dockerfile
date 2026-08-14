# NAME:     discourse/base
# VERSION:  release

ARG DEBIAN_RELEASE=trixie
ARG RUBY_VERSION=3.4.10
ARG FROM_DOCKER_IMAGE_TAG=${RUBY_VERSION}-${DEBIAN_RELEASE}-slim
ARG DATESTAMP=0

FROM discourse/ruby:${FROM_DOCKER_IMAGE_TAG} AS builder
ARG DATESTAMP
ARG DEBIAN_RELEASE
ENV DEBIAN_RELEASE=${DEBIAN_RELEASE}
RUN echo "deb http://deb.debian.org/debian ${DEBIAN_RELEASE}-backports main" > "/etc/apt/sources.list.d/${DEBIAN_RELEASE}-backports.list"
RUN apt update &&\
DEBIAN_FRONTEND=noninteractive apt-get -y install wget \
    autoconf build-essential \
    git \
    ccache \
    cmake \
    gnupg \
    libpcre2-dev \
    libfreetype-dev \
    libbrotli-dev

# BoringCache v1.19.1 targets ccache 4.13.6's @-attribute syntax. Keep
# Debian's compiler launchers, but use the same released ccache binary on both
# native runner architectures.
ARG CCACHE_VERSION=4.13.6
RUN set -eux; \
    architecture="$(dpkg --print-architecture)"; \
    case "$architecture" in \
      amd64) release_arch=x86_64; checksum=567b1b648411819590f918f045218c92da14418bdec3b30db94a3b4f5d77cf13 ;; \
      arm64) release_arch=aarch64; checksum=fae67fb810e1f0d390409af6603355483572229e19183e68574cd0f851a6fb98 ;; \
      *) echo "Unsupported ccache architecture: $architecture" >&2; exit 1 ;; \
    esac; \
    archive="ccache-${CCACHE_VERSION}-linux-${release_arch}-glibc.tar.gz"; \
    wget --quiet --tries=8 "https://github.com/ccache/ccache/releases/download/v${CCACHE_VERSION}/${archive}" -O "/tmp/${archive}"; \
    echo "${checksum}  /tmp/${archive}" | sha256sum --check; \
    tar xzf "/tmp/${archive}" -C /tmp; \
    install -m 0755 "/tmp/ccache-${CCACHE_VERSION}-linux-${release_arch}-glibc/ccache" /usr/bin/ccache; \
    ccache --version | grep -F "ccache version ${CCACHE_VERSION}"; \
    rm -rf "/tmp/${archive}" "/tmp/ccache-${CCACHE_VERSION}-linux-${release_arch}-glibc"

ENV PATH="/usr/lib/ccache:${PATH}" \
    CCACHE_COMPILERCHECK=content

FROM builder AS libheif-builder
ADD install-libheif /tmp/install-libheif
RUN /tmp/install-libheif && ccache --show-stats

FROM libheif-builder AS imagemagick_builder
ADD install-imagemagick /tmp/install-imagemagick
RUN /tmp/install-imagemagick && ccache --show-stats

FROM libheif-builder AS jpegli-builder
ADD install-jpegli /tmp/install-jpegli
RUN /tmp/install-jpegli && ccache --show-stats

FROM libheif-builder AS vips-builder
COPY --from=jpegli-builder /usr/local/lib/jpegli /usr/local/lib/jpegli
ADD install-vips /tmp/install-vips
RUN /tmp/install-vips && ccache --show-stats

FROM builder AS thpoff-builder
# This tool allows us to disable huge page support for our current process
# since the flag is preserved through forks and execs it can be used on any
# process
ADD thpoff.c /src/thpoff.c
RUN gcc -o /usr/local/sbin/thpoff /src/thpoff.c && rm /src/thpoff.c && ccache --show-stats

FROM builder AS jemalloc-builder
ADD install-jemalloc /tmp/install-jemalloc
RUN /tmp/install-jemalloc && ccache --show-stats

FROM builder AS oxipng-builder
ADD install-oxipng /tmp/install-oxipng
RUN /tmp/install-oxipng && ccache --show-stats

FROM discourse/ruby:${FROM_DOCKER_IMAGE_TAG} AS discourse-runtime-base
ARG DATESTAMP
ARG DEBIAN_RELEASE
ARG PG_MAJOR=18
ARG PG_MAJOR_OLD=15
ENV PG_MAJOR=${PG_MAJOR} \
    PG_MAJOR_OLD=${PG_MAJOR_OLD} \
    RUBY_ALLOCATOR=/usr/lib/libjemalloc.so \
    LEFTHOOK=0 \
    DEBIAN_RELEASE=${DEBIAN_RELEASE}

# Ensures that the gid and uid of the following users are consistent to avoid permission issues on directories in the
# mounted volumes.
RUN groupadd --gid 104 postgres &&\
    useradd --uid 101 --gid 104 --home /var/lib/postgresql --shell /bin/bash -c "PostgreSQL administrator,,," postgres &&\
    groupadd --gid 106 redis &&\
    useradd --uid 103 --gid 106 --home /var/lib/redis --shell /usr/sbin/nologin redis &&\
    groupadd --gid 1000 discourse &&\
    useradd --uid 1000 --gid 1000 -m --shell /bin/bash discourse

RUN echo 2.0.`date +%Y%m%d` > /VERSION
RUN echo "deb http://deb.debian.org/debian ${DEBIAN_RELEASE}-backports main" > "/etc/apt/sources.list.d/${DEBIAN_RELEASE}-backports.list"

COPY --from=libheif-builder /tmp/libheif-packages/libheif1.deb /tmp/libheif1.deb
COPY --from=libheif-builder /tmp/libheif-packages/discourse-libheif-guard.deb /tmp/discourse-libheif-guard.deb

RUN --mount=type=tmpfs,target=/var/log \
    --mount=type=tmpfs,target=/var/cache/apt \
    --mount=type=tmpfs,target=/var/lib/apt \
    echo "debconf debconf/frontend select Teletype" | debconf-set-selections &&\
    apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
# custom libheif packages
    /tmp/libheif1.deb /tmp/discourse-libheif-guard.deb \
# discourse runtime requirements
    gnupg sudo curl fping locales \
    ca-certificates rsync \
    gawk anacron wget \
    psmisc whois brotli \
    pngcrush pngquant ripgrep poppler-utils \
    catdoc antiword parallel \
# imagemagick runtime dependencies
    libjbig0 libtiff6 libpng16-16 libjpeg62-turbo libfontconfig1 \
    libwebpdemux2 libwebpmux3 libxext6 librsvg2-2 libgomp1 \
    fonts-urw-base35 \
# oxipng dependencies
    advancecomp jpegoptim libjpeg-turbo-progs \
# libvips runtime dependencies
    libglib2.0-0 libexpat1 libexif12 liblcms2-2 \
    liborc-0.4-0 libcgif0 libimagequant0 libjxl0.11 libwebp7 \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 &&\
# install these without recommends to avoid pulling in e.g.
# X11 libraries, mailutils
    DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends git rsyslog logrotate cron ssh-client less &&\
# postgres packages
    install -d /usr/share/postgresql-common/pgdg &&\
    curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc &&\
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${DEBIAN_RELEASE}-pgdg main" > /etc/apt/sources.list.d/pgdg.list &&\
# setup anacron, rsyslog, initctl
    sed -i -e 's/start -q anacron/anacron -s/' /etc/cron.d/anacron &&\
    sed -i.bak 's/$ModLoad imklog/#$ModLoad imklog/' /etc/rsyslog.conf &&\
    sed -i.bak 's/module(load="imklog")/#module(load="imklog")/' /etc/rsyslog.conf &&\
    dpkg-divert --local --rename --add /sbin/initctl &&\
    sh -c "test -f /sbin/initctl || ln -s /bin/true /sbin/initctl" &&\
    apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install runit socat \
    libpq-dev postgresql-client-${PG_MAJOR} postgresql-client-${PG_MAJOR_OLD} &&\
    mkdir -p /etc/runit/1.d &&\
    apt-mark hold libheif1 discourse-libheif-guard &&\
    rm /tmp/libheif1.deb /tmp/discourse-libheif-guard.deb &&\
    test "$(dpkg-query -W -f='${Version}' libheif1)" = "1.23.1-1discourse1"

ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8
RUN sed -i "s/^# $LANG/$LANG/" /etc/locale.gen &&\
    locale-gen

# nginx
RUN apt update &&\
    DEBIAN_FRONTEND=noninteractive apt-get -y install \
    nginx-light \
    libnginx-mod-http-brotli-filter \
    libnginx-mod-http-brotli-static

# Copy binary and configuration files for magick
COPY --from=imagemagick_builder /usr/local/bin/magick /usr/local/bin/magick
COPY --from=imagemagick_builder /usr/local/etc/ImageMagick-7 /usr/local/etc/ImageMagick-7
COPY --from=imagemagick_builder /usr/local/share/ImageMagick-7 /usr/local/share/ImageMagick-7
# Create symlinks to imagemagick tools
RUN ln -s /usr/local/bin/magick /usr/local/bin/animate &&\
  ln -s /usr/local/bin/magick /usr/local/bin/compare &&\
  ln -s /usr/local/bin/magick /usr/local/bin/composite &&\
  ln -s /usr/local/bin/magick /usr/local/bin/conjure &&\
  ln -s /usr/local/bin/magick /usr/local/bin/convert &&\
  ln -s /usr/local/bin/magick /usr/local/bin/display &&\
  ln -s /usr/local/bin/magick /usr/local/bin/identify &&\
  ln -s /usr/local/bin/magick /usr/local/bin/import &&\
  ln -s /usr/local/bin/magick /usr/local/bin/magick-script &&\
  ln -s /usr/local/bin/magick /usr/local/bin/mogrify &&\
  ln -s /usr/local/bin/magick /usr/local/bin/montage &&\
  ln -s /usr/local/bin/magick /usr/local/bin/stream &&\
  test $(magick -version | grep -o -e png -e tiff -e jpeg -e freetype -e heic -e webp | wc -l) -eq 6

COPY --from=vips-builder /usr/local/bin/vips /usr/local/bin/vips
COPY --from=vips-builder /usr/local/bin/vipsheader /usr/local/bin/vipsheader
COPY --from=vips-builder /usr/local/lib/libvips.so.42 /usr/local/lib/libvips.so.42
COPY --from=vips-builder /usr/local/lib/jpegli/lib/libjpeg.so.62.3.0 /usr/local/lib/jpegli/lib/libjpeg.so.62
RUN ldconfig &&\
  ruby -rfiddle -e 'lib = Fiddle.dlopen("libheif.so.1"); version = Fiddle::Function.new(lib["heif_get_version"], [], Fiddle::TYPE_VOIDP); abort "unexpected libheif version" unless Fiddle::Pointer.new(version.call).to_s == "1.23.1"' &&\
  ruby -rfiddle -e 'Fiddle.dlopen("libvips.so.42")' &&\
  sudo -u discourse vips --version &&\
  sudo -u discourse vipsheader --version &&\
  ldd /usr/local/bin/vips | grep -q '/usr/local/lib/libvips.so.42' &&\
  ldd /usr/local/bin/vipsheader | grep -q '/usr/local/lib/libvips.so.42' &&\
  ldd /usr/local/lib/libvips.so.42 | grep -q '/usr/local/lib/jpegli/lib/libjpeg.so.62' &&\
  ldd /usr/local/bin/magick | grep 'libjpeg.so.62' | grep -vq '/usr/local/lib/jpegli/' &&\
  sudo -u discourse vips black /tmp/vips-jpegli.jpg 1 1 &&\
  sudo -u discourse vipsheader /tmp/vips-jpegli.jpg >/dev/null &&\
  rm /tmp/vips-jpegli.jpg &&\
  for op in jpegload jpegsave pngload gifload webpload tiffload heifload jxlload svgload text thumbnail autorot gravity flatten; do \
    sudo -u discourse vips -l "$op" >/dev/null || { echo "ERROR: vips is missing operation: $op"; exit 1; }; \
  done &&\
  if dpkg-query -W -f '${Package} ${db:Status-Status}\n' ghostscript libgs10 libgs-common libgs10-common 2>/dev/null | grep -q ' installed$' || command -v gs >/dev/null; then \
    echo "ERROR: ghostscript must not be present in this image"; exit 1; \
  fi

COPY --from=thpoff-builder /usr/local/sbin/thpoff /usr/local/sbin
COPY --from=jemalloc-builder /usr/lib/libjemalloc.so /usr/lib
COPY --from=oxipng-builder /usr/local/bin/jhead /usr/local/bin
COPY --from=oxipng-builder /usr/local/bin/oxipng /usr/local/bin

# version check: https://rubygems.org/gems/pups
RUN cd /tmp &&\
    gem fetch pups --version 1.4.0 &&\
    echo "5809731d6f4819defe1aac694e614c4b3d9958b5f378a70edf761f3808877052 pups-1.4.0.gem" | sha256sum -c &&\
    gem install --local --force pups-1.4.0.gem &&\
    rm pups-1.4.0.gem &&\
    mkdir -p /pups/bin/ &&\
    ln -s /usr/local/bin/pups /pups/bin/pups

# this is required for aarch64 which uses buildx
# see https://github.com/docker/buildx/issues/150
RUN rm -f /etc/service

COPY etc/  /etc
COPY sbin/ /sbin

FROM discourse-runtime-base AS discourse-build-base
COPY --from=builder /usr/bin/ccache /usr/bin/ccache
COPY --from=builder /usr/lib/ccache /usr/lib/ccache
ENV PATH="/usr/lib/ccache:${PATH}" \
    CCACHE_COMPILERCHECK=content

# From https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key
# fingerprint: 6F71 F525 2828 41EE DAF8 51B4 2F59 B5F9 9B1B E0B4
ADD nodesource-repo.gpg.key /usr/share/keyrings/nodesource.asc
RUN --mount=type=tmpfs,target=/var/log \
    --mount=type=tmpfs,target=/var/cache/apt \
    --mount=type=tmpfs,target=/var/lib/apt \
# node packages
    printf 'Types: deb\nURIs: https://deb.nodesource.com/node_22.x\nSuites: nodistro\nComponents: main\nSigned-By: /usr/share/keyrings/nodesource.asc\n' > /etc/apt/sources.list.d/nodesource.sources &&\
    printf 'Package: nodejs\nPin: origin deb.nodesource.com\nPin-Priority: 600\n' > /etc/apt/preferences.d/nodejs &&\
    echo "debconf debconf/frontend select Teletype" | debconf-set-selections; \
    apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
# gem build dependencies
    cmake g++ pkg-config patch \
    libtool \
    libxslt-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libyaml-dev \
    libxml2-dev \
    libreadline-dev \
    libunwind-dev \
# node
    nodejs

# pnpm
RUN --mount=type=tmpfs,target=/root/.npm \
    npm install -g pnpm@10

FROM discourse-build-base AS discourse-slim
ARG DISCOURSE_BRANCH=main

# Discourse specific bits
RUN install -dm 0755 -o discourse -g discourse /var/www/discourse &&\
    sudo -u discourse git clone --branch $DISCOURSE_BRANCH --filter=tree:0 https://github.com/discourse/discourse.git /var/www/discourse

FROM discourse-slim AS discourse-web-only
ENV RAILS_ENV=production

RUN --mount=type=cache,id=discourse-bundle-${DISCOURSE_BRANCH},target=/home/discourse/.cache/bundle,sharing=locked \
    chown discourse:discourse /home/discourse/.cache/bundle &&\
    cd /var/www/discourse &&\
    echo "Installed bundle cache before install:" &&\
    sudo -u discourse du -sh /home/discourse/.cache/bundle &&\
    sudo -u discourse bundle config --local deployment true &&\
    sudo -u discourse bundle config --local path /home/discourse/.cache/bundle &&\
    sudo -u discourse bundle config --local without test development &&\
    sudo -u discourse bundle install --jobs $(nproc --ignore=1) &&\
    ccache --show-stats &&\
    echo "Installed bundle cache after install:" &&\
    sudo -u discourse du -sh /home/discourse/.cache/bundle &&\
    rm -rf /var/www/discourse/vendor/bundle &&\
    install -dm 0755 -o discourse -g discourse /var/www/discourse/vendor/bundle &&\
    cp -a /home/discourse/.cache/bundle/. /var/www/discourse/vendor/bundle/ &&\
    sudo -u discourse bundle config --local path ./vendor/bundle &&\
    sudo -u discourse bundle install --jobs $(nproc --ignore=1) &&\
    sudo -u discourse bundle check &&\
    find /var/www/discourse/vendor/bundle -name cache -not -path '*/gems/*' -type d -exec rm -rf {} + &&\
    find /var/www/discourse/vendor/bundle -name tmp -type d -exec rm -rf {} +

RUN install -dm 0755 -o discourse -g discourse /var/www/discourse/.pnpm-store
RUN --mount=type=cache,id=discourse-pnpm-${DISCOURSE_BRANCH},target=/var/www/discourse/.pnpm-store,sharing=locked \
    chown discourse:discourse /var/www/discourse/.pnpm-store &&\
    cd /var/www/discourse &&\
    pnpm_store="$(sudo -u discourse pnpm store path --store-dir=/var/www/discourse/.pnpm-store)" &&\
    case "$pnpm_store" in /var/www/discourse/.pnpm-store/*) ;; *) echo "Unexpected pnpm store: $pnpm_store" >&2; exit 1 ;; esac &&\
    echo "pnpm store before install: $pnpm_store" &&\
    du -sh /var/www/discourse/.pnpm-store &&\
    sudo -u discourse /bin/bash -c 'pnpm install --store-dir=/var/www/discourse/.pnpm-store --frozen-lockfile' &&\
    echo "pnpm store after install: $pnpm_store" &&\
    du -sh /var/www/discourse/.pnpm-store

FROM discourse-web-only AS discourse-release
RUN --mount=type=tmpfs,target=/var/log \
  apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
  postgresql-${PG_MAJOR} postgresql-contrib-${PG_MAJOR} postgresql-${PG_MAJOR}-pgvector
RUN apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install redis
