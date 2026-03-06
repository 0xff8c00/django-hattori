from typing import Annotated, Any

from hattori import Response

weapons = ["Ninjato", "Shuriken", "Katana", "Kama", "Kunai", "Naginata", "Yari"]


@api.get("/weapons/search")
def search_weapons(request, q: str, offset: int = 0) -> Annotated[Response[Any], 200]:
    results = [w for w in weapons if q in w.lower()]
    return Response(200, results[offset : offset + 10])
