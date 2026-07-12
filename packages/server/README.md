# Lappa server

Python CLI + FastAPI backend for the Lappa ROS2 package IDE.

```bash
pip install -e ".[dev,api]"
lappa demo
lappa serve --port 8840
```

Tests: `pytest -q` · Lint: `ruff check src tests`
