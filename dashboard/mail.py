from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_html_email(
    to_email: str | list,
    subject: str,
    template_name: str,
    context: dict | None = None,
    from_email: str | None = None,
    fail_silently: bool = False,
):
    """
    Sends a nicely styled HTML email using Django templates.

    Parameters:
        to_email        : Recipient email(s) – string or list
        subject         : Email subject (keep it short, no newlines)
        template_name   : Path to HTML template (e.g. "emails/welcome.html")
        context         : Dictionary passed to the template
        from_email      : Override sender (defaults to DEFAULT_FROM_EMAIL)
        fail_silently   : Whether to raise exceptions
    """
    context = context or {}

    # Render HTML version
    html_content = render_to_string(template_name, context)

    # Create plain-text version (fallback for email clients that don't support HTML)
    text_content = strip_tags(html_content)

    # Default sender
    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    # Build email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email] if isinstance(to_email, str) else to_email,
    )
    email.attach_alternative(html_content, "text/html")

    # Optional: attach files
    # email.attach("report.pdf", pdf_content, "application/pdf")

    # Send
    email.send(fail_silently=fail_silently)