from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from ..database import Base


class Click(Base):
    """Click statistics model"""
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("links.id", ondelete="CASCADE"), nullable=False)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(512), nullable=True)
    referer = Column(String(512), nullable=True)

    # Relationship with link
    link = relationship("Link", back_populates="clicks")

    def __repr__(self):
        return f"<Click {self.id} for link {self.link_id}>"
