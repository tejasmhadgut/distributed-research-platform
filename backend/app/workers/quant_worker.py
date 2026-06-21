import asyncio
import json
import aio_pika
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.quant_service import compute_quant


async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        ticker = body.get("ticker", "").upper()
        print(f"[quant_worker] computing quant for {ticker}")

        async with AsyncSessionLocal() as db:
            try:
                result = await compute_quant(db, ticker)
                print(f"[quant_worker] done: {result.metrics}")
            except Exception as e:
                print(f"[quant_worker] error: {e}")


async def main():
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    queue = await channel.declare_queue("quant_tasks", durable=True)
    print("[quant_worker] waiting for quant_tasks...")
    await queue.consume(handle_message)
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
