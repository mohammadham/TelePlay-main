"""Unit tests for JWT auth utilities."""
import pytest
from jose import jwt, JWTError
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_settings():
    from app.config import get_settings
    s = get_settings()
    s.jwt_secret = "test-jwt-secret-for-unit-tests-only"
    s.jwt_expiry_minutes = 60
    return s


class TestCreateAccessToken:
    def test_returns_string(self, mock_settings):
        from app.auth import create_access_token
        token = create_access_token(12345)
        assert isinstance(token, str)
        assert len(token) > 10

    def test_payload_contains_sub(self, mock_settings):
        from app.auth import create_access_token
        token = create_access_token(12345)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=["HS256"])
        assert payload["sub"] == "12345"

    def test_payload_type_is_access(self, mock_settings):
        from app.auth import create_access_token
        token = create_access_token(12345)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=["HS256"])
        assert payload["type"] == "access"

    def test_payload_contains_is_admin_true(self, mock_settings):
        from app.auth import create_access_token
        token = create_access_token(12345, is_admin=True)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=["HS256"])
        assert payload["is_admin"] is True

    def test_payload_contains_is_admin_false_default(self, mock_settings):
        from app.auth import create_access_token
        token = create_access_token(12345)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=["HS256"])
        assert payload["is_admin"] is False

    def test_payload_has_version(self, mock_settings):
        from app.auth import create_access_token
        token = create_access_token(12345, version=2)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=["HS256"])
        assert payload["ver"] == 2

    def test_different_ids_produce_different_tokens(self, mock_settings):
        from app.auth import create_access_token
        t1 = create_access_token(111)
        t2 = create_access_token(222)
        assert t1 != t2


class TestCreateRefreshToken:
    def test_returns_string(self, mock_settings):
        from app.auth import create_refresh_token
        token = create_refresh_token(12345)
        assert isinstance(token, str)

    def test_payload_type_is_refresh(self, mock_settings):
        from app.auth import create_refresh_token
        token = create_refresh_token(12345)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=["HS256"])
        assert payload["type"] == "refresh"


class TestCreateShortLivedToken:
    def test_expiry_is_15_minutes(self, mock_settings):
        from app.auth import create_short_lived_token
        token = create_short_lived_token(12345, minutes=15)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=["HS256"])
        import datetime
        exp = payload["exp"]
        now = datetime.datetime.utcnow().timestamp()
        diff = exp - now
        assert 899 <= diff <= 901  # ~15 minutes in seconds

    def test_is_admin_always_false(self, mock_settings):
        from app.auth import create_short_lived_token
        token = create_short_lived_token(12345)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=["HS256"])
        assert payload["is_admin"] is False


class TestVerifyToken:
    def test_valid_token_returns_id(self, mock_settings):
        from app.auth import create_access_token, verify_token
        token = create_access_token(99999)
        result = verify_token(token)
        assert result == 99999

    def test_expired_token_returns_none(self, mock_settings):
        from jose import jwt
        from app.auth import verify_token
        expired = jwt.encode(
            {"sub": "1", "exp": 0, "type": "access", "ver": 0, "is_admin": False},
            "test-jwt-secret-for-unit-tests-only",
            algorithm="HS256"
        )
        assert verify_token(expired) is None

    def test_wrong_secret_returns_none(self, mock_settings):
        from app.auth import create_access_token, verify_token
        token = create_access_token(12345)
        # tamper with token
        parts = token.split(".")
        parts[2] = "fake_signature"
        tampered = ".".join(parts)
        assert verify_token(tampered) is None

    def test_null_sub_returns_none(self, mock_settings):
        from app.auth import verify_token
        bad = jwt.encode(
            {"sub": None, "exp": 9999999999, "type": "access", "ver": 0},
            "test-jwt-secret-for-unit-tests-only",
            algorithm="HS256"
        )
        assert verify_token(bad) is None

    def test_non_numeric_sub_returns_none(self, mock_settings):
        from jose import jwt
        from app.auth import verify_token
        bad = jwt.encode(
            {"sub": "abc", "exp": 9999999999, "type": "access", "ver": 0},
            "test-jwt-secret-for-unit-tests-only",
            algorithm="HS256"
        )
        assert verify_token(bad) is None


