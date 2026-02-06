import logging
import yaml
import argparse
import pandas as pd  # Re-adding pandas for DataFrame type hint
from pathlib import Path
import json
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.data_processor import load_and_prepare_data
from src.manifest_builder import create_manifest, get_image_info


def _setup_environment(config_path: Path) -> Dict[str, Any]:
    """
    Loads the configuration, sets up logging, and creates necessary directories.

    Args:
        config_path (Path): Path to the configuration file.

    Returns:
        dict: The loaded configuration dictionary.
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    manifest_dir = Path(config["manifest_dir"])
    error_log_file = Path(config["error_log_file"])

    # Ensure the log directory exists before setting up file handler
    log_dir = error_log_file.parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # --- Start of Logging Fix ---
    # Get the root logger
    root_logger = logging.getLogger()
    # Clear any existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Set the logging level
    root_logger.setLevel(logging.INFO)

    # Create a formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Create a file handler
    file_handler = logging.FileHandler(str(error_log_file), mode="w")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Create a stream handler (for console output)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    # --- End of Logging Fix ---

    manifest_dir.mkdir(parents=True, exist_ok=True)

    logging.info(f"Configuration loaded from {config_path}")
    logging.info(f"Manifests will be saved to: {manifest_dir}")
    logging.info(f"Log messages will be written to: {error_log_file}")

    return config


def _filter_existing_manifests(data: pd.DataFrame, manifest_dir: Path) -> pd.DataFrame:
    """
    Filters out data for manifests that already exist in the manifest directory.
    """
    existing_manifests = [f for f in manifest_dir.iterdir() if f.suffix == ".json"]
    existing_manifest_ids = [f.stem for f in existing_manifests]

    original_rows = len(data)
    data = data[~data["catalogNumber"].isin(existing_manifest_ids)]
    new_rows = len(data)
    logging.info(
        f"Found {len(existing_manifests)} existing manifests. Processing {new_rows} new manifests out of {original_rows} total."
    )
    return data


def generate_and_save_manifests(
    data: pd.DataFrame, config: Dict[str, Any], mode: str
) -> None:
    """
    Orchestrates the conversion of specimen data and image URLs into IIIF Manifests.

    This function groups data by occurrenceID, fetches image metadata (dimensions)
    in parallel, and saves the resulting JSON manifests to the configured directory.

    Args:
        data (pd.DataFrame): Processed specimen data.
        config (Dict[str, Any]): Application configuration.
        mode (str): Execution mode ('full' or 'partial').
    """
    manifest_dir = Path(config["manifest_dir"])

    if mode == "partial":
        data = _filter_existing_manifests(data, manifest_dir)
        if data.empty:
            logging.info("No new manifests to process after filtering existing ones.")
            return

    grouped = data.groupby("occurrenceID")
    logging.info(
        f"Starting to generate manifests for {len(grouped)} unique occurrences."
    )
    generated_count = 0
    skipped_count = 0

    for occurrence_id, group in grouped:
        try:
            manifest_id: str = group["accessURI"].iloc[0]
            catalog_number: str = group["catalogNumber"].iloc[0]
            images_info: List[Dict[str, Any]] = []
            image_urls: List[str] = group["image_access_uris"].iloc[0]
            logging.debug(
                f"Processing occurrenceID: {occurrence_id}, Catalog Number: {catalog_number}"
            )

            # --- Start Parallel Fetching ---
            with ThreadPoolExecutor(max_workers=min(10, len(image_urls))) as executor:
                future_to_url = {
                    executor.submit(get_image_info, url): url for url in image_urls
                }
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        image_info = future.result()
                        if (
                            image_info
                            and "width" in image_info
                            and "height" in image_info
                        ):
                            images_info.append(image_info)
                        else:
                            logging.warning(
                                f"Invalid or incomplete image info for {url} (OccurrenceID: {occurrence_id}). Skipping this image."
                            )
                    except Exception as exc:
                        logging.error(
                            f"Image info fetch generated an exception for {url}: {exc}"
                        )
            # --- End Parallel Fetching ---

            if images_info:
                occurrence_data: Dict[str, Any] = group.iloc[0].to_dict()
                manifest = create_manifest(
                    manifest_id, catalog_number, images_info, occurrence_data, config
                )
                manifest_filename: str = f"{catalog_number}.json"
                manifest_filepath: Path = manifest_dir / manifest_filename
                with open(manifest_filepath, "w") as f:
                    raw_json_string = manifest.model_dump_json()
                    json_data = json.loads(raw_json_string)
                    json.dump(json_data, f, indent=2)
                logging.info(
                    f"Generated manifest for {catalog_number} at {manifest_filepath}"
                )
                generated_count += 1
            else:
                logging.error(
                    f"No valid images found for {catalog_number} (OccurrenceID: {occurrence_id}). Skipping manifest generation for this occurrence."
                )
                skipped_count += 1
        except Exception:
            logging.exception(
                f"Failed to generate manifest for occurrence ID {occurrence_id}"
            )
            skipped_count += 1
    logging.info(
        f"Finished manifest generation. Total occurrences processed: {len(grouped)}, Generated: {generated_count}, Skipped: {skipped_count}."
    )


def main(config_path: str, mode: str) -> None:
    """
    The main entry point for the IIIF manifest generation pipeline.

    Args:
        config_path (str): Path to the YAML configuration file.
        mode (str): 'full' to process all records, 'partial' to skip existing manifests.
    """
    logging.info("IIIF manifest generation process started.")
    config = _setup_environment(Path(config_path))

    logging.info("Beginning data loading and preparation.")
    data: Optional[pd.DataFrame] = load_and_prepare_data(config)
    if data is not None:
        logging.info("Data loading and preparation completed successfully.")
        logging.info(f"Total objects identified for processing: {len(data)}")
        logging.info("Initiating manifest generation phase.")
        generate_and_save_manifests(data, config, mode)
        logging.info("Manifest generation phase concluded.")
    else:
        logging.critical(
            "Fatal: Data loading and preparation failed. Exiting application."
        )  # Changed to critical
    logging.info("IIIF manifest generation process finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate IIIF manifests from Specify data."
    )
    parser.add_argument(
        "config", help="Path to the configuration file (e.g., config-entomology.yml)"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "partial"],
        default="full",
        help="Generation mode: 'full' to regenerate all, 'partial' to skip existing.",
    )
    args = parser.parse_args()
    main(args.config, args.mode)
