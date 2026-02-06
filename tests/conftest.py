import pytest


@pytest.fixture
def sample_config():
    return {
        "image_service_base_url": "https://example.org/iiif/3/",
        "default_language": "en",
        "image_url_regex": "(https?://example\\.org/iiif/3/[^/]+).*",
        "image_url_replacement": "\\1/info.json",
        "manifest_dir": "manifests",
        "error_log_file": "log/error.log",
        "occurrence_csv": "data/occurrence.txt",
        "media_image_csv": "data/media_image.txt",
        "media_iiif_csv": "data/media_iiif.txt",
        "separator": "\t",
        "metadata_keys": ["catalogNumber", "scientificName", "country"],
        "manifest": {
            "rights": "https://creativecommons.org/licenses/by/4.0/",
            "requiredStatement": {
                "label": {"en": ["Attribution"]},
                "value": {"en": ["Example Institution"]},
            },
        },
    }


@pytest.fixture
def sample_occurrence_data():
    return {
        "occurrenceID": "occ-1",
        "catalogNumber": "CN-1",
        "genus": "Homo",
        "specificEpithet": "sapiens",
        "country": "Sweden",
    }


@pytest.fixture
def sample_image_info():
    return {"id": "https://example.org/iiif/3/img1", "width": 1000, "height": 2000}
