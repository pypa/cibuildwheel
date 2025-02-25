### Linux builds

If you've got [Docker](https://www.docker.com/products/docker-desktop) installed on your development machine, you can run a Linux build.

!!! tip
    You can run the Linux build on any platform. Even Windows can run
    Linux containers these days, but there are a few hoops to jump
    through. Check [this document](https://docs.microsoft.com/en-us/virtualization/windowscontainers/quick-start/quick-start-windows-10-linux)
    for more info.

Because the builds are happening in manylinux Docker containers, they're perfectly reproducible.

The only side effect to your system will be docker images being pulled.
