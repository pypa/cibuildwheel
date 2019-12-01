---
title: Modern C++ standards
---

Building Python wheels with modern C++ (C++11) requires a few tricks.

Creating wheel for python 2.7 which need c++17 needs special configuration because python 2.7 header files using `register` keyword. 
In c++17 this keyword is reserved ((see)[https://en.cppreference.com/w/cpp/keyword/register])
It is possible to allow usage of `register` using proper flag `-Wno-register` for gcc/clang and `/wd5033` for MSVC. 

## Linux
When using default `manylinux1` image it is possible to use only c++11 and earlier standards. 
This is about how you can make C++14 wheels in `manylinux1`, through some tricks https://github.com/pypa/manylinux/issues/118

`manylinux2010` supports all C++ standards (up to c++17). 

## MacOS

To get C++11 and C++14 support, set `MACOSX_DEPLOYMENT_TARGET` variable to `"10.9"`.

To get C++17 support, set `MACOSX_DEPLOYMENT_TARGET` variable to `"10.13"` or `"10.14"`. (`"10.13"` supports C++17 partially, e.g. the filesystem header is in experimental: `#include <filesystem>` -> `#include <experimental/filesystem>`)

For more details see https://en.cppreference.com/w/cpp/compiler_support and https://xcodereleases.com/
(Xcode 10 needs MacOs 10.13 and Xcode 11 needs MacOS 10.14)

## Windows

Visual C++ for Python 2.7 does not support modern standards of C++.
When building on Appveyor, you'll need to use either the 'Visual Studio 2017' or 'Visual Studio 2019' image. Note that Python 2.7 isn't supported on these images - you should skip it using `CIBW_SKIP=cp27-win*`.

There is option for workaround this limitation. PyBind project has in documentation example how to compile python 2.7 extension with newer compiler https://github.com/pybind/python_example