class TestVerifyTokenPayload:
    def test_valid_access_returns_payload(self, mock_settings):
        from app.auth import create_access_token, verify_token_payload
        token = create_access_token(12345)
        payload = verify_token_payload(token, "access")
        assert payload is not None
        assert payload["sub"] == "12345"

    def test_refresh_token_rejected_for_access(self, mock_settings):
        from app.auth import create_refresh_token, verify_token_payload
        token = create_refresh_token(12345)
        payload = verify_token_payload(token, "access")
        assert payload is None

    def test_invalid_token_returns_none(self, mock_settings):
        from app.auth import verify_token_payload
        assert verify_token_payload("not-a-token") is None

    def test_empty_string_returns_none(self, mock_settings):
        from app.auth import verify_token_payload
        assert verify_token_payload("") is None


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_returns_user_from_db(self):
        from app.auth import get_current_user
        from app.models import User
        from datetime import datetime

        mock_user = User(
            id=1, telegram_id=12345, username="testuser",
            first_name="Test", last_name="User",
            auth_version=0, created_at=datetime.utcnow(), last_active=datetime.utcnow()
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_credentials = MagicMock()
        mock_credentials.credentials = "dummy-token"

        with patch("app.auth.verify_token_payload") as mock_verify, \
             patch("app.auth.get_db") as mock_get_db, \
             patch("app.auth.get_settings") as mock_settings:

            mock_settings.return_value.jwt_expiry_minutes = 60
            mock_verify.return_value = {"sub": "12345", "exp": 9999999999, "type": "access", "ver": 0, "is_admin": False}
            mock_get_db.return_value = mock_session

            from app.auth import create_access_token
            real_token = create_access_token(12345)

            result = await get_current_user(
                credentials=MagicMock(credentials=real_token),
                db=mock_session
            )
            assert result.telegram_id == 12345
            assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_missing_token_raises_401(self):
        from fastapi import HTTPException
        from app.auth import get_current_user

        mock_session = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=None,
                db=mock_session
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        from fastapi import HTTPException
        from app.auth import get_current_user

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.auth.verify_token_payload") as mock_verify, \
             patch("app.auth.get_db") as mock_get_db:

            mock_verify.return_value = {"sub": "999", "exp": 9999999999, "type": "access", "ver": 0}
            mock_get_db.return_value = mock_session

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    credentials=MagicMock(credentials="bad-token"),
                    db=mock_session
                )
            assert exc_info.value.status_code == 401


class TestRequireAdmin:
    @pytest.mark.asyncio
    async def test_admin_in_db_passes(self):
        from app.auth import require_admin
        from app.models import User, AdminUser
        from datetime import datetime

        mock_user = User(id=1, telegram_id=1, username="admin", auth_version=0)
        mock_admin = AdminUser(id=1, telegram_id=1, role="SUPER_ADMIN", is_active=True)

        mock_session = MagicMock()
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_admin_result = MagicMock()
        mock_admin_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_admin])))

        async def fake_execute(stmt):
            if "admin_users" in str(stmt):
                return mock_admin_result
            return mock_user_result

        mock_session.execute = AsyncMock(side_effect=fake_execute)

        result = await require_admin(current_user=mock_user, db=mock_session)
        assert result.telegram_id == 1

    @pytest.mark.asyncio
    async def test_non_admin_raises_403(self):
        from fastapi import HTTPException
        from app.auth import require_admin
        from app.models import User
        from datetime import datetime

        mock_user = User(id=1, telegram_id=999, username="regular", auth_version=0)
        mock_admin = AdminUser(id=1, telegram_id=1, role="SUPER_ADMIN", is_active=True)

        mock_session = MagicMock()
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_admin_result = MagicMock()
        mock_admin_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_admin])))

        async def fake_execute(stmt):
            if "admin_users" in str(stmt):
                return mock_admin_result
            return mock_user_result

        mock_session.execute = AsyncMock(side_effect=fake_execute)

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user=mock_user, db=mock_session)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_admins_configured_dev_mode_allows(self):
        from app.auth import require_admin
        from app.models import User
        from datetime import datetime

        mock_user = User(id=1, telegram_id=1, username="anyone", auth_version=0)
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        async def fake_execute(stmt):
            if "admin_users" in str(stmt):
                return mock_result
            return mock_result

        mock_session.execute = AsyncMock(side_effect=fake_execute)

        result = await require_admin(current_user=mock_user, db=mock_session)
        assert result.telegram_id == 1
