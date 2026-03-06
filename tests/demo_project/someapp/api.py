from datetime import date
from typing import Annotated

from django.shortcuts import get_object_or_404
from pydantic import BaseModel

from hattori import Response, Router

from .models import Event

router = Router()


class EventSchema(BaseModel):
    model_config = dict(from_attributes=True)

    title: str
    start_date: date
    end_date: date


@router.post("/create", url_name="event-create-url-name")
def create_event(request, event: EventSchema) -> Annotated[Response[EventSchema], 200]:
    Event.objects.create(**event.model_dump())
    return Response(200, event)


@router.get("")
def list_events(request) -> Annotated[Response[list[EventSchema]], 200]:
    return Response(200, list(Event.objects.all()))


@router.delete("")
def delete_events(request) -> Annotated[Response[None], 204]:
    Event.objects.all().delete()
    return Response(204, None)


@router.get("/{id}")
def get_event(request, id: int) -> Annotated[Response[EventSchema], 200]:
    event = get_object_or_404(Event, id=id)
    return Response(200, event)
