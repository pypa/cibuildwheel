import os
from unittest import mock

import pytest

from cibuildwheel.ci import CIProvider, detect_ci_provider


def test_detect_ci_provider_none():
    """Test that None is returned when no CI environment variables are set."""
    with mock.patch.dict(os.environ, {}, clear=True):
        assert detect_ci_provider() is None


def test_detect_ci_provider_generic():
    """Test that generic CI is detected when only CI=true is set."""
    with mock.patch.dict(os.environ, {"CI": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.other


def test_detect_ci_provider_travis():
    """Test that Travis CI is detected."""
    with mock.patch.dict(os.environ, {"TRAVIS": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.travis_ci


def test_detect_ci_provider_appveyor():
    """Test that AppVeyor is detected."""
    with mock.patch.dict(os.environ, {"APPVEYOR": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.appveyor


def test_detect_ci_provider_circle_ci():
    """Test that Circle CI is detected."""
    with mock.patch.dict(os.environ, {"CIRCLECI": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.circle_ci


def test_detect_ci_provider_azure_pipelines():
    """Test that Azure Pipelines is detected."""
    with mock.patch.dict(os.environ, {"AZURE_HTTP_USER_AGENT": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.azure_pipelines


def test_detect_ci_provider_github_actions():
    """Test that GitHub Actions is detected."""
    with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.github_actions


def test_detect_ci_provider_gitlab():
    """Test that GitLab CI is detected."""
    with mock.patch.dict(os.environ, {"GITLAB_CI": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.gitlab


def test_detect_ci_provider_cirrus_ci():
    """Test that Cirrus CI is detected."""
    with mock.patch.dict(os.environ, {"CIRRUS_CI": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.cirrus_ci


def test_detect_ci_provider_bitbucket_pipelines():
    """Test that Bitbucket Pipelines is detected."""
    with mock.patch.dict(os.environ, {"BITBUCKET_PIPELINE_UUID": "true"}, clear=True):
        assert detect_ci_provider() == CIProvider.bitbucket_pipelines


def test_detect_ci_provider_order():
    """Test that CI providers are detected in the correct order."""
    # Setting multiple CI environment variables
    with mock.patch.dict(
        os.environ,
        {
            "TRAVIS": "true",
            "APPVEYOR": "true",
            "CIRCLECI": "true",
            "AZURE_HTTP_USER_AGENT": "true",
            "GITHUB_ACTIONS": "true",
            "GITLAB_CI": "true",
            "CIRRUS_CI": "true",
            "BITBUCKET_PIPELINE_UUID": "true",
            "CI": "true",
        },
        clear=True,
    ):
        # Travis CI should be detected first based on the order in detect_ci_provider
        assert detect_ci_provider() == CIProvider.travis_ci