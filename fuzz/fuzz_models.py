"""Coverage-guided fuzzing (atheris/libFuzzer) of the input-validation layer.
Property: any input is either accepted or rejected with ValidationError, never another exception."""

import os
import sys
from pathlib import Path

import atheris

# A raiz do projeto entra no sys.path: `python fuzz/fuzz_models.py` só enxerga a pasta fuzz/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("APP_JWT_SECRET", "fuzz-only-secret-with-at-least-32-characters")

with atheris.instrument_imports():
    from pydantic import ValidationError

    from app.api.auth import RegisterIn
    from app.api.tasks import TaskIn


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    title = fdp.ConsumeUnicodeNoSurrogates(200)
    email = fdp.ConsumeUnicodeNoSurrogates(100)
    password = fdp.ConsumeUnicodeNoSurrogates(100)
    for model, payload in (
        (TaskIn, {"title": title}),
        (RegisterIn, {"email": email, "password": password}),
    ):
        try:
            model(**payload)
        except ValidationError:
            pass  # rejected cleanly: expected


atheris.Setup(sys.argv, test_one_input)
atheris.Fuzz()
