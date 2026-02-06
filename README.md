# Specify IIIF Manifest Generator

A robust, configuration-driven tool designed to transform Specify database exports into IIIF (International Image Interoperability Framework) v3.0 compliant manifests.

## Overview

The Specify IIIF Manifest Generator automates the creation of rich digital object metadata for scientific collections. By mapping Darwin Core standards and Specify-specific exports to the IIIF Presentation API, it enables seamless integration with universal viewers (e.g., Mirador, UV) and digital asset management systems.

## Key Features

- **IIIF v3.0 Compliance**: Generates manifests compatible with the latest IIIF standards using `iiif-prezi3`.
- **Collection-Agnostic**: Support for diverse scientific domains (e.g., Entomology, Geosciences) via modular YAML configurations.
- **Efficient Processing**: Implements a "partial" generation mode and multi-threaded image discovery to optimize large-scale updates.
- **Production-Ready Dockerization**: Multi-stage Docker builds ensure a minimal footprint, guarded by automated CI/CD verification.
- **Comprehensive Validation**: Automatic filtering of malformed records and missing media assets.

## Architecture & Workflow

1.  **Extraction**: Ingests tabular data (TSV/CSV) exported from Specify.
2.  **Transformation**: Maps specimen metadata and media URIs to IIIF structures.
3.  **Resolution**: Validates and retrieves image dimensions via IIIF Image Service endpoints, utilizing parallel execution for high-performance discovery.
4.  **Generation**: Outputs deterministic JSON manifests named by `catalogNumber`.

---

## Prerequisites
- **Docker** & **Docker Compose**
- (Optional) **Python 3.12+** for local development.

---

## Getting Started

### Docker Usage (Recommended)

The containerized workflow handles all dependencies and environment configurations. The image uses a non-root user (`appuser`) for enhanced security.

#### Building the Docker Image

Before running, build the Docker image using Docker Compose:

```bash
docker compose build
```

#### Running the Generator

To execute the generator for a specific collection, use `docker compose run`. The `docker-compose.yml` file defines the service `specify-iiif-manifest`.

> [!NOTE]
> Environment variables `UID` and `GID` are utilized by the compose file to ensure generated files match your local user permissions.

```bash
# General Syntax
UID=$(id -u) GID=$(id -g) docker compose run --rm specify-iiif-manifest <CONFIG_PATH> [OPTIONS]

# Example: Geoscience Collection (Partial Mode)
UID=$(id -u) GID=$(id -g) docker compose run --rm specify-iiif-manifest config/config-geoscience.yml --mode partial
```

### Local Development Setup

If you prefer to run the application outside of Docker:

1.  **Install Dependencies**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```
2.  **Execution**:
    ```bash
    source .venv/bin/activate
    python -m src.cli config/config-entomology.yml
    ```

---

## Configuration Schema

Configured via YAML files in the `config/` directory.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `image_service_base_url` | String | Root URL for the IIIF Image Service. |
| `default_language` | String | Default language code for manifest labels and metadata (e.g., "en", "sv"). |
| `manifest_dir` | Path | Output directory for generated JSON files. |
| `error_log_file` | Path | Destination for execution logs. |
| `occurrence_csv` | Path | Path to the main specimen data export. |
| `metadata_keys` | List | Darwin Core terms to include in the manifest metadata. |
| `manifest.rights` | URI | License URI applied to the manifests. |

---

## Developer Guide

### Quality Assurance
The project utilizes `pytest` for automated testing and `ruff` for linting. The CI/CD pipeline enforces these standards on every push.

#### Running Tests
To execute the test suite (includes unit and integration tests):
```bash
source .venv/bin/activate
PYTHONPATH=. python -m pytest
```

#### Linting
```bash
source .venv/bin/activate
python -m ruff check .
```

### Logging & Troubleshooting
Logs are separated by collection and stored in the `log/` directory. Critical failures (e.g., missing mandatory dependencies or network timeouts) are logged with full stack traces.

