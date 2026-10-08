import uuid

from sqlalchemy import update

from app.models.user import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return await self.get_by(token_hash=token_hash)

    async def revoke_if_active(self, token_id: uuid.UUID) -> bool:
        """Atomically revoke a token; False when it was already revoked (guards against concurrent reuse)."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        return result.rowcount == 1

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(stmt)
