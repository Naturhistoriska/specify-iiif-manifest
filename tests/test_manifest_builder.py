from src.manifest_builder import (
    _get_scientific_name,
    _create_metadata,
    create_manifest,
    get_id,
)


def test_get_scientific_name(sample_occurrence_data):
    name = _get_scientific_name(sample_occurrence_data)
    assert name == "Homo sapiens"


def test_get_scientific_name_empty():
    assert _get_scientific_name({}) == ""


def test_get_id():
    assert get_id({"id": "foo"}) == "foo"
    assert get_id({"@id": "bar"}) == "bar"
    assert get_id({"id": "foo", "@id": "bar"}) == "foo"
    assert get_id({}) is None


def test_create_metadata(sample_occurrence_data, sample_config):
    full_name = "Homo sapiens"
    metadata = _create_metadata(sample_occurrence_data, full_name, sample_config)

    # Check if ScientificName is present
    sci_name_meta = next(
        item for item in metadata if item["label"]["en"] == ["ScientificName"]
    )
    assert sci_name_meta["value"]["en"] == ["Homo sapiens"]

    # Check if other keys are present
    country_meta = next(item for item in metadata if item["label"]["en"] == ["country"])
    assert country_meta["value"]["en"] == ["Sweden"]


def test_create_manifest(sample_occurrence_data, sample_config, sample_image_info):
    manifest = create_manifest(
        manifest_id="https://example.org/manifest/1",
        catalog_number="CN-1",
        images_info=[sample_image_info],
        occurrence_data=sample_occurrence_data,
        config=sample_config,
    )

    assert manifest.id == "https://example.org/manifest/1"
    assert manifest.label["en"] == ["CN-1 - Homo sapiens"]
    assert len(manifest.items) == 1
    assert manifest.items[0].width == 1000
    assert manifest.items[0].height == 2000
