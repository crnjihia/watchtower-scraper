from ..items import AngaliaItem, ProductItem
from .models import ChangeEvent


def diff(old_item: AngaliaItem | None, new_item: AngaliaItem | None) -> list[ChangeEvent]:
    """
    Pure diff function returning a list of ChangeEvent objects.

    Rules:
    - If old_item is None -> NEW
    - If new_item is None -> REMOVED
    - For ProductItem: price change triggers PRICE_DROP or PRICE_RISE
    - For other non-base field changes -> UPDATED
    """
    events: list[ChangeEvent] = []

    if old_item is None and new_item is not None:
        new_payload = new_item.to_dict() if hasattr(new_item, "to_dict") else new_item
        events.append(
            ChangeEvent(
                type="NEW",
                source=new_item.source,
                external_id=new_item.external_id,
                field=None,
                old=None,
                new=new_payload,
                url=new_item.url,
            )
        )
        return events

    if new_item is None and old_item is not None:
        old_payload = old_item.to_dict() if hasattr(old_item, "to_dict") else old_item
        events.append(
            ChangeEvent(
                type="REMOVED",
                source=old_item.source,
                external_id=old_item.external_id,
                field=None,
                old=old_payload,
                new=None,
                url=old_item.url,
            )
        )
        return events

    if old_item is None and new_item is None:
        return events

    # Handled price separately for products
    handled_fields: set[str] = {"source", "external_id", "url", "scraped_at", "content_hash"}

    if isinstance(old_item, ProductItem) and isinstance(new_item, ProductItem):
        handled_fields.add("price")
        if old_item.price != new_item.price:
            price_type = "PRICE_DROP" if new_item.price < old_item.price else "PRICE_RISE"
            events.append(
                ChangeEvent(
                    type=price_type,
                    source=new_item.source,
                    external_id=new_item.external_id,
                    field="price",
                    old=old_item.price,
                    new=new_item.price,
                    url=new_item.url,
                )
            )

    # Compare remaining fields
    all_fields = set(getattr(new_item, "__dataclass_fields__", {}).keys())
    compare_fields = sorted(list(all_fields - handled_fields))

    for field_name in compare_fields:
        old_val = getattr(old_item, field_name, None)
        new_val = getattr(new_item, field_name, None)
        if old_val != new_val:
            events.append(
                ChangeEvent(
                    type="UPDATED",
                    source=new_item.source,
                    external_id=new_item.external_id,
                    field=field_name,
                    old=old_val,
                    new=new_val,
                    url=new_item.url,
                )
            )

    return events
