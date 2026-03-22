---
title: Home
---

# cibuildwheel

{%
   include-markdown "../README.md"
   start="<!--intro-start-->"
   end="<!--intro-end-->"
%}

To get started, head over to the [setup guide](setup.md).

How it works
------------

This diagram summarises the steps that cibuildwheel takes on each platform to build your package's wheels.

{%
   include "diagram.html"
%}

This isn't exhaustive, for a full list of the things cibuildwheel can do, check the [options](options.md) page.

!!! warning "A note on security"
      Building and testing wheels executes arbitrary code from your project and its dependencies. Although cibuildwheel uses OCI containers and Pyodide for some builds, these provide no security guarantees - the code you're building and testing has full access to the environment that's invoking cibuildwheel.

      If you cannot trust all the code that's pulled in, maintain good security hygiene: keep the job that builds distributions separate from the job that uploads them to PyPI, handle secrets and credentials with care and rotate them regularly, and follow the principle of least privilege when granting permissions. Do not store sensitive data on CI runners.
