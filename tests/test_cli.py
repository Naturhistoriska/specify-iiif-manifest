import pytest
import yaml
import json
from unittest.mock import patch, MagicMock
from src.cli import main


@pytest.fixture
def mock_data_files(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create occurrences
    occ_path = data_dir / "occurrence.txt"
    occ_content = "occurrenceID\tcatalogNumber\tgenus\tspecificEpithet\tcountry\nocc-1\tCN-1\tHomo\tsapiens\tSweden"
    occ_path.write_text(occ_content)

    # Create media image
    mi_path = data_dir / "media_image.txt"
    mi_content = "occurrenceID\taccessURI\tidentifier\nocc-1\thttps://example.org/iiif/3/img1/info.json\tid-1"
    mi_path.write_text(mi_content)

    # Create media IIIF
    me_path = data_dir / "media_iiif.txt"
    me_content = "occurrenceID\taccessURI\tidentifier\nocc-1\thttps://example.org/iiif/3/img1/manifest.json\tid-1"
    me_path.write_text(me_content)

    return {
        "occurrence": str(occ_path),
        "media_image": str(mi_path),
        "media_iiif": str(me_path),
    }


@pytest.fixture
def integration_config(tmp_path, mock_data_files):
    manifest_dir = tmp_path / "manifests"
    log_file = tmp_path / "log" / "error.log"
    log_file.parent.mkdir()

    config = {
        "image_service_base_url": "https://example.org/iiif/3/",
        "default_language": "en",
        "image_url_regex": "(https?://example\\.org/iiif/3/[^/]+).*",
        "image_url_replacement": "\\1/info.json",
        "manifest_dir": str(manifest_dir),
        "error_log_file": str(log_file),
        "occurrence_csv": mock_data_files["occurrence"],
        "media_image_csv": mock_data_files["media_image"],
        "media_iiif_csv": mock_data_files["media_iiif"],
        "separator": "\t",
        "metadata_keys": ["catalogNumber", "scientificName"],
        "manifest": {
            "rights": "https://creativecommons.org/publicdomain/zero/1.0/",
            "requiredStatement": {
                "label": {"en": ["Attribution"]},
                "value": {"en": ["Test"]},
            },
        },
    }

    config_path = tmp_path / "config.yml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return str(config_path), manifest_dir


@patch("src.manifest_builder.requests.get")
def test_cli_main_success(mock_get, integration_config):
    config_path, manifest_dir = integration_config

    # Mock image info response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "https://example.org/iiif/3/img1",
        "width": 100,
        "height": 200,
    }
    mock_get.return_value = mock_response

    # Run CLI
    main(config_path, mode="full")

    # Verify results
    assert manifest_dir.exists()
    manifest_files = list(manifest_dir.glob("*.json"))
    assert len(manifest_files) == 1

    with open(manifest_files[0], "r") as f:
        manifest_data = json.load(f)
        assert manifest_data["id"] == "https://example.org/iiif/3/img1/manifest.json"
        assert manifest_data["label"]["en"] == ["CN-1 - Homo sapiens"]
