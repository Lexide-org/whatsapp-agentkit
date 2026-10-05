# tests/test_local.py — Simulador de chat en terminal
# Generado por AgentKit

"""
Prueba tu agente sin necesitar WhatsApp.
Simula una conversación en la terminal y actualiza las respuestas de la IA
y de las intervenciones del administrador en tiempo real desde el CRM.
"""

import asyncio
import sys
import os
from sqlalchemy import select

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import (
    inicializar_db, 
    guardar_mensaje, 
    obtener_historial, 
    limpiar_historial, 
    obtener_estado_chat,
    async_session,
    Mensaje
)

TELEFONO_TEST = "test-local-001"


def pedir_input(prompt: str) -> str:
    """Función bloqueante para ejecutar en executor."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "salir"


async def obtener_input_async(prompt: str) -> str:
    """Obtiene input de consola de forma asíncrona sin bloquear el loop de asyncio."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pedir_input, prompt)


async def monitorear_mensajes_nuevos(ultimo_id_ref):
    """Tarea de fondo que escucha si Gemini o el Administrador responden en el CRM."""
    while True:
        await asyncio.sleep(1.5)
        try:
            async with async_session() as session:
                query = (
                    select(Mensaje)
                    .where(Mensaje.telefono == TELEFONO_TEST)
                    .where(Mensaje.id > ultimo_id_ref[0])
                    .order_by(Mensaje.id.asc())
                )
                result = await session.execute(query)
                mensajes_nuevos = result.scalars().all()
                
                for msg in mensajes_nuevos:
                    if msg.role == "assistant":
                        prefijo = "Admin" if msg.enviado_por_admin else "Agente"
                        print(f"\n\n{prefijo}: {msg.content}")
                        print("\nTu: ", end="", flush=True)
                    ultimo_id_ref[0] = msg.id
        except Exception:
            pass


async def main():
    """Loop principal del chat de prueba."""
    await inicializar_db()

    print()
    print("=" * 55)
    print("   AgentKit — Test Local")
    print("=" * 55)
    print()
    print("  Escribe mensajes como si fueras un cliente.")
    print("  Comandos especiales:")
    print("    'limpiar'  — borra el historial")
    print("    'salir'    — termina el test")
    print()
    print("-" * 55)
    print()

    # Obtener el ID del último mensaje actual para no repetir el historial en pantalla
    ultimo_id_ref = [0]
    async with async_session() as session:
        query = select(Mensaje.id).where(Mensaje.telefono == TELEFONO_TEST).order_by(Mensaje.id.desc()).limit(1)
        res = await session.execute(query)
        val = res.scalar_one_or_none()
        if val:
            ultimo_id_ref[0] = val

    # Arrancar tarea en segundo plano para escuchar al administrador
    task_monitoreo = asyncio.create_task(monitorear_mensajes_nuevos(ultimo_id_ref))

    try:
        while True:
            mensaje = await obtener_input_async("Tu: ")

            if not mensaje or mensaje == "":
                continue

            if mensaje.lower() == "salir":
                print("\nTest finalizado.")
                break

            if mensaje.lower() == "limpiar":
                await limpiar_historial(TELEFONO_TEST)
                ultimo_id_ref[0] = 0
                print("[Historial borrado]\n")
                continue

            # 1. Guardar mensaje del usuario inmediatamente
            await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
            
            # Actualizar la referencia del último mensaje visto
            async with async_session() as session:
                query = select(Mensaje.id).where(Mensaje.telefono == TELEFONO_TEST).order_by(Mensaje.id.desc()).limit(1)
                res = await session.execute(query)
                val = res.scalar_one_or_none()
                if val:
                    ultimo_id_ref[0] = val

            # 2. Verificar si el chat tiene la IA pausada (CRM /admin)
            is_paused = await obtener_estado_chat(TELEFONO_TEST)
            if is_paused:
                print("\n[IA PAUSADA] Mensaje registrado en el CRM. Esperando respuesta manual de un admin...\n")
                continue

            # 3. Obtener historial (los últimos 30 mensajes para Gemini)
            historial = await obtener_historial(TELEFONO_TEST, limite=30)

            # 4. Generar respuesta
            print("\nAgente: ", end="", flush=True)
            respuesta = await generar_respuesta(mensaje, historial)
            print(respuesta)
            print()

            # 5. Guardar respuesta de la IA
            await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)
            
            async with async_session() as session:
                query = select(Mensaje.id).where(Mensaje.telefono == TELEFONO_TEST).order_by(Mensaje.id.desc()).limit(1)
                res = await session.execute(query)
                val = res.scalar_one_or_none()
                if val:
                    ultimo_id_ref[0] = val

    finally:
        # Cancelar el monitoreo al salir
        task_monitoreo.cancel()


if __name__ == "__main__":
    asyncio.run(main())
