import secrets
import string


class PasswordGenerator:
    """Cryptographically secure password generator module."""

    # Pre-defined character sets based on standard KeePass groups
    UPPERCASE = string.ascii_uppercase
    LOWERCASE = string.ascii_lowercase
    DIGITS = string.digits
    MINUS = "-"
    UNDERLINE = "_"
    SPACE = " "
    SPECIAL = "!$%&'*+,./:;=?@\\^`|~"
    BRACKETS = "[]{}()<>"
    LATIN1_SUPPLEMENT = (
        "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
    )

    @classmethod
    def generate(
        cls,
        length: int = 20,
        use_upper: bool = True,
        use_lower: bool = True,
        use_digits: bool = True,
        use_minus: bool = False,
        use_underline: bool = False,
        use_space: bool = False,
        use_special: bool = False,
        use_brackets: bool = False,
        use_latin1: bool = False,
        custom_chars: str = "",
    ) -> str:
        """Generates a cryptographically secure random password meeting the

        specified character set criteria.
        """
        char_pools = []
        if use_upper:
            char_pools.append(cls.UPPERCASE)
        if use_lower:
            char_pools.append(cls.LOWERCASE)
        if use_digits:
            char_pools.append(cls.DIGITS)
        if use_minus:
            char_pools.append(cls.MINUS)
        if use_underline:
            char_pools.append(cls.UNDERLINE)
        if use_space:
            char_pools.append(cls.SPACE)
        if use_special:
            char_pools.append(cls.SPECIAL)
        if use_brackets:
            char_pools.append(cls.BRACKETS)
        if use_latin1:
            char_pools.append(cls.LATIN1_SUPPLEMENT)

        # Build full character pool (and include custom string as a standalone pool if custom characters exist without standard sets)
        full_pool = "".join(char_pools) + custom_chars

        if not full_pool:
            raise ValueError(
                "At least one character set or custom character string must be provided."
            )

        # Handle custom characters as a pool requirement if only custom characters are entered
        required_pools = list(char_pools)
        if custom_chars and not char_pools:
            required_pools.append(custom_chars)

        if length < len(required_pools):
            raise ValueError(
                f"Password length ({length}) is too short to include a character from every selected set ({len(required_pools)} required)."
            )

        password_chars = []

        # Guarantee at least one character from each active requirement pool
        for pool in required_pools:
            password_chars.append(secrets.choice(pool))

        # Fill remaining length from full combined pool
        remaining_length = length - len(password_chars)
        for _ in range(remaining_length):
            password_chars.append(secrets.choice(full_pool))

        # Cryptographically secure Fisher-Yates shuffle
        for i in range(len(password_chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_chars[i], password_chars[j] = (
                password_chars[j],
                password_chars[i],
            )

        return "".join(password_chars)