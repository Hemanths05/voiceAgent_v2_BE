"""
Input Validation Utilities
Common validators for API inputs
"""
import re
from typing import Optional
from app.core.exceptions import ValidationError


class Validators:
    """
    Collection of input validation utilities
    """

    # Regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format
    TWILIO_PHONE_PATTERN = re.compile(r'^\+1\d{10}$')  # US format: +1XXXXXXXXXX
    TWILIO_SID_PATTERN = re.compile(r'^[A-Z]{2}[a-f0-9]{32}$')  # Twilio SID format
    MONGODB_OBJECTID_PATTERN = re.compile(r'^[a-f0-9]{24}$')

    @staticmethod
    def validate_email(email: str, field_name: str = "email") -> str:
        """
        Validate email format

        Args:
            email: Email address to validate
            field_name: Name of field for error messages

        Returns:
            Normalized email (lowercase)

        Raises:
            ValidationError: If email is invalid
        """
        if not email or not isinstance(email, str):
            raise ValidationError(f"{field_name} is required", {"field": field_name})

        email = email.strip().lower()

        if not Validators.EMAIL_PATTERN.match(email):
            raise ValidationError(
                f"Invalid {field_name} format",
                {"field": field_name, "value": email}
            )

        return email

    @staticmethod
    def validate_password(
        password: str,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = False,
        field_name: str = "password"
    ) -> str:
        """
        Validate password strength

        Args:
            password: Password to validate
            min_length: Minimum password length
            require_uppercase: Require at least one uppercase letter
            require_lowercase: Require at least one lowercase letter
            require_digit: Require at least one digit
            require_special: Require at least one special character
            field_name: Name of field for error messages

        Returns:
            Password (unchanged)

        Raises:
            ValidationError: If password doesn't meet requirements
        """
        if not password or not isinstance(password, str):
            raise ValidationError(f"{field_name} is required", {"field": field_name})

        errors = []

        if len(password) < min_length:
            errors.append(f"at least {min_length} characters")

        if require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("at least one uppercase letter")

        if require_lowercase and not re.search(r'[a-z]', password):
            errors.append("at least one lowercase letter")

        if require_digit and not re.search(r'\d', password):
            errors.append("at least one digit")

        if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("at least one special character")

        if errors:
            raise ValidationError(
                f"{field_name} must contain {', '.join(errors)}",
                {"field": field_name, "requirements": errors}
            )

        return password

    @staticmethod
    def validate_phone(
        phone: str,
        allow_twilio_format: bool = True,
        field_name: str = "phone"
    ) -> str:
        """
        Validate phone number format

        Args:
            phone: Phone number to validate
            allow_twilio_format: Allow Twilio US format (+1XXXXXXXXXX)
            field_name: Name of field for error messages

        Returns:
            Normalized phone number

        Raises:
            ValidationError: If phone is invalid
        """
        if not phone or not isinstance(phone, str):
            raise ValidationError(f"{field_name} is required", {"field": field_name})

        phone = phone.strip()

        # Check Twilio format first (stricter)
        if allow_twilio_format and Validators.TWILIO_PHONE_PATTERN.match(phone):
            return phone

        # Check E.164 format
        if Validators.PHONE_PATTERN.match(phone):
            return phone

        raise ValidationError(
            f"Invalid {field_name} format. Expected E.164 format (e.g., +1234567890)",
            {"field": field_name, "value": phone}
        )

    @staticmethod
    def validate_twilio_sid(
        sid: str,
        sid_type: str = "SID",
        field_name: str = "sid"
    ) -> str:
        """
        Validate Twilio SID format

        Twilio SIDs follow pattern: 2 uppercase letters + 32 hex chars
        Examples: AC..., CA..., SM..., etc.

        Args:
            sid: SID to validate
            sid_type: Type of SID for error messages (e.g., "Account SID", "Call SID")
            field_name: Name of field for error messages

        Returns:
            SID (unchanged)

        Raises:
            ValidationError: If SID is invalid
        """
        if not sid or not isinstance(sid, str):
            raise ValidationError(f"{sid_type} is required", {"field": field_name})

        sid = sid.strip()

        if not Validators.TWILIO_SID_PATTERN.match(sid):
            raise ValidationError(
                f"Invalid {sid_type} format",
                {"field": field_name, "value": sid}
            )

        return sid

    @staticmethod
    def validate_mongodb_id(
        object_id: str,
        field_name: str = "id"
    ) -> str:
        """
        Validate MongoDB ObjectId format

        Args:
            object_id: ObjectId to validate
            field_name: Name of field for error messages

        Returns:
            ObjectId (unchanged)

        Raises:
            ValidationError: If ObjectId is invalid
        """
        if not object_id or not isinstance(object_id, str):
            raise ValidationError(f"{field_name} is required", {"field": field_name})

        object_id = object_id.strip()

        if not Validators.MONGODB_OBJECTID_PATTERN.match(object_id):
            raise ValidationError(
                f"Invalid {field_name} format",
                {"field": field_name, "value": object_id}
            )

        return object_id

    @staticmethod
    def validate_string_length(
        value: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        field_name: str = "field"
    ) -> str:
        """
        Validate string length

        Args:
            value: String to validate
            min_length: Minimum length (optional)
            max_length: Maximum length (optional)
            field_name: Name of field for error messages

        Returns:
            Value (unchanged)

        Raises:
            ValidationError: If length is invalid
        """
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string", {"field": field_name})

        value_length = len(value)

        if min_length is not None and value_length < min_length:
            raise ValidationError(
                f"{field_name} must be at least {min_length} characters",
                {"field": field_name, "min_length": min_length, "actual_length": value_length}
            )

        if max_length is not None and value_length > max_length:
            raise ValidationError(
                f"{field_name} must be at most {max_length} characters",
                {"field": field_name, "max_length": max_length, "actual_length": value_length}
            )

        return value

    @staticmethod
    def validate_enum(
        value: str,
        allowed_values: list,
        field_name: str = "field",
        case_sensitive: bool = False
    ) -> str:
        """
        Validate value is in allowed list

        Args:
            value: Value to validate
            allowed_values: List of allowed values
            field_name: Name of field for error messages
            case_sensitive: Whether comparison is case-sensitive

        Returns:
            Normalized value

        Raises:
            ValidationError: If value is not in allowed list
        """
        if not value or not isinstance(value, str):
            raise ValidationError(f"{field_name} is required", {"field": field_name})

        value = value.strip()

        if not case_sensitive:
            value_lower = value.lower()
            allowed_lower = [v.lower() for v in allowed_values]
            if value_lower not in allowed_lower:
                raise ValidationError(
                    f"Invalid {field_name}. Must be one of: {', '.join(allowed_values)}",
                    {"field": field_name, "value": value, "allowed": allowed_values}
                )
            # Return the value with original casing from allowed_values
            idx = allowed_lower.index(value_lower)
            return allowed_values[idx]
        else:
            if value not in allowed_values:
                raise ValidationError(
                    f"Invalid {field_name}. Must be one of: {', '.join(allowed_values)}",
                    {"field": field_name, "value": value, "allowed": allowed_values}
                )
            return value

    @staticmethod
    def validate_url(
        url: str,
        allowed_schemes: list = None,
        field_name: str = "url"
    ) -> str:
        """
        Validate URL format

        Args:
            url: URL to validate
            allowed_schemes: List of allowed schemes (e.g., ["http", "https"])
            field_name: Name of field for error messages

        Returns:
            URL (unchanged)

        Raises:
            ValidationError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise ValidationError(f"{field_name} is required", {"field": field_name})

        url = url.strip()

        # Basic URL validation
        url_pattern = re.compile(
            r'^(?:http|https|ws|wss)://'  # Scheme
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # Domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # Port
            r'(?:/?|[/?]\S+)$',  # Path
            re.IGNORECASE
        )

        if not url_pattern.match(url):
            raise ValidationError(
                f"Invalid {field_name} format",
                {"field": field_name, "value": url}
            )

        # Validate scheme if specified
        if allowed_schemes:
            scheme = url.split('://')[0].lower()
            if scheme not in allowed_schemes:
                raise ValidationError(
                    f"{field_name} must use one of these schemes: {', '.join(allowed_schemes)}",
                    {"field": field_name, "value": url, "allowed_schemes": allowed_schemes}
                )

        return url

    @staticmethod
    def validate_integer_range(
        value: int,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        field_name: str = "field"
    ) -> int:
        """
        Validate integer is within range

        Args:
            value: Integer to validate
            min_value: Minimum value (optional)
            max_value: Maximum value (optional)
            field_name: Name of field for error messages

        Returns:
            Value (unchanged)

        Raises:
            ValidationError: If value is out of range
        """
        if not isinstance(value, int):
            raise ValidationError(f"{field_name} must be an integer", {"field": field_name})

        if min_value is not None and value < min_value:
            raise ValidationError(
                f"{field_name} must be at least {min_value}",
                {"field": field_name, "min_value": min_value, "actual_value": value}
            )

        if max_value is not None and value > max_value:
            raise ValidationError(
                f"{field_name} must be at most {max_value}",
                {"field": field_name, "max_value": max_value, "actual_value": value}
            )

        return value

    @staticmethod
    def validate_float_range(
        value: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        field_name: str = "field"
    ) -> float:
        """
        Validate float is within range

        Args:
            value: Float to validate
            min_value: Minimum value (optional)
            max_value: Maximum value (optional)
            field_name: Name of field for error messages

        Returns:
            Value (unchanged)

        Raises:
            ValidationError: If value is out of range
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{field_name} must be a number", {"field": field_name})

        value = float(value)

        if min_value is not None and value < min_value:
            raise ValidationError(
                f"{field_name} must be at least {min_value}",
                {"field": field_name, "min_value": min_value, "actual_value": value}
            )

        if max_value is not None and value > max_value:
            raise ValidationError(
                f"{field_name} must be at most {max_value}",
                {"field": field_name, "max_value": max_value, "actual_value": value}
            )

        return value


# Export public class
__all__ = ["Validators"]
