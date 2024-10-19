import asyncio

async def handle_connection(reader, writer):
    addr = writer.get_extra_info("peername")

    while True:
        # Receive
        try:
            data = await reader.read(1024)
        except ConnectionError:
            print(f"Client suddenly closed while receiving from {addr}")
            break
        if not data:
            break

        print(addr, data)

        data = data.upper()
        try:
            writer.write(data)
        except ConnectionError:
            print(f"Client suddenly closed, cannot send")
            break

    writer.close()
    print("Disconnected by", addr)

async def main(host, port):
    server = await asyncio.start_server(handle_connection, host, port)
    async with server:
        await server.serve_forever()

HOST, PORT = "127.0.0.1", 7777

if __name__ == "__main__":
    asyncio.run(main(HOST, PORT))