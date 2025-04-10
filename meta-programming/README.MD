# Metaclass-Based Document Validation & Processing

This project demonstrates **advanced meta-programming** in Python by using **custom metaclasses** to enforce specific contracts on classes, automatically **register** them, and provide a **dynamic plugin loader**. The solution also includes scripts for **logging**, **testing**, and **generating documentation**. Below, you’ll find all the details on how it works, how to set it up, and why it satisfies the challenge requirements.

## Table of Contents
1. [Overview](#overview)
2. [Project Goals](#project-goals)
3. [Key Requirements & Where They’re Met](#key-requirements--where-theyre-met)
4. [Repository Structure](#repository-structure)
5. [How it Works](#how-it-works)
   - [1. Metaclass Enforcement (ContractMeta)](#1-metaclass-enforcement-contractmeta)
   - [2. BaseContract (ABC)](#2-basecontract-abc)
   - [3. Automatic Registration](#3-automatic-registration)
   - [4. Plugin Loader](#4-plugin-loader)
   - [5. Logging Instead of Print](#5-logging-instead-of-print)
   - [6. Documentation Generation](#6-documentation-generation)
6. [Examples](#examples)
7. [Running Tests](#running-tests)
8. [Future Extensions](#future-extensions)
9. [License](#license)

---

## Overview
This library allows developers to create **document validators** and **processors** by simply inheriting from `BaseContract`. The **metaclass** ensures each subclass implements:

- `validate(self, data: dict) -> bool` – Validation logic (with docstring).
- `process(self, data: dict)` – Post-validation processing logic (with docstring).
- A **class docstring** describing what the class is.

If these rules are not met, the code raises a **TypeError** at class definition time, ensuring “fail-fast” behavior. Additionally, the plugin loader can **dynamically discover** these classes from a specified directory, making the system **extensible** without changing the core code.

---

## Project Goals
1. **Advanced Meta-Programming**: Show in-depth knowledge of metaclasses by enforcing contracts and automatically registering classes.
2. **Runtime Validation**: Ensure classes define required methods and docstrings with correct type hints/signatures.
3. **Clean Architecture**: Maintain a clear separation of responsibilities (core, metaclasses, plugins, examples, tests).
4. **Extensibility**: A plugin system that allows new “document contract” classes to be loaded and discovered dynamically.
5. **Professional Practices**: Use of `logging`, docstrings, type hints, and demonstration scripts, culminating in a well-tested and documented library.

---

## Key Requirements & Where They’re Met
Below is a summary linking the **challenge requirements** to the **solution** components:

1. **“Uses metaclasses to enforce a specific API contract across multiple classes.”**  
   - Our `ContractMeta` metaclass (in `src/core/metaclasses/contract_meta.py`) checks for `validate` and `process` methods, docstrings, etc.
2. **“Automatically registers classes in a registry upon definition.”**  
   - In `ContractMeta.__new__`, we add classes (that are not base classes) into `ContractMeta.REGISTRY`.
3. **“Provides runtime validation of class attributes and methods.”**  
   - `ContractMeta` raises `TypeError` if docstrings or methods are missing, or if type hints are incorrect (optional).
4. **“Should support inheritance properly.”**  
   - `BaseContract` (using `ABC` + `ContractMeta`) is the parent. Each plugin (e.g., `FinancialContract`) inherits from it, no conflict after we unify `abc.ABCMeta` with our custom metaclass.
5. **“Must include descriptive error messages for contract violations.”**  
   - `ContractMeta` raises exceptions with clear messages (“Class must implement method 'validate'...”, etc.).
6. **Additional**:
   - **Logging** instead of print (professional approach).
   - **Plugin Loader** for dynamic discovery.
   - **Documentation Generator** script to produce a Markdown file listing all discovered classes.

---

## Repository Structure
A typical layout might be:

```
metaclass-contract/
├── src/
│   ├── core/
│   │   ├── metaclasses/
│   │   │   └── contract_meta.py
│   │   └── interfaces/
│   │       └── base_contract.py
│   ├── external/
│   │   └── plugin_loader.py
│   └── plugins/
│       ├── financial_contract.py
│       └── hr_document.py
├── examples/
│   ├── demonstrate_financial.py
│   ├── demonstrate_hr.py
│   ├── demonstrate_plugin_load.py
│   └── generate_docs.py
├── tests/
│   ├── test_contract.py
│   └── test_workflows.py
├── requirements.txt (or pyproject.toml)
└── README.md (this file)
```

*(Adjust file paths as needed for your real project.)*

---

## How it Works

### 1. Metaclass Enforcement (`ContractMeta`)
- Located in `src/core/metaclasses/contract_meta.py`.
- In `__new__`, it checks for:
  1. A **class docstring** (or raises `TypeError`).
  2. Methods `validate` and `process`.
  3. Method docstrings of minimum length.
  4. (Optional) Type hints, e.g., ensuring `validate(self, data: dict) -> bool`.

If any of these checks fail, a descriptive **TypeError** or `AttributeError` is thrown before the class is successfully created.

### 2. `BaseContract` (ABC)
- Found in `src/core/interfaces/base_contract.py`.
- Declares `@abstractmethod` placeholders for `validate` and `process`.
- Uses the metaclass `ContractMeta`.
- This combination (`ABC` + `ContractMeta`) ensures sub-classes must implement the required methods, plus the extended checks from `ContractMeta`.

### 3. Automatic Registration
- Once a subclass of `BaseContract` is imported, `ContractMeta.__new__` automatically puts it in `ContractMeta.REGISTRY`.
- This registry can later be used to **list** or **instantiate** discovered classes.

### 4. Plugin Loader
- `plugin_loader.py` scans a directory (e.g., `src/plugins/`) for `.py` files.
- Dynamically imports each file, searching for classes that inherit from `BaseContract`.
- This triggers the metaclass checks and populates the registry.
- The system is thus **extensible**: simply drop a new `.py` file in `plugins/` containing a class like:

  ```python
  from src.core.interfaces.base_contract import BaseContract

  class MyNewDocument(BaseContract):
      """Docstring explaining the document"""

      def validate(self, data: dict) -> bool:
          ...

      def process(self, data: dict):
          ...
  ```

### 5. Logging Instead of `print`
- All scripts use Python’s `logging` module for messages, allowing flexible verbosity levels (`INFO`, `WARN`, etc.).
- This is a **best practice** in production code over raw `print` statements.

### 6. Documentation Generation
- A script `generate_docs.py` iterates `ContractMeta.REGISTRY` and creates a Markdown file (`plugins_doc.md`) summarizing each discovered class, its docstring, and the docstrings for `validate` / `process`.
- Before generating docs, you must **import** or **load** the plugin classes so that the registry is populated.

---

## Examples
We provide **four** demonstration scripts in the `examples/` folder:

1. **`demonstrate_financial.py`**  
   - Imports `FinancialContract` from `src/plugins/financial_contract.py`.  
   - Attempts to validate and process both valid and invalid data, showing how the contract reacts.

2. **`demonstrate_hr.py`**  
   - Same approach, but for `HRDocument`, verifying field presence and ID numeric.

3. **`demonstrate_plugin_load.py`**  
   - Uses `PluginLoader` to dynamically discover all `.py` files in `src/plugins/`, listing them and testing one or more classes.

4. **`generate_docs.py`**  
   - Optionally calls `PluginLoader.load_plugins(...)` first, then writes a `plugins_doc.md` listing every discovered class in `ContractMeta.REGISTRY`, including docstrings.

To run an example, do:
```bash
python examples/demonstrate_financial.py
```
Or whichever script you want to see in action.

---

## Running Tests
If using `pytest`, simply:
```bash
pytest --maxfail=1 --disable-warnings -v
```
Typical tests:
- **`test_contract.py`**: Ensures classes missing `validate`/`process` or docstrings raise `TypeError`.
- **`test_workflows.py`** (or other test files): Additional checks for correct behavior in real scenarios.

---

## Future Extensions
1. **Multiple Contract Types**: For instance, “AdvancedContractMeta” requiring even more methods (e.g., `stop`, `rollback`).
2. **Dynamic Revalidation**: If the contract changes, re-check existing classes in the registry.
3. **Performance / Stress Tests**: For large volumes of data or many plugins.
4. **Automated Docs**: Generating HTML or a web UI for discovered classes, beyond Markdown.
5. **CI/CD Integration**: Adding GitHub Actions / Jenkins pipelines to automate tests & lint checks.

---

## License
*(Adjust this section according to your chosen license.)*

```
MIT License

Copyright (c) ...

Permission is hereby granted, free of charge, ...
```

---

**Thank you for exploring Metaclass-Based Document Validation & Processing!**  
If you have any questions, issues, or suggestions, feel free to open an Issue or Pull Request in this repository.

