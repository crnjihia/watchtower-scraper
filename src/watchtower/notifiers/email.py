"""Email notification provider via SendGrid with HTML table & diff snippets."""

from typing import List, Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail, To

from watchtower.config import get_settings
from watchtower.logging import get_logger
from watchtower.schemas.alert import AlertPayload

logger = get_logger(__name__)


class EmailNotifier:
    """Sends batched alerts formatted as responsive HTML emails."""

    name = "email"

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        to_emails: Optional[List[str]] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.SENDGRID_API_KEY
        self.from_email = from_email or settings.ALERT_FROM_EMAIL
        self.to_emails = to_emails or settings.ALERT_TO_EMAILS

    def is_configured(self) -> bool:
        """Check if SendGrid API key and recipient emails are present."""
        return bool(self.api_key and self.to_emails and self.from_email)

    def send(self, payloads: List[AlertPayload]) -> bool:
        """Batch all events into a single HTML email with a table and diff snippets."""
        if not self.is_configured():
            logger.info("email_skipped_not_configured")
            return False

        if not payloads:
            return True

        subject = f"[Watchtower Alert] {len(payloads)} Changes Detected"
        html_body = self._render_html_table(payloads)

        try:
            sg = SendGridAPIClient(self.api_key)
            from_sender = Email(self.from_email, name="Watchtower Scraper")
            content = Content("text/html", html_body)

            success = True
            for recipient in self.to_emails:
                to_email = To(recipient)
                mail = Mail(from_sender, to_email, subject, content)
                response = sg.client.mail.send.post(request_body=mail.get())
                if response.status_code not in (200, 201, 202):
                    logger.error("sendgrid_send_error", status_code=response.status_code, to=recipient)
                    success = False
                else:
                    logger.info("sendgrid_email_sent", to=recipient)

            return success
        except Exception as e:
            logger.exception("sendgrid_send_exception", error=str(e))
            return False

    def _render_html_table(self, payloads: List[AlertPayload]) -> str:
        """Generate clean, responsive HTML email markup."""
        rows = []
        for p in payloads:
            diff_text = "—"
            if p.diff:
                if "old" in p.diff and "new" in p.diff:
                    old_p = f"KES {p.diff['old']:,.2f}" if p.diff["old"] else "N/A"
                    new_p = f"KES {p.diff['new']:,.2f}" if p.diff["new"] else "N/A"
                    pct = f"{p.diff.get('pct', 0.0):.1f}%"
                    diff_text = f"<b>{old_p}</b> ➔ <b>{new_p}</b> ({pct})"
                elif "price_kes" in p.diff and p.diff["price_kes"]:
                    diff_text = f"KES {p.diff['price_kes']:,.2f}"

            kind_color = {
                "new_listing": "#2563eb",
                "price_drop": "#16a34a",
                "price_increase": "#dc2626",
                "removed": "#64748b",
            }.get(p.kind, "#475569")

            row_html = f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px; font-weight: bold; color: {kind_color};">
                    {p.kind.replace('_', ' ').upper()}
                </td>
                <td style="padding: 10px; text-transform: capitalize;">{p.site}</td>
                <td style="padding: 10px;">
                    <a href="{p.url}" style="color: #2563eb; text-decoration: none; font-weight: 500;">
                        {p.title}
                    </a>
                    {f'<br><span style="color:#64748b;font-size:12px;">{p.company}</span>' if p.company else ''}
                </td>
                <td style="padding: 10px; font-size: 13px;">{diff_text}</td>
                <td style="padding: 10px; color: #475569; font-size: 13px;">{p.summary or ''}</td>
            </tr>
            """
            rows.append(row_html)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; }}
            .header {{ background: #0f172a; color: #ffffff; padding: 20px 24px; }}
            .header h1 {{ margin: 0; font-size: 20px; }}
            .content {{ padding: 24px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 16px; text-align: left; }}
            th {{ background: #f1f5f9; padding: 10px; font-size: 12px; color: #475569; text-transform: uppercase; }}
            .footer {{ padding: 16px 24px; background: #f8fafc; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>Watchtower Scraper &mdash; Activity Report</h1>
            </div>
            <div class="content">
              <p style="color: #334155; margin-top: 0;">We detected <b>{len(payloads)}</b> events requiring your attention:</p>
              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Source</th>
                    <th>Listing / Item</th>
                    <th>Diff</th>
                    <th>Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {''.join(rows)}
                </tbody>
              </table>
            </div>
            <div class="footer">
              Generated automatically by Watchtower Scraper. All times UTC.
            </div>
          </div>
        </body>
        </html>
        """
        return html
