# flask-crontab

> Simple Flask scheduled tasks without extra daemons

[![PyPI](https://img.shields.io/pypi/v/flask-crontab)](https://pypi.org/project/flask-crontab) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/flask-crontab)](https://pypi.org/project/flask-crontab) [![Github Action](https://github.com/frostming/flask-crontab/workflows/Continuous%20Integration/badge.svg)](https://github.com/frostming/flask-crontab/actions?query=workflow%3A%22Continuous+Integration%22) ![Supported Platforms](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey)

This project is strongly inspired by [django-crontab](https://github.com/kraiz/django-crontab), and only works on Python 3.5+.
Due to the coming EOL of Python 2 on 2020/01/01, there is no plan for Python 2 support.

## Quick Start

Install via `pip`:

```bash
$ pip install flask-crontab
```

Instantiate the extension in your `app.py` after the creation of Flask app:

```python
from flask import Flask
from flask_crontab import Crontab

app = Flask(__name__)
crontab = Crontab(app)
```

If you are using App Factory pattern, you can also register the extension later:

```python
crontab = Crontab()

def create_app():
    ...
    crontab.init_app(app)
```

Now create a scheduled job:

```python
@crontab.job(minute="0", hour="6")
def my_scheduled_job():
    do_something()
```

An app context is automatically activated for every job run, so that you can access objects that are attached to app context.
Then add the job to crontab:

```bash
$ flask crontab add
```

That's it! If you type in `crontab -l` in your shell, you can see some new lines created by `flask-crontab`.

Show jobs managed by current app:

```bash
$ flask crontab show
```

Purge all jobs managed by current app:

```bash
$ flask crontab remove
```

Run a specific job given by hash:

```bash
$ flask crontab run <job_hash>
```

See supported options via `--help` for every commands.

## Decorator API

```python
def job(
    minute: str = "*",
    hour: str = "*",
    day: str = "*",
    month: str = "*",
    day_of_week: str = "*",
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
) -> Callable:
```

The decorator accepts five arguments `minute`, `hour`, `day`, `month`, `day_of_month`, which are the same as crontab 5-parts time format. Any part that is not given defaults to `*`.
Besides, `job` decorator accepts `args` and `kwargs` which will be passed to the decorated function as positional arguments and keywords arguments, respectively.

## Configuration

| Config item        | Description                    | Default value      |
| ------------------ | ------------------------------ | ------------------ |
| CRONTAB_EXECUTABLE | The absolute path of `crontab` | `/usr/bin/crontab` |
| CRONTAB_LOCK_JOBS  | Whether lock jobs when running | `False`            |

## License

This project is publised under [MIT](LICENSE) license.
