"""Functions to get paths to data sets."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

import yaml
from yaml.loader import SafeLoader
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def get_abs_data_path(name="", version="latest", location="get_from_env", local_parent_folder=""):
    """Return the absolute path to the data directory from data/repository.yaml.

    Sets the location of the data set. Can be "repo" or "local" or "get_from_env".
    - "get_from_env" is the default. The function will return the look for the value of the
        environment variable ZLFLODATA_LOCATION. If not found, it will default to "repo", if found
        it's value will be used as the `local_parent_folder` of the local data set.
    - "repo" means the repository contains the data set. It is packaged with the zlflodata package.
    - "local" is the path to the local data set. If only local is defined the data is not 
       shipped with the zlflodata package. Please reach out to
       the data set owner listed in repository.yaml to obtain the data set.
       If local, defining parent folder is required.
    - "zlflo_server" is the data set on the zlflo server. Format is correct
        and the data is unaltered. Used for working on the zlflo.com server.

    Parameters
    ----------
    name : str
        Name of the data set.
    version : str
        Version of the data set. Can be "latest" or a specific version number. Version numbers
        must be a valid semantic version number: 1.0.0, 1.0.1, 1.1.0, etc.
        Corresponds to the verion_zlflo entry in repository.yaml.
    location : str, optional
        Location of the data set. Can be "repo", "local" or "get_from_env".
        - "get_from_env" is the default. The function will return the look for the value of the
            environment variable ZLFLODATA_LOCATION for the data path. Repo will be used if the
            variable is not found.
        - "repo" is the repository of the data set. It is packaged with the zlflodata package.
        - "local" is the local data set. This data is not shipped  with the 
           zlflodata package. Please reach out to
           the data set owner listed in repository.yaml to obtain the data set.
           If local, defining parent folder is required.
    local_parent_folder : str, optional
        Parent folder of the local data set. Required if location is "local".
        Must be left empty if location is "get_from_env".

    Returns
    -------
    str
        Absolute path to the data set.
    """
    if local_parent_folder and location != "local":
        msg = "local_parent_folder must be empty if location is 'get_from_env'"
        raise ValueError(msg)

    if location == "get_from_env":
        local_parent_folder = os.environ.get("ZLFLODATA_LOCATION", "")

    if location not in {
        "get_from_env",  # "get_from_env" is the default
        "repo",
        "local",
    }:
        msg = "Location must be 'get_from_env', 'repo', or 'local'"
        raise ValueError(msg)
    if not (is_valid_semver(version) or version == "latest"):
        msg = "Version must be a valid semantic version number or 'latest'"
        raise ValueError(msg)

    rep = get_repository_data()

    if version == "latest":
        version_index = 0

    else:
        versions_ordered = [item["version_zlflo"] for item in rep[name]]
        if version not in versions_ordered:
            msg = "Version not found in repository.yaml"
            raise ValueError(msg)

        version_index = versions_ordered.index(version)

    if location == "repo" or (location == "get_from_env" and not local_parent_folder):
        rel_path = rep[name][version_index]["paths"]["repo"]
        abs_path = os.path.join(get_data_dir(), rel_path)

    elif location == "local" or (location == "get_from_env" and local_parent_folder):
        rel_path = rep[name][version_index]["paths"]["local"]
        abs_path = os.path.join(local_parent_folder, rel_path)

    logger.info("Data path prompted is: %s", abs_path)

    if not os.path.exists(abs_path):
        logger.warning("Path does not exist: %s", abs_path)

    return Path(abs_path)


def get_data_dir():
    """Return the path to the data directory."""
    return os.path.join(os.path.dirname(__file__), "data")


def get_latest_data_paths() -> list[Path]:
    """
    Get paths to all latest data versions in the repository.

    Returns
    -------
    List[Path]
        List of Path objects representing all found directories

    Examples
    --------
    >>> folders = get_latest_data_paths()
    >>> print(folders[0])
    ./data/subfolder1/v1.2.3
    """
    dataset_names = sorted(get_repository_data().keys())
    dataset_paths = [get_abs_data_path(name, version="latest", location="repo") for name in dataset_names]
    return [Path(path) for path in dataset_paths]


def get_repository_path():
    """Return the path to the repository.yaml file from data/repository.yaml."""
    # from importlib.resources import files
    data_dir = get_data_dir()
    return os.path.join(data_dir, "repository.yaml")


def get_repository_data():
    """Return the data from the repository.yaml file."""
    with open(get_repository_path(), encoding="utf-8") as file:
        return yaml.load(file, Loader=SafeLoader)["data"]


def is_valid_semver(version):
    """Return True if the version is a valid semantic version number."""
    pattern = re.compile(r"^\d+\.\d+\.\d+$")
    return pattern.match(version) is not None


def create_new_dataset(name, version="1.0.0", location="repo", makedirs=True, **kwargs):  # noqa: FBT002
    """Create a new data set in the repository.yaml file."""
    rep = get_repository_data()

    if name in rep:
        msg = "Data set already exists in repository.yaml"
        raise ValueError(msg)

    if location not in {"repo", "local"}:
        msg = "Location must be 'repo' or 'local'"
        raise ValueError(msg)

    if not is_valid_semver(version):
        msg = "Version must be a valid semantic version number"
        raise ValueError(msg)

    new_entry = {
        "version_zlflo": version,
        "owner": None,
        "publication_date": datetime.now(tz=ZoneInfo("Europe/Amsterdam")).strftime("%Y-%m-%d"),
        "version_owner": version,
        "description_short": None,
        "description_long": None,
        "contact": None,
        "timezone": "Europe/Amsterdam",
        "extent": "",
        "paths": {
            "local": f"{name}/v{version}",
            "zlflo_server": f"/data/{name}/v{version}",
            "repo": f"public/{name}/v{version}",
        },
        "changelog": {"previous_version": "0.0.0", "log": "Initial version"},
    }
    new_entry.update(kwargs)
    rep[name] = [new_entry]

    # create public directory for new dataset
    if makedirs and location == "public":
        datadir = Path(get_data_dir())
        (datadir / "public" / name / f"v{version}").mkdir(parents=True, exist_ok=True)

    # write repository.yaml with added dataset
    with open(get_repository_path(), "w", encoding="utf-8") as file:
        rep_yml = {
            "title": "ZLFLO data repository",
            "description": "Repository containing the public data for ZLFLO.",
            "data": rep,
        }
        yaml.dump(rep_yml, file, allow_unicode=True, sort_keys=False)
