from dataclasses import dataclass

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type



# OWASP's current minimum Argon2id profile. These values are encoded into every
# hash, which lets the application transparently increase the work factor later.
password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19 * 1024,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


@dataclass(frozen=True)
class PasswordVerification:
    valid: bool
    needs_rehash: bool = False


def hash_password(plain: str) -> str:
    return password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> PasswordVerification:
    """Verify Argon2id hashes and support migration from legacy bcrypt hashes."""
    if hashed.startswith("$2"):
        try:
            valid = bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
            return PasswordVerification(valid=valid, needs_rehash=valid)
        except ValueError:
            return PasswordVerification(valid=False)

    try:
        valid = password_hasher.verify(hashed, plain)
        return PasswordVerification(
            valid=valid,
            needs_rehash=valid and password_hasher.check_needs_rehash(hashed),
        )
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return PasswordVerification(valid=False)
