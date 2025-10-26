## Quick context

This project is a small pipeline for tomato leaf disease detection and explanation using DSPy and an LLM (OpenAI / gpt-4o). Key components:

- `src/main.py` — orchestration: verify plant photo, run disease predictor, and generate child-friendly explanation.
- `src/PlantDetector.py` — uses OpenAI chat completions (gpt-4o) to return a simple True/False (is-this-a-plant) for images.
- `src/PlantDoctor.py` — loads a DSPy compiled program from `./compiled_leaf_disease` and returns the disease label.
- `src/ExplainDiseaseForKids.py` — DSPy module that maps disease → (explain, cause, cure) for downstream presentation.
- `src/train_PlantDoctor.py` & `src/make_dataset.py` — build DSPy datasets and compile a program into `compiled_leaf_disease`.
- `src/server.py` — simple FastAPI wrapper exposing POST /analyze that calls `main()` and returns JSON.

## Big picture / data flow

1. An image URL is posted to the API (`src/server.py`). The server downloads the image to a temp file.
2. `main()` in `src/main.py` calls `PlantDetector.analyze_image()` to confirm the photo is of a plant.
3. If plant, `PlantDoctor.analyze_disease()` loads `compiled_leaf_disease` (dspy compiled program) and predicts one of the dataset labels.
4. `ExplainDiseaseForKids.explain()` produces human-friendly strings (explain, cause, cure) using DSPy prediction.

This separation (detector → classifier → explainer) is intentional: small, independent responsibilities.

## Important files to consult (examples)

- Orchestration: `src/main.py` — shows the three-step flow and how results are packaged.
- Production API: `src/server.py` — illustrates expected input JSON and output format.
- Inference: `src/PlantDoctor.py` — calls `dspy.load("./compiled_leaf_disease")` and expects a `Prediction.answer` string.
- Training/compile: `src/train_PlantDoctor.py` — builds DSPy `Signature`, `Module`, compiles with `MIPROv2` and `save("./compiled_leaf_disease")`.
- Dataset builder: `src/make_dataset.py` — reads `./data/*` folders and returns `dspy.Example(image=..., answer=class)`.

## Project-specific conventions & gotchas

- DSPy compiled artifacts are stored at `./compiled_leaf_disease`. Inference expects this exact relative path — keep it in sync with training output.
- `data/` folders are used both for training and quick tests. `make_dataset.build_datasets()` excludes `Yes_tomato` / `No_tomato` when building disease classes.
- `src/PlantDetector.test_dataset()` expects `data/Yes_tomato` and `data/No_tomato` for a simple binary dataset.
- API key location: `config.json` (root). The code reads `config.json` directly (do not rely on env vars unless you change the code).
- LLM model names used in code: `gpt-4o` (see `src/PlantDetector.py` and DSPy LM config in `src/PlantDoctor.py` & `src/train_PlantDoctor.py`).

## Dev workflows (concrete commands)

1) Install deps (uses `requirements.txt`):

```bash
python -m pip install -r requirements.txt
```

2) Run the API (local):

```bash
# Option A: run server script directly
python src/server.py

# Option B: use uvicorn (reload helpful during development)
uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```

3) Train / compile DSPy program (produces `./compiled_leaf_disease`):

```bash
python src/train_PlantDoctor.py
```

4) Build dataset helper (inspect/test):

```bash
python src/make_dataset.py
```

5) Run quick local inference (from repository root):

```bash
python -c "from src.main import main; print(main('./data/Leaf_mold/16.jpeg', 'temp info', 'humidity info'))"
```

## Integration points & external deps

- DSPy (custom high-level framework) — used for prompt optimization, train/eval, and compiled models. See `requirements.txt` for version in use and imports across `src/*.py`.
- OpenAI / gpt-4o — used directly in `src/PlantDetector.py` and configured via `config.json` for the API key.
- FastAPI + Uvicorn — exposes the HTTP API used by downstream clients.

## Patterns agents should follow when editing

- When changing inference paths, update both `src/PlantDoctor.py` (loader) and `src/train_PlantDoctor.py` (saver) to avoid mismatches.
- Prefer small, local changes: the code expects relative paths (e.g., `../config.json` from `src/`). Use project-root context when running scripts.
- When editing prompts inside DSPy modules, prefer changing the `disease_info` strings in `train_PlantDoctor.py` and `ExplainDiseaseForKids.py` because they are the canonical human-readable definitions.

## Quick safety notes

- `config.json` contains the OPENAI_API_KEY. Avoid committing new secrets; use `gitignore` or environment variables if you rotate keys.

## If you need to extend functionality

- To add a new disease label: add a new folder under `data/`, ensure `make_dataset.build_datasets()` picks it up, then re-run `python src/train_PlantDoctor.py` to recompile `compiled_leaf_disease`.
- To serve a different model or key location: update the DSPy LM config in `src/PlantDoctor.py` and `src/train_PlantDoctor.py` and ensure `config.json` (or env var loader) is in place.

---
If anything here is unclear or you want me to expand a particular section (examples of prompt text, more run/debug tips, or automated tests), tell me which part and I'll iterate.
