Contributing
============

Wheel-building can be pretty complex. I expect users to find many edge-cases - please help the rest of the community out by documenting these, adding features to support them, and reporting bugs.

I plan to be pretty liberal in accepting pull requests, as long as they align with the design goals below.

`cibuildwheel` is indie open source. I'm not paid to work on this.

Design Goals
------------

- `cibuildwheel` should wrap the complexity of wheel building.
- The user interface to `cibuildwheel` is the build script (e.g. `.travis.yml`). Feature additions should not increase the complexity of this script.
- Options should be environment variables (these lend themselves better to YML config files). They should be prefixed with `CIBW_`.
- Options should be generalise to all platforms. If platform-specific options are required, they should be namespaced e.g. `CIBW_TEST_COMMAND_MACOS`

Other notes:

- The platforms are very similar, until they're not. I'd rather have straight-forward code than totally DRY code, so let's keep airy platfrom abstractions to a minimum.
- I might want to break the options into a shared config file one day, so that config is more easily shared. That has motivated some of the design decisions.

### cibuildwheel's relationship with build errors

cibuildwheel doesn't really do anything itself - it's always deferring to other tools (pip, wheel, auditwheel, delocate, docker). Without cibuildwheel, the process is really fragmented. Different tools, across different OSs need to be stitched together in just the right way to make it work.

We're not responsible for errors in those tools, for fixing errors/crashes there. But cibuildwheel's job is providing users with an 'integrated' user experience across those tools. We provide an abstraction. The user says 'build me some wheels', not 'open the docker container, build a wheel with pip, fix up the symbols with auditwheel' etc.  However, errors have a habit of breaking abstractions. And this is where users get confused, because the mechanism of cibuildwheel is laid bare, and they must understand a little bit how it works to debug.

So, if we can, I'd like to improve the experience on errors as well. In [this](https://github.com/joerick/cibuildwheel/issues/139) case, it takes a bit of knowledge to understand that the linux builds are happening in a totally different OS via docker, that the linked symbols won't match, that auditwheel will fail because of this. A problem with how the tools fit together, instead of the tools themselves.
