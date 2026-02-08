# Инсталиране и употреба

## Prerequisites
* Python >=3.9
* pip (Python package manager)

## Quick Start

1.  **Clone/Download** проектът върху вашата машина.

2.  **Създайте Virtual Environment**:
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    ```

3.  **Инсталирайте Dependencies**:
    Тъй като използваме `pyproject.toml`, може да се инсталира всичко с една команда:
    ```bash
    pip install -e .[dev]
    ```

4.  **Пуснете играта**:
    ```bash
    python main.py
    ```