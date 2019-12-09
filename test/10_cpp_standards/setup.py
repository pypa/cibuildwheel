import os, sys
from setuptools import setup, Extension
import platform

standard = os.environ["STANDARD"]

language_standard = "/std:c++" + standard if platform.system() == "Windows" else "-std=c++" + standard

extra_compile_args = [language_standard, "-DSTANDARD=" + standard]

if standard == "17":
    if platform.system() == "Windows":
        extra_compile_args.append("/wd5033")
    else:
        extra_compile_args.append("-Wno-register")

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.cpp'], language="c++", extra_compile_args=extra_compile_args)],
    version="0.1.0",
)
