from sqlalchemy import Column, Integer, String, DateTime, func
from ..database import Base


class IPBlacklist(Base):
    """IP blacklist model for spam protection"""
    __tablename__ = "ip_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, index=True, nullable=False)
    reason = Column(String(255), nullable=True)
    blocked_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<IPBlacklist {self.ip_address}>"
