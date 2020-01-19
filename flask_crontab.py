"""
    flask-crontab
    ~~~~~~~~~~~~~
    Simple Flask scheduled tasks without extra daemons

    :author: Frost Ming
    :email: mianghong@gmail.com
    :license: MIT
"""
import fcntl
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, Tuple, Any, Callable, List, Optional

import click
from flask import current_app, Flask
from flask.cli import with_appcontext

logger = logging.getLogger(__name__)
__version__ = "0.1.2"
__all__ = ["Crontab"]


def _ensure_extension_object():
    obj = current_app.extensions.get("crontab")
    if not obj:
        raise RuntimeError(
            "Flask-Crontab extension is not registered yet. Please call "
            "'Crontab(app)' or 'crontab.init_app(app)' before using."
        )
    return obj


class _CronJob:
    """An object to represent a cron job.

    Arguments:
        func: the function to run
        minute, hour, day, month, day_of_week: The same as crontab schedule definitions,
            if not given, '*' is implied.
        args: An tuple of positional arguments passed to func.
        kwargs: A dict of keyword arguments passed to func.
    """

    def __init__(
        self,
        func: Callable,
        *,
        minute: str,
        hour: str,
        day: str,
        month: str,
        day_of_week: str,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any]
    ) -> None:
        self.func = func
        self.schedule = "{} {} {} {} {}".format(minute, hour, day, month, day_of_week)
        self.args = args
        self.kwargs = kwargs
        self.func_ident = "{func.__module__}:{func.__name__}".format(func=func)

    @property
    def hash(self) -> str:
        data = {
            "name": self.func_ident,
            "schedule": self.schedule,
            "args": self.args,
            "kwargs": self.kwargs,
        }
        j = json.JSONEncoder(sort_keys=True).encode(data)
        h = hashlib.md5(j.encode("utf-8")).hexdigest()
        return h

    def run(self) -> None:
        try:
            self.func(*self.args, **self.kwargs)
        except Exception:
            logger.exception("Failed to complete cronjob at %s", self.func_ident)
            raise

    def as_crontab_line(self) -> str:
        flask_bin = sys.executable + " -m flask"
        env_prefix = (
            "FLASK_APP={} ".format(os.getenv("FLASK_APP"))
            if os.getenv("FLASK_APP")
            else ""
        )
        crontab_comment = "Flask cron jobs for {}".format(current_app.name)
        line = "{} cd {} && {}{} crontab run {}  # {}".format(
            self.schedule,
            os.getcwd(),
            env_prefix,
            flask_bin,
            self.hash,
            crontab_comment,
        )
        return line


