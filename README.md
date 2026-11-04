# UCI Chess Engine With Computer Vision Support

[![CI](https://github.com/wompbreaker/chess-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/wompbreaker/chess-engine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)

A UCI chess engine written from scratch in Python, built as a learning project, with a planned port to C++ once the design is proven correct.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Overview](#overview)
- [Roadmap](#roadmap)
- [Development](#development)
- [License](#license)

---

## Quick Start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/wompbreaker/chess-engine.git
cd chess-engine
uv sync
```

> The engine is under construction. UCI usage will be documented here once Phase N lands.

---

## Overview

(What the engine is, planned features, how the Python, C++, and OpenCV parts fit together.)

---

## Roadmap

Progress is tracked on the [project board](LINK_TO_YOUR_PROJECT).

| Phase | Goal |
|-------|------|
| 0 | Python scaffolding and CI |
| 1-9 | Pure Python engine |
| 10 | C++ port |
| 11 | OpenCV real-time board monitoring |

---

## Development

```bash
uv sync                                   # install dependencies
uv run pre-commit install --install-hooks -t pre-commit -t commit-msg
uv run pytest                             # tests
uv run ruff check . && uv run ruff format --check .   # lint
uv run mypy                               # type check
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `test:`, ...).

---

## License

[MIT](LICENSE)
