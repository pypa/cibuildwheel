import os
from unittest import mock

from cibuildwheel.ci import CIProvider
from cibuildwheel.logger import Logger


def test_logger_fold_pattern_for_bitbucket_pipelines():
    """Test that the logger uses the correct fold pattern for Bitbucket Pipelines."""
    with mock.patch("cibuildwheel.logger.detect_ci_provider", return_value=CIProvider.bitbucket_pipelines):
        # Set up a logger that thinks it's running on Bitbucket Pipelines
        logger = Logger()
        
        # Check that it has the expected fold mode
        assert logger.fold_mode == "bitbucket"
        
        # Check that colors are enabled
        assert logger.colors_enabled is True


def test_logger_fold_mode_default():
    """Test that the logger defaults to disabled fold mode for unknown CI providers."""
    with mock.patch("cibuildwheel.logger.detect_ci_provider", return_value=CIProvider.other):
        logger = Logger()
        assert logger.fold_mode == "disabled"