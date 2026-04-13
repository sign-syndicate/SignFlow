# SignFlow Architecture

This document describes the current repository state.

## Current State

The code implementation has been intentionally removed from the main branch to prepare for a clean rebuild.

- No Python source files are present.
- Architecture described in earlier versions is no longer applicable.
- Folder layout and non-code project assets are preserved.

## Directory Structure

```
SignFlow/
├── Code/
│   ├── core/
│   ├── ui/ 
│   └── models/
├── Documents/
│   └── architecture.md
├── README.md
├── requirements.txt
├── LICENSE
└── .gitignore
```

## Notes

- `requirements.txt` is kept as dependency metadata and can be revised during rebuild.
- `Code/models/` is preserved for model files and related assets.
- Future architecture should be documented here as new source modules are added.
