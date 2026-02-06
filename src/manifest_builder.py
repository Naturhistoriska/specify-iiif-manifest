import logging
import requests
from typing import Dict, List, Optional, Any
from iiif_prezi3 import Manifest, Canvas, Annotation, AnnotationPage


def get_image_info(image_url: str) -> Optional[Dict[str, Any]]:
    """Fetches image information from the IIIF image service."""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        logging.debug(f"Successfully fetched image info from {image_url}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching image info from {image_url}: {e}")
        return None
    except requests.exceptions.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {image_url}: {e}")
        return None


def get_id(image_info: Dict[str, Any]) -> Optional[str]:
    """Gets the ID from image_info, checking for 'id' and '@id'."""
    return image_info.get("id") or image_info.get("@id")


def _get_scientific_name(occurrence_data: Dict[str, Any]) -> str:
    """Creates the full scientific name string."""
    scientific_name_keys = [
        "genus",
        "subgenus",
        "specificEpithet",
        "infraspecificEpithet",
        "scientificNameAuthorship",
    ]
    scientific_name_parts = []
    for key in scientific_name_keys:
        if key in occurrence_data and occurrence_data[key] is not None:
            val = str(occurrence_data[key]).strip()
            if val:
                scientific_name_parts.append(val)
    return " ".join(scientific_name_parts)


def _create_canvases(
    images_info: List[Dict[str, Any]], manifest_id: str, config: Dict[str, Any]
) -> List[Canvas]:
    """Creates the list of canvases for the manifest."""
    logging.debug(f"Starting to create canvases for manifest_id: {manifest_id}")
    canvases = []
    for i, image_info in enumerate(images_info):
        canvas_id = f"{manifest_id}/canvas/{i + 1}"
        canvas = Canvas(
            id=canvas_id, width=image_info["width"], height=image_info["height"]
        )

        image_id = get_id(image_info)
        image_service = {"id": image_id, "type": "ImageService3", "profile": "level2"}

        image_filename = image_id.split("/")[-1] if image_id else "unknown_image"

        anno_body = {
            "id": f"{config['image_service_base_url']}{image_filename}",
            "type": "Image",
            "format": "image/jpeg",
            "service": image_service,
        }

        anno = Annotation(
            id=f"{canvas_id}/annotation/1",
            type="Annotation",
            motivation="painting",
            body=anno_body,
            target=canvas_id,
        )

        anno_page = AnnotationPage(id=f"{canvas_id}/page/1", items=[anno])
        canvas.items = [anno_page]
        canvases.append(canvas)
        logging.debug(f"Created canvas {canvas_id} for image {image_id}")
    logging.debug(
        f"Finished creating {len(canvases)} canvases for manifest_id: {manifest_id}"
    )
    return canvases


def _create_metadata(
    occurrence_data: Dict[str, Any], full_scientific_name: str, config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Creates the metadata list for the manifest."""
    logging.debug("Starting to create metadata for manifest.")
    metadata = []
    lang = config.get("default_language", "en")

    if full_scientific_name:
        metadata.append(
            {
                "label": {lang: ["ScientificName"]},
                "value": {lang: [full_scientific_name]},
            }
        )
        logging.debug(f"Added scientific name to metadata: {full_scientific_name}")

    for key in config["metadata_keys"]:
        if key in [
            "genus",
            "subgenus",
            "specificEpithet",
            "infraspecificEpithet",
            "scientificNameAuthorship",
        ]:
            continue
        if key in occurrence_data and occurrence_data[key] is not None:
            metadata.append(
                {"label": {lang: [key]}, "value": {lang: [str(occurrence_data[key])]}}
            )
            logging.debug(f"Added metadata key '{key}': {occurrence_data[key]}")
    logging.debug("Finished creating metadata.")
    return metadata


def create_manifest(
    manifest_id: str,
    catalog_number: str,
    images_info: List[Dict[str, Any]],
    occurrence_data: Dict[str, Any],
    config: Dict[str, Any],
) -> Manifest:
    """
    Creates a IIIF Manifest v3.0 object for a specimen.

    Maps occurrence metadata and image information to the IIIF standard.
    Supports configurable internationalization via the 'default_language' key.

    Args:
        manifest_id (str): The unique URI for the manifest.
        catalog_number (str): The specimen's catalog number (used for labels).
        images_info (List[dict]): List of image metadata (width, height, ID).
        occurrence_data (Dict[str, Any]): Key-value pairs of specimen metadata.
        config (Dict[str, Any]): Application configuration.

    Returns:
        Manifest: A pydantic-based IIIF Manifest object.
    """
    logging.info(f"Creating manifest for Catalog Number: {catalog_number}")
    full_scientific_name = _get_scientific_name(occurrence_data)
    label_text = (
        f"{catalog_number} - {full_scientific_name}"
        if full_scientific_name
        else catalog_number
    )
    lang = config.get("default_language", "en")

    manifest_kwargs = config.get("manifest", {}).copy()
    manifest_kwargs.update({"id": manifest_id, "label": {lang: [label_text]}})

    manifest = Manifest(**manifest_kwargs)
    manifest.items = _create_canvases(images_info, manifest_id, config)
    manifest.metadata = _create_metadata(occurrence_data, full_scientific_name, config)
    logging.info(f"Manifest created successfully for Catalog Number: {catalog_number}")

    return manifest
