FROM debian:trixie

WORKDIR /root

RUN apt-get update && \
    apt-get -y install bzip2 wget

ARG arch
RUN if [ "${arch:?}" = "aarch64" ]; then arch="arm64"; fi && \
    filename="gcc-$arch-linux-x86_64.tar.bz2" && \
    wget "https://github.com/mzakharo/android-gfortran/releases/download/r21e/$filename" && \
    tar -xf "$filename"

COPY fortran-entrypoint.sh ./
ENTRYPOINT ["./fortran-entrypoint.sh"]
