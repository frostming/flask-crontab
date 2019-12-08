import io
import re
import os
import sys
from setuptools import setup, Command

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

with io.open("flask_crontab.py", "rt", encoding="utf8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)  # type: ignore


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            from shutil import rmtree

            self.status("Removing previous builds…")
            rmtree("dist")
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags...")
        os.system("git tag v{0}".format(version))
        os.system("git push --tags")

        sys.exit()


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
    cmdclass={"publish": UploadCommand},
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
