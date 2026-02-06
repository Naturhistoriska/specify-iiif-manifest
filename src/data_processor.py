import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any


def validate_dataframe(
    df: pd.DataFrame, required_columns: List[str], df_name: str
) -> bool:
    """
    Validates if all required columns are present in the DataFrame.
    Logs an error and returns False if any column is missing.
    """
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logging.error(
            f"Validation failed for {df_name}: Missing required columns: {', '.join(missing_columns)}"
        )
        return False
    logging.debug(
        f"Validation successful for {df_name}. All required columns are present."
    )
    return True


def _load_csv_with_validation(
    filepath: Path,
    separator: str,
    required_columns: List[str],
    df_name: str,
    dtype: Optional[Dict[str, Any]] = None,
) -> Optional[pd.DataFrame]:
    """Loads a CSV file and validates required columns."""
    logging.info(f"Attempting to load CSV file: {filepath.name} for {df_name}")
    try:
        df = pd.read_csv(filepath, sep=separator, dtype=dtype, low_memory=False)
        logging.info(
            f"Successfully loaded {filepath.name}. Number of rows in {df_name} = {len(df)}"
        )
        if not validate_dataframe(df, required_columns, df_name):
            logging.error(f"Validation failed for {df_name} from {filepath.name}.")
            return None
        return df
    except FileNotFoundError:
        logging.error(
            f"Error loading data file: {filepath.name} not found at {filepath}."
        )
        return None
    except Exception as e:
        logging.error(
            f"An unexpected error occurred while loading {filepath.name}: {e}"
        )
        return None


def _merge_and_prepare_dataframes(
    occurrence_df: pd.DataFrame,
    media_image_df: pd.DataFrame,
    media_iiif_df: pd.DataFrame,
    config: Dict[str, Any],
) -> pd.DataFrame:
    """
    Performs regex replacement, checks for missing identifiers,
    groups image URIs, and merges the dataframes.
    """
    logging.info("Starting dataframe merging and preparation steps.")
    media_image_df["iiif_image_info"] = media_image_df["accessURI"].str.replace(
        config["image_url_regex"], config["image_url_replacement"], regex=True
    )
    logging.debug("Applied regex replacement for iiif_image_info.")

    logging.info(
        f"Number of unique rows in media image df {(media_image_df['occurrenceID'].nunique())}"
    )

    missing_identifiers = set(media_iiif_df["identifier"]) - set(
        media_image_df["identifier"]
    )
    if missing_identifiers:
        logging.warning(
            f"WARNING: {len(missing_identifiers)} identifiers in media_iiif_df are missing from media_image_df: {missing_identifiers}"
        )
    else:
        logging.debug(
            "No missing identifiers found between media_iiif_df and media_image_df."
        )

    media_image_uris = (
        media_image_df.groupby("occurrenceID")["iiif_image_info"]
        .apply(list)
        .reset_index()
    )
    media_image_uris = media_image_uris.rename(
        columns={"iiif_image_info": "image_access_uris"}
    )
    logging.info(
        f"Grouped media image URIs by occurrenceID. Length: {len(media_image_uris)}"
    )

    merged_df = pd.merge(
        media_iiif_df, media_image_uris, on="occurrenceID", how="inner"
    )
    logging.info(
        f"Merged media_iiif_df and media_image_uris. Resulting length: {len(merged_df)}"
    )

    merged_df = pd.merge(
        merged_df,
        occurrence_df,
        left_on="occurrenceID",
        right_on="occurrenceID",
        how="inner",
    )
    logging.info(
        f"Merged with occurrence_df. Final merged DataFrame length: {len(merged_df)}"
    )

    logging.info("Dataframe merging and preparation steps completed.")
    return merged_df


def load_and_prepare_data(config: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """Loads, validates, and prepares the data from CSV files."""
    logging.info("Starting to load and validate CSV files.")
    try:
        occurrence_df = _load_csv_with_validation(
            Path(config["occurrence_csv"]),
            config["separator"],
            ["occurrenceID", "catalogNumber"],
            "occurrence_csv",
            dtype={"catalogNumber": "string"},
        )
        if occurrence_df is None:
            logging.error("Failed to load or validate occurrence CSV.")
            return None
        logging.debug("Occurrence CSV loaded and validated.")

        media_image_df = _load_csv_with_validation(
            Path(config["media_image_csv"]),
            config["separator"],
            [
                "occurrenceID",
                "accessURI",
                "identifier",
            ],  # Added "identifier" for validation
            "media_image_csv",
        )
        if media_image_df is None:
            logging.error("Failed to load or validate media image CSV.")
            return None
        logging.debug("Media image CSV loaded and validated.")

        media_iiif_df = _load_csv_with_validation(
            Path(config["media_iiif_csv"]),
            config["separator"],
            [
                "occurrenceID",
                "accessURI",
                "identifier",
            ],  # Added "identifier" for validation
            "media_iiif_csv",
        )
        if media_iiif_df is None:
            logging.error("Failed to load or validate media IIIF CSV.")
            return None
        logging.debug("Media IIIF CSV loaded and validated.")

    except FileNotFoundError as e:
        logging.error(f"A data file was not found during initial loading: {e}")
        return None
    except Exception as e:
        logging.critical(
            f"An unhandled error occurred during CSV loading: {e}", exc_info=True
        )
        return None

    logging.info(
        "All required CSV files loaded and validated. Proceeding to merge and prepare dataframes."
    )
    return _merge_and_prepare_dataframes(
        occurrence_df, media_image_df, media_iiif_df, config
    )
