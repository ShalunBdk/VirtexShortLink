from sqlalchemy import Column, Integer, String, Date, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base


class UniqueVisitor(Base):
    """Unique visitor tracking model for daily unique click counting"""
    __tablename__ = "unique_visitors"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("links.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    user_agent_hash = Column(String(64), nullable=False)  # SHA256 hash of User-Agent
    visit_date = Column(Date, nullable=False)
    first_click_id = Column(Integer, ForeignKey("clicks.id", ondelete="SET NULL"), nullable=True)

    # Relationship with link
    link = relationship("Link")

    # Unique constraint and index for fast lookup
    __table_args__ = (
        UniqueConstraint('link_id', 'ip_address', 'user_agent_hash', 'visit_date',
                        name='uix_unique_visitor'),
        Index('idx_unique_visitors_lookup', 'link_id', 'ip_address', 'user_agent_hash', 'visit_date'),
    )

    def __repr__(self):
        return f"<UniqueVisitor {self.id} for link {self.link_id} on {self.visit_date}>"
