FROM registry.fedoraproject.org/fedora:latest
RUN dnf install -y gcc git-core meson pkg-config \
    python3-requests python3-pyyaml \
    cairo-devel glib2-devel libdicom-devel libjpeg-turbo-devel libpng-devel \
    libtiff-devel libxml2-devel libzstd-devel openjpeg2-devel sqlite-devel \
    zlib-devel \
    libjpeg-turbo-utils valgrind valgrind-devel xdelta \
    dnf-plugins-core && \
    dnf debuginfo-install -y cairo fontconfig glib2 && \
    dnf clean all
COPY test.sh /
CMD ["/bin/bash", "/test.sh"]
ENV PYTHONUNBUFFERED=1
