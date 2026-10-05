# agent/memory.py — Memoria de conversaciones y CRM
# Generado por AgentKit

"""
Sistema de memoria del agente y CRM. Guarda el historial de conversaciones,
el estado de la IA (pausa/activa), credenciales administrativas y soporta
SQLite y PostgreSQL de forma transparente.
"""

import os
import bcrypt
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Boolean, select, Integer
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")

# Ajuste automático del driver de base de datos si es PostgreSQL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UsuarioAdmin(Base):
    """Modelo para autenticación del panel CRM /admin."""
    __tablename__ = "usuarios_admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    debe_cambiar_password: Mapped[bool] = mapped_column(Boolean, default=True)


class ChatStatus(Base):
    """Modelo para almacenar el estado de pausa de la IA por número telefónico."""
    __tablename__ = "chat_status"

    telefono: Mapped[str] = mapped_column(String(50), primary_key=True)
    is_ai_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    ultima_actividad: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Mensaje(Base):
    """Modelo de mensaje extendido para auditar y soportar multimedia."""
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    mensaje_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" o "assistant"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Atributos multimedia
    url_media: Mapped[str] = mapped_column(Text, nullable=True)
    es_imagen: Mapped[bool] = mapped_column(Boolean, default=False)
    es_audio: Mapped[bool] = mapped_column(Boolean, default=False)
    es_documento: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Atributo de intervención humana
    enviado_por_admin: Mapped[bool] = mapped_column(Boolean, default=False)


