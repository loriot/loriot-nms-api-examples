<!-- Creator: LORIOT AG -->

# LORIOT API Implementation Example

This repository contains example Python scripts demonstrating how to interact with the [loriot.io](https://loriot.io) Network Server API.

The main example in this repository lives in the `nms_gws_update` folder. A dedicated README in that folder documents `main.py` usage and script-specific details.

## Repository Layout

* `nms_gws_update/` - Example script for updating connected gateways running the LORIOT gateway binary. See the folder-level README for usage instructions.
* `loriot-public/` - Git submodule: the public [LORIOT Python library](https://github.com/loriot/loriot-python-library) (`loriot` package) used by the examples.

> **Disclaimer:** This repository is provided to share an implementation example. **THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.** It is not an officially supported LORIOT product.

## Prerequisites

* Python 3.8+
* A valid LORIOT API Token

## Setup Instructions

1. **Clone the repository together with the library submodule:**
   ```bash
   git clone --recurse-submodules <repository-url> loriot-api-examples
   cd loriot-api-examples
   # in an existing clone:
   git submodule update --init
   ```

2. **Create a virtual environment and install the library:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r nms_gws_update/requirements.txt   # run from the repository root
   ```

3. **Run an example:** see the folder-level README, e.g. `nms_gws_update/README.md`.

## License

Apache License, Version 2.0. See [LICENSE](LICENSE).
