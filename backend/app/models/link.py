from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, Index
from sqlalchemy.orm import relationship
from ..database import Base


class Link(Base):
    """Short link model"""
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(20), unique=True, index=True, nullable=False)
    original_url = Column(String(2048), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)  # IP address or user_id
    clicks_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Relationship with clicks
    clicks = relationship("Click", back_populates="link", cascade="all, delete-orphan")

    # Index for case-insensitive search
    __table_args__ = (
        Index('idx_short_code_lower', func.lower(short_code)),
    )

    def __repr__(self):
        return f"<Link {self.short_code} -> {self.original_url}>"
