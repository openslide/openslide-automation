FROM registry.fedoraproject.org/fedora:latest
RUN dnf install -y gcc git-core meson pkg-config \
    python3-requests python3-pyyaml diffutils \
    zlib-devel libzstd-devel libpng-devel libjpeg-turbo-devel libtiff-devel \
    openjpeg2-devel libdicom-devel libxml2-devel sqlite-devel cairo-devel \
    glib2-devel libjpeg-turbo-utils valgrind valgrind-devel xdelta \
    dnf-plugins-core && \
    dnf debuginfo-install -y cairo fontconfig glib2 && \
    dnf clean all
COPY test.sh /
CMD ["/bin/bash", "/test.sh"]
ENV PYTHONUNBUFFERED=1
