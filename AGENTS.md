# GWAITH Agent Contributor Guide

This document provides guidelines for AI agents contributing to the GWAITH project.

## 1. Project Aim

GWAITH (Welsh for "work") is a flexible scientific workflow management system. Its primary purpose is to automate the generation of complex, multi-step data analysis pipelines, particularly iterative "round-robin"/"blocked gibbs" analyses for use in the LISA global fit in gravitational wave astronomy.

The system takes a high-level configuration file and generates a complete, executable workflow for various target execution environments, including local Bash execution, HTCondor, Slurm, and Pegasus. It is designed to handle dependencies between processing steps, manage intermediate data products, and provide a robust, reproducible analysis framework.

## 2. Repository Structure

The repository is organized as follows:

*   `/src/gwaith/`: Contains the core source code for the project.
    *   `types/`: Defines the fundamental data structures used throughout the application, such as `TimeSeries` and `FrequencySeries`.
    *   `workflow/`: The heart of the application, containing the logic for building, exporting, and submitting analysis workflows.
        *   `types/`: Defines the components of a workflow, like `GwaithWorkflow`, `GwaithNode`, and `GwaithFile`.
        *   `exporters/`: Contains modules for exporting the abstract workflow into concrete, runnable scripts for different platforms (e.g., `bash_exporter.py`, `pegasus_exporter.py`).
    *   `io/`: Provides utilities for handling input/output, including command-line argument parsing.
    *   `config/`: Manages the loading and parsing of YAML configuration files.
*   `/tools/`: Contains modules that are exposed as command-line tools (via `pyproject.toml`). These tools perform the individual analysis steps that form the nodes of a workflow.
*   `/examples/`: Contains example configurations and scripts to demonstrate how to use GWAITH. The `examples/README.md` is a crucial resource for understanding a typical use case.
*   `/tests/`: Contains unit tests and integration tests for the project.

## 3. Licensing Constraint

**Important:** This project cannot incorporate any code or dependencies that are licensed under the GNU General Public License (GPL) or its variants (LGPL, AGPL). Please ensure that any proposed additions or modifications are compatible with a more permissive license (e.g., MIT, Apache 2.0, BSD).

## 4. Agent Contribution and Testing Protocol

All code changes submitted by an agent must be rigorously tested before they can be accepted. The following two-step process is mandatory:

1.  **Unit Tests:** All existing unit tests must pass. If new functionality is added, corresponding new unit tests must be created to cover the changes.

2.  **Example Workflow Validation:** After the unit tests pass, the example workflow must be executed to ensure that the changes have not introduced any regressions in a full integration scenario. The process is:
    *   Generate the example data if it doesn't exist.
    *   Build the example workflow using `gwaith_build_workflow`.
    *   Run the generated `run_workflow.sh` script.

Only after both steps complete successfully can the code be submitted for review.
