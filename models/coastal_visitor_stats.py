from sqlalchemy import Column, BigInteger, String, Integer, UniqueConstraint
from core.database import Base


class CoastalVisitorStats(Base):
    __tablename__ = "coastal_visitor_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    region = Column(String(20), nullable=False)
    year_month = Column(String(7), nullable=False)  # YYYY-MM 형식
    visitor = Column(Integer, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('region', 'year_month', name='uk_region_month'),
    )
