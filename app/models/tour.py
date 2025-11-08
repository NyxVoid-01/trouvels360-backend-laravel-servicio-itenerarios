from sqlalchemy import Column, BigInteger, String, Enum, Date, SmallInteger, DECIMAL, JSON, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base


class Tour(Base):
    __tablename__ = "tours"
    
    servicio_id = Column(BigInteger, ForeignKey('servicios.id'), primary_key=True)
    categoria = Column(Enum('Gastronomía', 'Aventura', 'Cultura', 'Relajación'), nullable=False)
    fecha = Column(Date, nullable=False)
    duracion = Column(SmallInteger, nullable=True)
    precio = Column(DECIMAL(10, 2), nullable=False)
    cupos = Column(SmallInteger, nullable=True)
    cosas_para_llevar = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    
    # Relación con Servicio
    servicio = relationship("Servicio", back_populates="tour")


class TourActividad(Base):
    __tablename__ = "tour_actividades"
    
    id = Column(BigInteger, primary_key=True, index=True)
    servicio_id = Column(BigInteger, ForeignKey('servicios.id'), nullable=False, index=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(String, nullable=True)
    orden = Column(SmallInteger, nullable=False, default=1)
    duracion_min = Column(SmallInteger, nullable=True)
    direccion = Column(String(255), nullable=True)
    imagen_url = Column(String(500), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    
    # Relación con Servicio
    servicio = relationship("Servicio", back_populates="tour_actividades")
