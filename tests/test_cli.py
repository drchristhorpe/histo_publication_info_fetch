import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from histo_publication_info_fetch.cli import main
from histo_publication_info_fetch.core import PublicationRecord


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_record():
    return PublicationRecord(
        pdb_id="1ao7",
        title="Test Title",
        authors=["Author One"],
        release_date="2020-01-01",
        deposition_date="2019-12-01",
        experimental_method="X-ray diffraction",
    )


@patch("histo_publication_info_fetch.cli.PublicationFetcher")
def test_cli_basic(mock_fetcher_class, runner, mock_record):
    """Test basic CLI invocation."""
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_many.return_value = [mock_record]
    mock_fetcher_class.return_value = mock_fetcher

    result = runner.invoke(main, ["1ao7"])

    assert result.exit_code == 0
    assert "1AO7" in result.output
    assert "Test Title" in result.output


@patch("histo_publication_info_fetch.cli.PublicationFetcher")
def test_cli_multiple_codes(mock_fetcher_class, runner, mock_record):
    """Test CLI with multiple PDB codes."""
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_many.return_value = [mock_record, mock_record]
    mock_fetcher_class.return_value = mock_fetcher

    result = runner.invoke(main, ["1ao7", "1hla"])

    assert result.exit_code == 0
    mock_fetcher.fetch_many.assert_called_once()


@patch("histo_publication_info_fetch.cli.PublicationFetcher")
def test_cli_output_json(mock_fetcher_class, runner, tmp_path, mock_record):
    """Test CLI with JSON output to file."""
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_many.return_value = [mock_record]
    mock_fetcher_class.return_value = mock_fetcher

    output_file = tmp_path / "output.json"

    result = runner.invoke(main, [
        "--output", str(output_file),
        "--format", "json",
        "1ao7"
    ])

    assert result.exit_code == 0
    mock_fetcher.write_json.assert_called_once()


@patch("histo_publication_info_fetch.cli.PublicationFetcher")
def test_cli_output_csv(mock_fetcher_class, runner, tmp_path, mock_record):
    """Test CLI with CSV output to file."""
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_many.return_value = [mock_record]
    mock_fetcher_class.return_value = mock_fetcher

    output_file = tmp_path / "output.csv"

    result = runner.invoke(main, [
        "--output", str(output_file),
        "--format", "csv",
        "1ao7"
    ])

    assert result.exit_code == 0
    mock_fetcher.write_csv.assert_called_once()


@patch("histo_publication_info_fetch.cli.PublicationFetcher")
def test_cli_refresh_flag(mock_fetcher_class, runner, mock_record):
    """Test CLI with --refresh flag."""
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_many.return_value = [mock_record]
    mock_fetcher_class.return_value = mock_fetcher

    result = runner.invoke(main, ["--refresh", "1ao7"])

    assert result.exit_code == 0
    # Check that PublicationFetcher was called with refresh=True
    mock_fetcher_class.assert_called_once()
    call_kwargs = mock_fetcher_class.call_args[1]
    assert call_kwargs.get("refresh") is True


@patch("histo_publication_info_fetch.cli.PublicationFetcher")
def test_cli_comma_separated_codes(mock_fetcher_class, runner, mock_record):
    """Test CLI with comma-separated PDB codes."""
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_many.return_value = [mock_record, mock_record]
    mock_fetcher_class.return_value = mock_fetcher

    result = runner.invoke(main, ["1ao7,1hla"])

    assert result.exit_code == 0
    # Should parse comma-separated codes
    called_codes = mock_fetcher.fetch_many.call_args[0][0]
    assert len(called_codes) >= 2


def test_cli_no_codes(runner):
    """Test CLI with no PDB codes."""
    result = runner.invoke(main, [])

    assert result.exit_code != 0
