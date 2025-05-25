---
title: 'Getting started'
---

# Getting started

Before getting to [CI setup](ci-services.md), it can be convenient to test cibuildwheel locally to quickly iterate and track down issues without having to commit each change, push, and then check CI logs.

Install cibuildwheel and run a build like this:

```sh
# run using uv
uvx cibuildwheel

# or pipx
pipx run cibuildwheel

# or, install it first
pip install cibuildwheel
cibuildwheel
```

!!!tip
    You can pass the `--platform linux` option to cibuildwheel to build Linux wheels, even if you're not on Linux. On most machines, the easiest builds to try are the Linux builds. You don't need any software installed except a Docker daemon, such as [Docker Desktop](https://www.docker.com/get-started/). Each platform that cibuildwheel supports has its own system requirements and platform-specific behaviors. See the [platforms page](platforms.md) for details.

You should see the builds taking place. You can experiment with [options](options.md) using pyproject.toml or environment variables.

!!! tab "pyproject.toml"

    If you write your options into [`pyproject.toml`](configuration.md#configuration-file), you can work on your options locally, and they'll be automatically picked up when running in CI.

    > pyproject.toml

    ```
    [tool.cibuildwheel]
    before-all = "uname -a"
    ```

    Then invoke cibuildwheel, like:

    ```console
    cibuildwheel
    ```

!!! tab "Environment variables"

    cibuildwheel will read config from the environment. Syntax varies, depending on your shell:

    > POSIX shell (Linux/macOS)

    ```sh
    # run a command to set up the build system
    export CIBW_BEFORE_ALL='uname -a'

    cibuildwheel
    ```

    > CMD (Windows)

    ```bat
    set CIBW_BEFORE_ALL='uname -a'

    cibuildwheel
    ```

- Once you've got a build working locally, you can move on to [setting up a CI service](ci-services.md).
- View the [full options reference](options.md) to see what cibuildwheel can do.
- Check out the [FAQ](faq.md) for common questions.
