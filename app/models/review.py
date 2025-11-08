from sqlalchemy import Column, BigInteger, Text, SmallInteger, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(BigInteger, primary_key=True, index=True)
    servicio_id = Column(BigInteger, ForeignKey('servicios.id'), nullable=False, index=True)
    usuario_id = Column(BigInteger, nullable=False)
    comentario = Column(Text, nullable=False)
    calificacion = Column(SmallInteger, nullable=False)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    
    # Relación con Servicio
    servicio = relationship("Servicio", back_populates="reviews")
