from distutils.core import setup

PACKAGE = "fnpy"
NAME = "fnpy"
DESCRIPTION = ""
AUTHOR = "isaac"
AUTHOR_EMAIL = "ndtm.idea@gmail.com"
URL = "https://github.com/gfZeng/fn.py"
VERSION = __import__(PACKAGE).__version__

setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license="BSD",
    url=URL,
    packages=["fnpy"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Framework :: Django",
    ],
    zip_safe=False,
)
