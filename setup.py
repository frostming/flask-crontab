import io
import re
from setuptools import setup

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

with io.open("flask_crontab.py", "rt", encoding="utf8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)  # type: ignore


setup(
    name="flask-crontab",
    version=version,
    description="Simple Flask scheduled tasks without extra daemons",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="frostming",
    author_email="mianghong@gmail.com",
    url="https://github.com/frostming/flask-crontab",
    py_modules=["flask_crontab"],
    license="MIT",
    install_requires=["flask"],
    python_requires=">=3.5",
    entry_points={"flask.commands": ["crontab=flask_crontab:crontab_cli"]},
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
