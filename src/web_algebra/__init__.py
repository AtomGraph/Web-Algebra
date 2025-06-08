from .server import serve


def main_serve():
    import asyncio
    asyncio.run(serve())


if __name__ == "__main__":
    main_serve()
