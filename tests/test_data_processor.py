import pandas as pd
from src.data_processor import validate_dataframe, _merge_and_prepare_dataframes


def test_validate_dataframe():
    df = pd.DataFrame({"col1": [1], "col2": [2]})
    assert validate_dataframe(df, ["col1"], "test_df") is True
    assert validate_dataframe(df, ["col3"], "test_df") is False


def test_merge_and_prepare_dataframes(sample_config):
    occ_df = pd.DataFrame({"occurrenceID": ["occ-1"], "catalogNumber": ["CN-1"]})
    media_image_df = pd.DataFrame(
        {
            "occurrenceID": ["occ-1"],
            "accessURI": ["https://example.org/iiif/3/img1/info.json"],
            "identifier": ["id-1"],
        }
    )
    media_iiif_df = pd.DataFrame(
        {
            "occurrenceID": ["occ-1"],
            "accessURI": ["https://example.org/iiif/3/img1/manifest.json"],
            "identifier": ["id-1"],
        }
    )

    # Update config for the test regex
    sample_config["image_url_regex"] = "(https?://example\\.org/iiif/3/[^/]+).*"
    sample_config["image_url_replacement"] = "\\1/info.json"

    merged_df = _merge_and_prepare_dataframes(
        occ_df, media_image_df, media_iiif_df, sample_config
    )

    assert len(merged_df) == 1
    assert "image_access_uris" in merged_df.columns
    assert merged_df["image_access_uris"].iloc[0] == [
        "https://example.org/iiif/3/img1/info.json"
    ]
    assert merged_df["catalogNumber"].iloc[0] == "CN-1"
