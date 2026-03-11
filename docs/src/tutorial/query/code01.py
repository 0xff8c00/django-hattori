from typing import Annotated

from hattori import Response

weapons = ["Ninjato", "Shuriken", "Katana", "Kama", "Kunai", "Naginata", "Yari"]


@api.get("/weapons")
def list_weapons(
    request, limit: int = 10, offset: int = 0
) -> Annotated[Response[list[str]], 200]:
    return Response(200, weapons[offset : offset + limit])
