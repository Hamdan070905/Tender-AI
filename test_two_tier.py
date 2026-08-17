import sys, asyncio
sys.path.insert(0, "backend")
from connectors.cppp import CPPPConnector
from connectors.gem import GeMConnector
from connectors.state_eprocurement import build_state_connectors
from connectors.private_sector import PrivateSectorConnector

async def main():
    # Test CPPP
    print("=" * 60)
    c = CPPPConnector()
    async with c:
        r = await c.search(["3D Concrete"])
        print(f"CPPP results: {len(r)}")
        for t in r[:3]:
            print(f"  [{t.source_id}] {t.title[:80]}")
            print(f"    org={t.organization}, deadline={t.deadline}")

    # Test GeM
    print("\n" + "=" * 60)
    g = GeMConnector()
    async with g:
        r = await g.search(["concrete"])
        print(f"GeM results: {len(r)}")
        for t in r[:3]:
            print(f"  [{t.source_id}] {t.title[:80]}")

    # Test Maharashtra state
    print("\n" + "=" * 60)
    states = build_state_connectors()
    s = states[0]  # Maharashtra
    async with s:
        r = await s.search(["concrete"])
        print(f"{s.source_id} results: {len(r)}")
        for t in r[:3]:
            print(f"  [{t.source_id}] {t.title[:80]}")

    # Test Private Sector
    print("\n" + "=" * 60)
    p = PrivateSectorConnector()
    async with p:
        r = await p.search(["construction"])
        print(f"Private Sector results: {len(r)}")
        for t in r[:3]:
            print(f"  [{t.source_id}] {t.title[:80]}")

asyncio.run(main())
