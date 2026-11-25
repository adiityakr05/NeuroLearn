import pytest
from pydantic import ValidationError
from app.core.config import Settings, INSECURE_DEV_JWT_SECRET


def test_development_configuration_defaults_pass():
    """Test that standard local development settings instantiate smoothly."""
    s = Settings(ENVIRONMENT="development", DEBUG=True)
    assert s.ENVIRONMENT == "development"
    assert s.DEBUG is True
    assert s.JWT_SECRET == INSECURE_DEV_JWT_SECRET


def test_production_without_explicit_jwt_secret_fails():
    """Test that production environment rejects the default insecure dev secret."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            # Leaving default JWT_SECRET
        )
    assert "JWT_SECRET must be explicitly set" in str(exc_info.value)


def test_production_with_short_secret_fails():
    """Test that production environment rejects secrets with fewer than 32 bytes."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET="too_short_secret_under_32_bytes",
        )
    assert "at least 32 bytes" in str(exc_info.value)


def test_production_with_debug_enabled_fails():
    """Test that production environment cannot start with DEBUG=True."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            JWT_SECRET="a" * 32,
        )
    assert "DEBUG mode cannot be enabled in production" in str(exc_info.value)


def test_production_with_wildcard_cors_fails():
    """Test that production environment rejects wildcard '*' CORS when credentials are enabled."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET="a" * 32,
            BACKEND_CORS_ORIGINS=["*"],
        )
    assert "cannot contain wildcard '*'" in str(exc_info.value)


def test_production_with_malformed_cors_origin_fails():
    """Test that production environment validates CORS origin protocol schemes."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET="a" * 32,
            BACKEND_CORS_ORIGINS=["neurolearn.example.com"],  # missing http:// or https://
        )
    assert "must begin with http:// or https://" in str(exc_info.value)


def test_production_valid_configuration_succeeds():
    """Test that a fully compliant production configuration instantiates successfully."""
    valid_secret = "b" * 32
    s = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET=valid_secret,
        BACKEND_CORS_ORIGINS=["https://neurolearn.example.com", "https://app.neurolearn.io"],
    )
    assert s.ENVIRONMENT == "production"
    assert s.DEBUG is False
    assert s.JWT_SECRET == valid_secret
    assert len(s.BACKEND_CORS_ORIGINS) == 2
