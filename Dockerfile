FROM ghcr.io/linuxserver/baseimage-kasmvnc:debianbookworm

# set version label
ARG BUILD_DATE
ARG VERSION
LABEL build_version="Metatrader Docker:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="gmartin"

# Set automatically by BuildKit (amd64 or arm64)
ARG TARGETARCH
# Wine release used on both architectures. Wine 11 trips MetaTrader's
# "a debugger has been found" check, so stay on 10.x.
ARG WINE_VERSION=10.0

ENV TITLE=Metatrader5
ENV WINEPREFIX="/config/.wine"
ENV WINEDEBUG=-all
# Only used on arm64: keep Box64 quiet in logs
ENV BOX64_LOG=0
ENV BOX64_NOBANNER=1

# Install all packages in a single layer to reduce image size
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    gnupg2 \
    software-properties-common \
    ca-certificates \
    xz-utils \
    && mkdir -pm755 /etc/apt/keyrings \
    && if [ "$TARGETARCH" = "arm64" ]; then \
        # ARM64 (e.g. Raspberry Pi 5): x86_64 Wine emulated by Box64
        wget -qO- https://pi-apps-coders.github.io/box64-debs/KEY.gpg | gpg --dearmor -o /etc/apt/keyrings/box64-archive-keyring.gpg \
        && echo "deb [signed-by=/etc/apt/keyrings/box64-archive-keyring.gpg] https://Pi-Apps-Coders.github.io/box64-debs/debian ./" > /etc/apt/sources.list.d/box64.list \
        && apt-get update \
        && apt-get install -y --no-install-recommends \
            box64-generic-arm \
            libasound2 \
            libcups2 \
            libdbus-1-3 \
            libegl1 \
            libfontconfig1 \
            libfreetype6 \
            libgl1 \
            libgnutls30 \
            libgssapi-krb5-2 \
            libkrb5-3 \
            libpulse0 \
            libvulkan1 \
            libx11-6 \
            libxcomposite1 \
            libxcursor1 \
            libxext6 \
            libxfixes3 \
            libxi6 \
            libxinerama1 \
            libxkbcommon0 \
            libxrandr2 \
            libxrender1 \
        && wget -qO /tmp/wine.tar.xz "https://github.com/Kron4ek/Wine-Builds/releases/download/${WINE_VERSION}/wine-${WINE_VERSION}-amd64-wow64.tar.xz" \
        && mkdir -p /opt/wine \
        && tar -xJf /tmp/wine.tar.xz -C /opt/wine --strip-components=1 \
        # Wrappers run the x86_64 Wine binaries through Box64. The installer and
        # terminal crash with Box64's default fast dynarec, so default to its
        # accurate settings (each can still be overridden from the environment).
        && for bin in wine wineserver; do \
            printf '%s\n' '#!/bin/sh' \
                'for v in STRONGMEM=2 SAFEFLAGS=2 BIGBLOCK=0 CALLRET=0 FASTNAN=0 FASTROUND=0 NATIVEFLAGS=0 DIRTY=0; do' \
                '    n=BOX64_DYNAREC_${v%%=*}; eval "[ -n \"\${$n+x}\" ] || export $n=${v#*=}"' \
                'done' \
                "exec box64 /opt/wine/bin/$bin \"\$@\"" > /usr/bin/$bin; \
        done \
        && for tool in wineboot winecfg msiexec regedit regsvr32 winepath; do \
            printf '#!/bin/sh\nexec wine %s "$@"\n' "$tool" > /usr/bin/$tool; \
        done \
        && ln -s /usr/bin/wine /usr/bin/wine64 \
        && chmod +x /usr/bin/wine /usr/bin/wineserver /usr/bin/wineboot /usr/bin/winecfg /usr/bin/msiexec /usr/bin/regedit /usr/bin/regsvr32 /usr/bin/winepath; \
    else \
        # AMD64: native WineHQ packages
        wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key \
        && wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/bookworm/winehq-bookworm.sources \
        && dpkg --add-architecture i386 \
        && apt-get update \
        && WINE_PKG_VERSION="${WINE_VERSION}.0.0~bookworm-1" \
        && apt-get install --install-recommends -y \
            winehq-stable=$WINE_PKG_VERSION \
            wine-stable=$WINE_PKG_VERSION \
            wine-stable-amd64=$WINE_PKG_VERSION \
            wine-stable-i386:i386=$WINE_PKG_VERSION \
        && rm -f /etc/apt/keyrings/winehq-archive.key; \
    fi \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


COPY /Metatrader /Metatrader
RUN chmod +x /Metatrader/start.sh
COPY /root /

EXPOSE 3000 8001
VOLUME /config
