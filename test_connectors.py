import sys
import asyncio

sys.path.insert(0, "backend")

from connectors.gem import GeMConnector
from connectors.psu import build_psu_connectors

async def main():
    gem = GeMConnector()
    gem_res = await gem.search(["3d", "concrete"])
    print("GeM Tenders:", len(gem_res))

    psus = build_psu_connectors()
    total_psu = 0
    for psu in psus[:4]:
        res = await psu.search(["3d", "concrete"])
        print(f"PSU {psu.source_id}:", len(res))
        total_psu += len(res)
    print("Total PSU Tenders:", total_psu)

if __name__ == "__main__":
    asyncio.run(main())
