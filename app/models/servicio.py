from sqlalchemy import Column, BigInteger, String, Enum, Text, DECIMAL, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base


class Servicio(Base):
    __tablename__ = "servicios"
    
    id = Column(BigInteger, primary_key=True, index=True)
    proveedor_id = Column(BigInteger, nullable=False)
    nombre = Column(String(150), nullable=False)
    tipo = Column(Enum('hotel', 'tour'), nullable=False)
    descripcion = Column(Text, nullable=True)
    ciudad = Column(String(100), nullable=False, index=True)
    pais = Column(String(100), nullable=False)
    latitud = Column(DECIMAL(10, 6), nullable=True)
    longitud = Column(DECIMAL(10, 6), nullable=True)
    imagen_url = Column(String(500), nullable=True)
    activo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    
    # Relaciones
    hotel = relationship("Hotel", back_populates="servicio", uselist=False)
    tour = relationship("Tour", back_populates="servicio", uselist=False)
    reviews = relationship("Review", back_populates="servicio")
    tour_actividades = relationship("TourActividad", back_populates="servicio")


class Hotel(Base):
    __tablename__ = "hoteles"
    
    servicio_id = Column(BigInteger, ForeignKey('servicios.id'), primary_key=True)
    direccion = Column(String(255), nullable=False)
    estrellas = Column(BigInteger, nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    
    # Relación con Servicio
    servicio = relationship("Servicio", back_populates="hotel")
