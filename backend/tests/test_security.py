"""Hash de senhas e tokens JWT."""

from __future__ import annotations

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_e_verificacao_de_senha():
    encoded = hash_password("Clinic@2026")
    assert encoded != "Clinic@2026"
    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password("Clinic@2026", encoded)
    assert not verify_password("senha-errada", encoded)
    assert not verify_password("Clinic@2026", "formato-invalido")


def test_token_jwt_roundtrip():
    token = create_access_token("user@example.com", role="GESTOR")
    payload = decode_access_token(token)
    assert payload["sub"] == "user@example.com"
    assert payload["role"] == "GESTOR"
    assert payload["iss"] == "clinic-analytics"


def test_token_invalido():
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("token-invalido")