async def inicializar_db():
    """Crea las tablas si no existen e inserta el administrador por defecto."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await crear_admin_por_defecto()


async def crear_admin_por_defecto():
    """Crea la cuenta admin/admin si no existe ningún usuario."""
    async with async_session() as session:
        query = select(UsuarioAdmin).where(UsuarioAdmin.username == "admin")
        result = await session.execute(query)
        admin = result.scalar_one_or_none()
        
        if not admin:
            salt = bcrypt.gensalt()
            pw_hash = bcrypt.hashpw(b"admin", salt).decode("utf-8")
            nuevo_admin = UsuarioAdmin(
                username="admin",
                password_hash=pw_hash,
                debe_cambiar_password=True
            )
            session.add(nuevo_admin)
            await session.commit()
            logger.info("Usuario administrador por defecto ('admin' / 'admin') creado.")


async def verificar_credenciales(username: str, password_plana: str) -> UsuarioAdmin | None:
    """Verifica si el usuario y contraseña son correctos."""
    async with async_session() as session:
        query = select(UsuarioAdmin).where(UsuarioAdmin.username == username)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            # Comparar el hash bcrypt
            if bcrypt.checkpw(password_plana.encode('utf-8'), user.password_hash.encode('utf-8')):
                return user
        return None


async def actualizar_password(username: str, nueva_password_plana: str):
    """Actualiza la contraseña del usuario administrador y desactiva el flag de cambio forzado."""
    async with async_session() as session:
        query = select(UsuarioAdmin).where(UsuarioAdmin.username == username)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            salt = bcrypt.gensalt()
            user.password_hash = bcrypt.hashpw(nueva_password_plana.encode('utf-8'), salt).decode("utf-8")
            user.debe_cambiar_password = False
            await session.commit()


async def obtener_usuario_admin(username: str) -> UsuarioAdmin | None:
    """Busca y retorna un usuario administrador por su nombre de usuario."""
    async with async_session() as session:
        query = select(UsuarioAdmin).where(UsuarioAdmin.username == username)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def es_mensaje_duplicado(mensaje_id: str) -> bool:
    """Retorna True si el mensaje_id ya existe en la base de datos (deduplicación)."""
    if not mensaje_id:
        return False
    async with async_session() as session:
        query = select(Mensaje).where(Mensaje.mensaje_id == mensaje_id)
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None


async def obtener_estado_chat(telefono: str) -> bool:
    """Retorna True si la IA está pausada para este número telefónico."""
    async with async_session() as session:
        query = select(ChatStatus).where(ChatStatus.telefono == telefono)
        result = await session.execute(query)
        status = result.scalar_one_or_none()
        return status.is_ai_paused if status else False


async def actualizar_estado_chat(telefono: str, pausar: bool):
    """Pausa o despausa la IA para un número telefónico."""
    async with async_session() as session:
        query = select(ChatStatus).where(ChatStatus.telefono == telefono)
        result = await session.execute(query)
        status = result.scalar_one_or_none()
        
        if status:
            status.is_ai_paused = pausar
            status.ultima_actividad = datetime.utcnow()
        else:
            status = ChatStatus(telefono=telefono, is_ai_paused=pausar, ultima_actividad=datetime.utcnow())
            session.add(status)
        await session.commit()


async def guardar_mensaje(
    telefono: str, 
    role: str, 
    content: str, 
    mensaje_id: str = None,
    url_media: str = None,
    es_imagen: bool = False,
    es_audio: bool = False,
    es_documento: bool = False,
    enviado_por_admin: bool = False
):
    """Guarda un mensaje en la BD y actualiza el timestamp de última actividad del chat."""
    async with async_session() as session:
        mensaje = Mensaje(
            telefono=telefono,
            mensaje_id=mensaje_id,
            role=role,
            content=content,
            url_media=url_media,
            es_imagen=es_imagen,
            es_audio=es_audio,
            es_documento=es_documento,
            enviado_por_admin=enviado_por_admin,
            timestamp=datetime.utcnow()
        )
        session.add(mensaje)
        
        # Actualizar actividad
        query = select(ChatStatus).where(ChatStatus.telefono == telefono)
        result = await session.execute(query)
        status = result.scalar_one_or_none()
        if status:
            status.ultima_actividad = datetime.utcnow()
        else:
            status = ChatStatus(telefono=telefono, is_ai_paused=False, ultima_actividad=datetime.utcnow())
            session.add(status)
            
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 30) -> list[dict]:
    """
    Recupera los últimos N mensajes de una conversación.
    
    Returns:
        Lista de diccionarios con la estructura de mensaje formateada.
    """
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        result = await session.execute(query)
        mensajes = result.scalars().all()
        mensajes.reverse()  # Orden cronológico (pasado -> presente)

        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "url_media": msg.url_media,
                "es_imagen": msg.es_imagen,
                "es_audio": msg.es_audio,
                "es_documento": msg.es_documento,
                "enviado_por_admin": msg.enviado_por_admin,
                "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
            for msg in mensajes
        ]


async def obtener_chats_activos() -> list[dict]:
    """Retorna una lista de todas las conversaciones ordenadas por última actividad."""
    async with async_session() as session:
        query = select(ChatStatus).order_by(ChatStatus.ultima_actividad.desc())
        result = await session.execute(query)
        statuses = result.scalars().all()
        
        chats = []
        for status in statuses:
            msg_query = (
                select(Mensaje)
                .where(Mensaje.telefono == status.telefono)
                .order_by(Mensaje.timestamp.desc())
                .limit(1)
            )
            msg_result = await session.execute(msg_query)
            ultimo_msg = msg_result.scalar_one_or_none()
            
            preview = ""
            es_imagen = False
            es_audio = False
            es_documento = False

            if ultimo_msg:
                es_imagen = bool(ultimo_msg.es_imagen)
                es_audio = bool(ultimo_msg.es_audio)
                es_documento = bool(ultimo_msg.es_documento)
                if es_imagen:
                    preview = "Imagen"
                elif es_audio:
                    preview = "Nota de voz"
                elif es_documento:
                    preview = "Documento"
                else:
                    preview = (ultimo_msg.content[:30] + "...") if len(ultimo_msg.content) > 30 else ultimo_msg.content
                    
            chats.append({
                "telefono": status.telefono,
                "is_ai_paused": status.is_ai_paused,
                "ultima_actividad": status.ultima_actividad.strftime("%d/%m %H:%M"),
                "preview": preview,
                "es_imagen": es_imagen,
                "es_audio": es_audio,
                "es_documento": es_documento
            })
            
        return chats


async def limpiar_historial(telefono: str):
    """Borra todo el historial de una conversación."""
    async with async_session() as session:
        query = select(Mensaje).where(Mensaje.telefono == telefono)
        result = await session.execute(query)
        mensajes = result.scalars().all()
        for msg in mensajes:
            session.delete(msg)
            
        status_query = select(ChatStatus).where(ChatStatus.telefono == telefono)
        status_res = await session.execute(status_query)
        status = status_res.scalar_one_or_none()
        if status:
            session.delete(status)
            
        await session.commit()
