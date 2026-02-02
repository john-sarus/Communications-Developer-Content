"""Credential management via Windows keyring."""

import keyring

SERVICE = "avatax_comms_test_harness"

_KEYS = ("username", "password", "client_id", "client_profile_id")


def store_credentials(username: str, password: str, client_id: str, client_profile_id: str = "") -> None:
    keyring.set_password(SERVICE, "username", username)
    keyring.set_password(SERVICE, "password", password)
    keyring.set_password(SERVICE, "client_id", client_id)
    keyring.set_password(SERVICE, "client_profile_id", client_profile_id or "")


def get_credentials() -> dict | None:
    vals = {k: keyring.get_password(SERVICE, k) for k in _KEYS}
    if not vals["username"] or not vals["password"] or not vals["client_id"]:
        return None
    return vals


def has_credentials() -> bool:
    return get_credentials() is not None


def delete_credentials() -> None:
    for k in _KEYS:
        try:
            keyring.delete_password(SERVICE, k)
        except keyring.errors.PasswordDeleteError:
            pass
