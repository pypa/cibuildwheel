---
title: Home
---

# cibuildwheel

{%
   include-markdown "../README.md"
   start="<!--intro-start-->"
   end="<!--intro-end-->"
%}

!!! warning "A note on security"
      Building and testing wheels executes arbitrary code from your project and its dependencies. To maintain security standards: keep the job that builds distributions separate from the job that uploads them to PyPI, handle secrets and credentials with care and rotate them regularly, and follow the principle of least privilege when granting permissions. Do not store sensitive data on CI runners. It is a good idea to follow [the Python Packaging Authority's guides](https://packaging.python.org/en/latest/guides/).

To get started, head over to the [setup guide](setup.md).

How it works
------------

This diagram summarises the steps that cibuildwheel takes on each platform to build your package's wheels.

{%
   include "diagram.html"
%}

This isn't exhaustive, for a full list of the things cibuildwheel can do, check the [options](options.md) page.
