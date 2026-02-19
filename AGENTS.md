# RayRun Project Guide

## Project Goal

RayRun is a Jupyter notebook widget that provides on-demand cloud GPU/CPU compute for experimentation. Users can spin up RunPod instances with Ray distributed computing framework through an interactive widget, run remote computations, and automatically shut down when idle to minimize costs.

## Important Files

- **SPEC.md**: Full project specification with architecture, components, and requirements
- **DOCS_RUNPOD.md**: Concise RunPod API documentation with examples
- **runpod_openapi.json**: Full OpenAPI schema for RunPod API

## Tooling

### uv - Fast Python Package Manager

This project uses **uv** for dependency management and script execution.

**Common Commands**:

```bash
# Run a script with dependencies
uv run --with requests --with python-dotenv script.py

# Add a dependency to pyproject.toml
uv add <package>

# Install project dependencies
uv sync
```
