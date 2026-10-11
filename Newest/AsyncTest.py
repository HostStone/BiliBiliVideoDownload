import asyncio

sem = asyncio.BoundedSemaphore(1)

async def out():
    async with sem:
        print("hello from out1")
        await asyncio.sleep(1)

async def out2():
    async with sem:
        print("hello from out2")
        await asyncio.sleep(1)

async def main():
    print("hello from main")
    # await asyncio.sleep(1)
    queue = [out(), out2()]
    await asyncio.gather(*queue)
    pass

print("a")
asyncio.run(main())
# asyncio.run(out())
print("b")