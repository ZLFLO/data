"""Test folder structure in the repo public folder matches repository.yaml."""

import os
from pathlib import Path

import pytest

from zlflodata.get_paths import (
    get_abs_data_path,
    get_data_dir,
    get_repository_data,
)


def test_repo_folder_structure():
    """Test that all folders in muckup data folder are present in repository.yaml."""
    rep = get_repository_data()
    assert rep is not None, "Unable to load repository.yaml is None"

    # Test if all paths listed in repository.yaml are present in the public folder
    for name, dataset in rep.items():
        for version in dataset:
            if version["paths"]["local"] != f"{name}/v{version['version_zlflo']}":
                pytest.fail(
                    "Path in repository.yaml does not match the expected path:"
                    f" {version['paths']['local']}"
                )

            if (
                version["paths"]["repo"]
                != f"public/{name}/v{version['version_zlflo']}"
            ):
                pytest.fail(
                    "Path in repository.yaml does not match the expected path:"
                    f" {version['paths']['public']}"
                )

            path = str(
                get_abs_data_path(
                    name=name,
                    version=version["version_zlflo"],
                    location="repo",
                )
            )
            if not path.endswith(version["paths"]["repo"]):
                pytest.fail(
                    "Path in repository.yaml does not match the expected path:"
                    f" {version['paths']['repo']}"
                )

            assert os.path.exists(path), f"Path {path} does not exist"
            assert os.listdir(path), f"Path {path} is empty"

    # Test if all folders in the public folder are listed in repository.yaml
    data_repo_path = Path(get_data_dir()) / "public"

    skip_folders = {
        ".gitkeep",
        "README.md",
        ".DS_Store",
        "Thumbs.db",
        "license_by-nc-sa-40.txt",
    }

    for dataset_name in os.listdir(data_repo_path):
        if dataset_name in skip_folders:
            continue

        if dataset_name not in rep:
            pytest.fail(
                f"Folder {dataset_name} in public is not listed in repository.yaml"
            )

        sort_versions = sorted(
            [
                i
                for i in os.listdir(data_repo_path / dataset_name)
                if i not in skip_folders
            ],
            reverse=True,
        )
        rep_version = [f"v{version['version_zlflo']}" for version in rep[dataset_name]]

        if sort_versions != rep_version:
            pytest.fail(
                f"Versions of {dataset_name} in public folder do not match versions "
                "in repository.yaml"
            )