class _Crontab:
    CRONTAB_LINE_REGEXP = re.compile(
        r"^\s*((?:[^#\s]+\s+){5})([^#\n]*?)\s*(?:#\s*([^\n]*)|$)"
    )

    def __init__(self, *, verbose: bool = True, readonly: bool = False):
        obj = _ensure_extension_object()
        self.jobs = obj.jobs
        self.verbose = verbose
        self.readonly = readonly
        self.crontab_lines = []  # type: List[str]
        self.settings = current_app.config.get_namespace("CRONTAB_")
        self.crontab_comment = "Flask cron jobs for {}".format(current_app.name)

    def __enter__(self) -> "_Crontab":
        """
        Automatically read crontab when used as with statement
        """
        self.read()
        return self

    def __exit__(self, type, value, traceback) -> None:
        """
        Automatically write back crontab when used as with statement
        if readonly is False
        """
        if not self.readonly:
            self.write()

    def __get_crontab_lines(self):
        try:
            return subprocess.run(
                [self.settings["executable"], "-l"], stdout=subprocess.PIPE
            ).stdout.decode("utf-8").splitlines()
        except AttributeError:
            return []

    def read(self) -> None:
        """
        Reads the crontab into internal buffer
        """
        self.crontab_lines[:] = self.__get_crontab_lines()

    def write(self) -> None:
        """
        Writes internal buffer back to crontab
        """
        fd, path = tempfile.mkstemp()
        tmp = os.fdopen(fd, "w")
        for line in self.crontab_lines:
            tmp.write(line + "\n")
        tmp.close()
        # replace the contab with the temporary file
        subprocess.run([self.settings["executable"], path], stdout=subprocess.PIPE)
        os.unlink(path)

    def add_jobs(self) -> None:
        """
        Adds all jobs defined in CRONJOBS setting to internal buffer
        """
        for job in self.jobs:
            print("Adding cronjob: {} -> {}".format(job.hash, job.func_ident))
            self.crontab_lines.append(job.as_crontab_line())

    def show_jobs(self) -> None:
        """
        Print the jobs from from crontab
        """
        print("Currently active jobs in crontab:")
        for line in self.crontab_lines:
            # check if the line describes a crontab job
            job = self.CRONTAB_LINE_REGEXP.match(line)
            if not job:
                continue
            # if the job is generated using django_crontab for this application
            sched, script, comment = job.groups()
            if comment == self.crontab_comment:
                job_hash = script.split("crontab run ")[1]
                print(
                    "{} -> {}".format(
                        job_hash, self.__get_job_by_hash(job_hash).func_ident
                    )
                )

    def remove_jobs(self) -> None:
        """
        Removes all jobs defined in CRONJOBS setting from internal buffer
        """
        for line in self.crontab_lines[:]:
            # check if the line describes a crontab job
            job = self.CRONTAB_LINE_REGEXP.match(line)
            if not job:
                continue
            # if the job is generated using django_crontab for this application
            sched, script, comment = job.groups()
            if comment == self.crontab_comment:
                self.crontab_lines.remove(line)
                # output the action if the verbose option is specified
                job_hash = script.split("crontab run ")[1]
                if self.verbose:
                    print(
                        "Removing cronjob: {} -> {}".format(
                            job_hash, self.__get_job_by_hash(job_hash).func_ident
                        )
                    )

    # noinspection PyBroadException
    def run_job(self, job_hash: str) -> None:
        """
        Executes the corresponding function defined in CRONJOBS
        """
        job = self.__get_job_by_hash(job_hash)

        lock_file_name = None
        # if the LOCK_JOBS option is specified in settings
        if self.settings["lock_jobs"]:
            # create and open a lock file
            lock_file = open(
                os.path.join(
                    tempfile.gettempdir(), "flask_crontab_%s.lock" % job_hash
                ),
                "w",
            )
            lock_file_name = lock_file.name
            try:
                # acquire the lock
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                logger.warning(
                    "Tried to start cron job %s that is already running.", job
                )
                return
        # run the function
        job.run()

        # if the LOCK_JOBS option is specified in settings
        if self.settings["lock_jobs"]:
            try:
                # release the lock
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except IOError:
                logger.exception("Error unlocking %s", lock_file_name)
                return

    def __get_job_by_hash(self, job_hash):
        """
        Finds the job by given hash
        """
        for job in self.jobs:
            if job.hash == job_hash:
                return job
        raise RuntimeError(
            "No job with hash %s found. It seems the crontab is out of sync with your "
            'application. Run "flask crontab add" again to resolve this issue!'
            % job_hash
        )


def common_options(f):
    f = click.option(
        "--suppress",
        "verbose",
        flag_value=False,
        default=True,
        help="Do not show verbose outputs.",
    )(f)
    return with_appcontext(f)


@click.group(help="Manage the scheduled cron jobs.")
def crontab_cli():
    pass


@crontab_cli.command()
@common_options
def add(verbose):
    with _Crontab(verbose=verbose) as c:
        c.remove_jobs()
        c.add_jobs()


@crontab_cli.command()
@common_options
def remove(verbose):
    with _Crontab(verbose=verbose) as c:
        c.remove_jobs()


@crontab_cli.command()
@common_options
@click.argument("job_hash")
def run(verbose, job_hash):
    with _Crontab(verbose=verbose, readonly=True) as c:
        c.run_job(job_hash)


@crontab_cli.command()
@common_options
def show(verbose):
    with _Crontab(verbose=verbose, readonly=True) as c:
        c.show_jobs()


class Crontab:
    def __init__(self, app: Optional[Flask] = None) -> None:
        self.app = app
        self.jobs = []  # type: List[_CronJob]
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.config.setdefault("CRONTAB_EXECUTABLE", "/usr/bin/crontab")
        app.config.setdefault("CRONTAB_LOCK_JOBS", False)
        app.extensions["crontab"] = self
        self.app = app

    def job(
        self,
        minute: str = "*",
        hour: str = "*",
        day: str = "*",
        month: str = "*",
        day_of_week: str = "*",
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """
        Register a function as crontab job.
        """

        def wrapper(func: Callable) -> Callable:
            job = _CronJob(
                func,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                args=args,
                kwargs=kwargs or {},
            )
            self.jobs.append(job)
            return func

        return wrapper
