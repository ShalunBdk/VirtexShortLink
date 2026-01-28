from sqlalchemy import Column, Integer, String, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base


class BitrixUser(Base):
    """Bitrix24 user model for personal cabinet integration"""
    __tablename__ = "bitrix_users"

    id = Column(Integer, primary_key=True, index=True)
    bitrix_user_id = Column(String(50), nullable=False)  # User ID from Bitrix24
    bitrix_domain = Column(String(255), nullable=False)  # Portal domain
    name = Column(String(255), nullable=True)  # User display name
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship with links
    links = relationship("Link", back_populates="owner", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('bitrix_user_id', 'bitrix_domain', name='uix_bitrix_user_domain'),
    )

    def __repr__(self):
        return f"<BitrixUser {self.bitrix_user_id}@{self.bitrix_domain}>"
