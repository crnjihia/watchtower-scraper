import os
from datetime import UTC, datetime
from typing import Any

import structlog
from jinja2 import Template

logger = structlog.get_logger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("EMAIL_FROM", "alerts@watchtower.io")
TO_EMAIL = os.getenv("EMAIL_TO", "user@example.com")

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Watchtower Daily Digest</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 20px; color: #333; }
    h2 { color: #1a365d; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
    p.summary { font-size: 15px; color: #4a5568; margin-bottom: 20px; }
    table { border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 14px; }
    th, td { border: 1px solid #cbd5e0; padding: 10px 12px; text-align: left; }
    th { background-color: #f7fafc; color: #2d3748; font-weight: 600; }
    tr:nth-child(even) { background-color: #f8fafc; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .badge-new { background-color: #c6f6d5; color: #22543d; }
    .badge-price-drop { background-color: #feebc8; color: #7b341e; }
    .badge-price-rise { background-color: #fed7d7; color: #742a2a; }
    .badge-updated { background-color: #e2e8f0; color: #2d3748; }
    .badge-removed { background-color: #edf2f7; color: #718096; }
    a.item-link { color: #3182ce; text-decoration: none; font-weight: 500; }
    a.item-link:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h2>Watchtower Daily Digest — {{ date }}</h2>
  <p class="summary"><strong>Summary:</strong> {{ summary }}</p>
  <table>
    <thead>
      <tr>
        <th>Source</th>
        <th>Type</th>
        <th>Item</th>
        <th>Change</th>
        <th>Link</th>
      </tr>
    </thead>
    <tbody>
    {% for ev in events %}
      <tr>
        <td><strong>{{ ev.source|title }}</strong></td>
        <td>
          <span class="badge badge-{{ ev.type|lower|replace('_', '-') }}">{{ ev.type }}</span>
        </td>
        <td>
          {% if ev.new and ev.new.title %}
            {{ ev.new.title }}
          {% elif ev.new and ev.new.name %}
            {{ ev.new.name }}
          {% elif ev.title %}
            {{ ev.title }}
          {% elif ev.name %}
            {{ ev.name }}
          {% else %}
            {{ ev.field or "item" }}
          {% endif %}
        </td>
        <td>
          {% if ev.type in ["PRICE_DROP", "PRICE_RISE"] %}
            <strong>{{ ev.old }}</strong> → <strong>{{ ev.new }}</strong>
          {% elif ev.type == "UPDATED" %}
            <em>{{ ev.field }}:</em> {{ ev.old }} → {{ ev.new }}
          {% elif ev.type == "NEW" %}
            New listing detected
          {% else %}
            {{ ev.type|lower }}
          {% endif %}
        </td>
        <td><a class="item-link" href="{{ ev.url }}" target="_blank">View Item</a></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""


def build_subject_and_summary(events: list[dict[str, Any]]) -> tuple[str, str]:
    """Generate dynamic subject and summary counts from events."""
    new_jobs = sum(
        1
        for e in events
        if e.get("type") == "NEW"
        and e.get("source") in ("brightermonday", "fuzu", "myjobmag")
    )
    price_drops = sum(1 for e in events if e.get("type") == "PRICE_DROP")
    new_products = sum(
        1
        for e in events
        if e.get("type") == "NEW"
        and e.get("source") in ("jumia", "kilimall")
    )
    price_rises = sum(1 for e in events if e.get("type") == "PRICE_RISE")
    updates = sum(1 for e in events if e.get("type") == "UPDATED")

    parts = []
    if new_jobs:
        parts.append(f"{new_jobs} new job{'s' if new_jobs != 1 else ''}")
    if price_drops:
        parts.append(f"{price_drops} price drop{'s' if price_drops != 1 else ''}")
    if new_products:
        parts.append(f"{new_products} new product{'s' if new_products != 1 else ''}")
    if price_rises:
        parts.append(f"{price_rises} price rise{'s' if price_rises != 1 else ''}")
    if updates:
        parts.append(f"{updates} update{'s' if updates != 1 else ''}")

    if not parts:
        desc = f"{len(events)} changes"
    else:
        desc = ", ".join(parts)

    subject = f"Watchtower Daily: {desc}"
    summary = f"{len(events)} total events recorded ({desc})"
    return subject, summary


def render_html(events: list[dict[str, Any]]) -> str:
    """Render HTML email body using Jinja2."""
    normalized = [e.to_dict() if hasattr(e, "to_dict") else e for e in events]
    _, summary = build_subject_and_summary(normalized)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")

    tmpl = Template(HTML_TEMPLATE)
    return tmpl.render(date=date_str, summary=summary, events=normalized)


def send_email_digest(events: list[Any], check_dedup: bool = True) -> str | None:
    """
    Format and send SendGrid daily digest email.
    Deduplicates events and logs to alerts_sent.
    """
    if not events:
        logger.info("no_events_for_email_digest")
        return None

    normalized = [e.to_dict() if hasattr(e, "to_dict") else e for e in events]

    if check_dedup:
        from .telegram import _filter_dedup_events, _record_alerts_sent
        to_send = _filter_dedup_events(normalized)
    else:
        to_send = normalized

    if not to_send:
        logger.info("no_email_events_after_dedup")
        return None

    subject, _ = build_subject_and_summary(to_send)
    html_content = render_html(to_send)

    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        logger.info("sendgrid_skipped_no_api_key", subject=subject, count=len(to_send))
        return html_content

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=TO_EMAIL,
            subject=subject,
            html_content=html_content,
        )
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info(
            "sendgrid_email_sent",
            status_code=response.status_code,
            subject=subject,
            count=len(to_send),
        )

        if check_dedup:
            from .telegram import _record_alerts_sent
            _record_alerts_sent(to_send)

        return html_content
    except Exception as exc:
        logger.error("sendgrid_send_error", error=str(exc))
        return html_content
