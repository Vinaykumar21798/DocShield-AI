"""
Authentication and password security helpers.

Uses only the standard library:

- Password hashing: PBKDF2-HMAC-SHA256 with a per-user random salt. The
  stored value is a self-describing string so the iteration count and salt
  can change over time without invalidating existing hashes:
  ``pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>``.
- Session tokens: opaque random tokens (never persisted in plaintext). Only
  the SHA-256 digest of the token is stored in the database.
"""
import hashlib
import hmac
import secrets

from core.config import settings

HASH_ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = settings.auth_pbkdf2_iterations
SALT_BYTES = 16
DIGEST_BYTES = 32


def hash_password(
    password: str,
    iterations: int = DEFAULT_ITERATIONS,
) -> str:
    """
    Hash a plaintext password with PBKDF2-HMAC-SHA256 and a random salt.

    Args:
        password: Plaintext password.
        iterations: PBKDF2 iteration count.

    Returns:
        ``pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>``.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=DIGEST_BYTES,
    )
    return (
        f"{HASH_ALGORITHM}${iterations}$"
        f"{salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash.

    Parses the stored value and recomputes the digest with the embedded
    salt and iteration count, then compares in constant time.
    """
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$")
    except (ValueError, AttributeError):
        return False

    if algorithm != HASH_ALGORITHM:
        return False

    try:
        iterations = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False

    computed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected),
    )
    return hmac.compare_digest(computed, expected)


def generate_session_token() -> str:
    """
    Generate an opaque session token for API clients.

    The raw token is returned to the caller exactly once; only its SHA-256
    digest should be stored server-side.
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """
    Return the SHA-256 digest of an opaque session token.

    This is what is stored in the ``auth_sessions`` table so a database
    leak does not expose usable session tokens.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()