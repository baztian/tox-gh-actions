import os
import sys
from typing import Dict, Iterable, List

import pluggy
from tox.config import Config, _split_env as split_env
from tox.reporter import verbosity1, verbosity2


hookimpl = pluggy.HookimplMarker("tox")


@hookimpl
def tox_configure(config):
    # type: (Config) -> None
    verbosity2("original envconfigs: {}".format(list(config.envconfigs.keys())))
    verbosity2("original envlist: {}".format(config.envlist))
    verbosity2("original envlist_default: {}".format(config.envlist_default))

    version = get_python_version()
    verbosity2("Python version: {}".format(version))

    gh_actions_config = parse_config(config._cfg.sections.get("gh-actions", {}))
    verbosity2("tox-gh-actions config: {}".format(gh_actions_config))

    envlist = get_envlist(config.envlist, gh_actions_config, version)
    verbosity2("new envlist: {}".format(envlist))

    if "GITHUB_ACTION" not in os.environ:
        verbosity1("tox is not running in GitHub Actions")
        verbosity1("tox-gh-actions won't override envlist")
        return
    config.envlist_default = config.envlist = envlist


def parse_config(config):
    # type: (Dict[str, str]) -> Dict[str, Dict[str, List[str]]]
    """Parse gh-actions section in tox.ini"""
    config_python = parse_dict(config.get("python", ""))
    # Example of split_env:
    # "py{27,38}" => ["py27", "py38"]
    return {
        "python": {k: split_env(v) for k, v in config_python.items()}
    }


def get_envlist(envlist, gh_actions_config, version):
    # type: (Iterable[str], Dict[str, Dict[str, List[str]]], str) -> List[str]
    """Get envlist using config"""
    factors = gh_actions_config["python"].get(version, [])
    return get_envlist_from_factors(envlist, factors)


def get_envlist_from_factors(envlist, factors):
    # type: (Iterable[str], Iterable[str]) -> List[str]
    """Filter envlist using factors"""
    result = []
    for env in envlist:
        for factor in factors:
            env_facts = env.split("-")
            if all(f in env_facts for f in factor.split("-")):
                result.append(env)
                break
    return result


def get_python_version():
    # type: () -> str
    """Get Python version running in string (e.g,. 3.8)"""
    return '.'.join([str(i) for i in sys.version_info[:2]])


# The following function was copied from
# https://github.com/tox-dev/tox-travis/blob/0.12/src/tox_travis/utils.py#L11-L32
# which is licensed under MIT LICENSE
# https://github.com/tox-dev/tox-travis/blob/0.12/LICENSE

def parse_dict(value):
    # type: (str) -> Dict[str, str]
    """Parse a dict value from the tox config.
    .. code-block: ini
        [travis]
        python =
            2.7: py27, docs
            3.5: py{35,36}
    With this config, the value of ``python`` would be parsed
    by this function, and would return::
        {
            '2.7': 'py27, docs',
            '3.5': 'py{35,36}',
        }
    """
    lines = [line.strip() for line in value.strip().splitlines()]
    pairs = [line.split(':', 1) for line in lines if line]
    return dict((k.strip(), v.strip()) for k, v in pairs)
