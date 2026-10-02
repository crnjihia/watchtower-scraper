import os
import structlog
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

log = structlog.get_logger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("EMAIL_FROM", "alerts@angalia.io")
TO_EMAIL = os.getenv("EMAIL_TO", "user@example.com")

# Inline template – keep repository tidy without external files
TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <style>
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; }}
    th {{ background-color: #f2f2f2; }}
  </style>
</head>
<body>
  <h2>Angalia Daily Digest – {{ date }}</h2>
  <p>{{ summary }}</p>
  <table>
    <thead>
      <tr>
        <th>Source</th><th>Type</th><th>Item</th><th>Change</th><th>Link</th>
      </tr>
    </thead>
    <tbody>
    {% for ev in events %}
      <tr>
        <td>{{ ev.source }}</td>
        <td>{{ ev.type }}</td>
        <td>{{ ev.field or "item" }}</td>
        <td>
          {% if ev.type in ["PRICE_DROP", "PRICE_RISE"] %}
            {{ ev.old }} → {{ ev.new }}
          {% elif ev.type == "UPDATED" %}
            {{ ev.old }} → {{ ev.new }}
          {% else %}
            {{ ev.type|lower }}
          {% endif %}
        </td>
        <td><a href="{{ ev.url }}">link</a></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""

env = Environment(
    loader=FileSystemLoader(searchpath=os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_html(events):
    tmpl = env.from_string(TEMPLATE)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    summary = f"{len([e for e in events if e['type']=='NEW'])} new items, " \
              f"{len([e for e in events if e['type']=='PRICE_DROP'])} price drops"
    return tmpl.render(date=date_str, summary=summary, events=events)


def send_email_digest(events):
    if not SENDGRID_API_KEY:
        log.warning("SendGrid API key missing – email digest disabled")
        return

    html_content = render_html(events)
    subject = f"Angalia Daily: {len(events)} changes"

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject=subject,
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        log.info(
            "email_sent",
            status_code=response.status_code,
            body=response.body,
            headers=response.headers,
        )
    except Exception as exc:
        log.error("sendgrid_error", error=str(exc))
