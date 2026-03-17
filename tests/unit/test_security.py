from datetime import timedelta

import pytest

from finrag_core.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_differs_from_plain(self):
        assert hash_password("supersecret") != "supersecret"

    def test_verify_correct_password(self):
        assert verify_password("mypassword", hash_password("mypassword")) is True

    def test_reject_wrong_password(self):
        assert verify_password("wrong", hash_password("mypassword")) is False


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("user-123")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"

    def test_expired_token_raises(self):
        token = create_access_token("user-123", expires_delta=timedelta(seconds=-1))
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token("user-123")
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token(token[:-5] + "XXXXX")
