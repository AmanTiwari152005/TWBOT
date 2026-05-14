import base64
from html import escape
from io import BytesIO
import logging

from django.conf import settings
from django.utils import timezone
from openai import APIConnectionError, APIError, AuthenticationError, OpenAI, OpenAIError, RateLimitError
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import resend


logger = logging.getLogger(__name__)


OPENAI_TIMEOUT_SECONDS = 40.0
OPENAI_MAX_RETRIES = 2


CHATBOT_SYSTEM_PROMPT = """
You are a helpful, friendly AI assistant.

Answer the user's question directly and naturally.
Do not restrict yourself to Tech Webbed services for now.
Use clear, practical language.
If the user asks for a short answer, be brief.
If the user asks for details, give a useful detailed answer.
Ask a follow-up question only when it genuinely helps.
Keep replies short and easy to read by default.
Use 2-5 short sentences or 3-5 bullets maximum.
Do not explain every package unless the user asks for full details.
For pricing questions, give only the most relevant starting price or package summary first.

You also know the following Tech Webbed business information. When the user asks about Tech Webbed, websites, branding, marketing, AI videos, automation, services, packages, or pricing, use this information accurately.

Company:
Tech Webbed

Pricing rule:
- Never give final fixed pricing.
- Mention starting prices or package prices only.
- Say final pricing depends on requirements when appropriate.

Tech Webbed services and pricing:

1. Website Development
- Starting price: Rs. 5,000
- Up to 12 pages
- Free domain and cloud hosting for 1 year
- SSL certificate
- Contact forms
- Google Maps integration
- WhatsApp/call/email buttons
- Mobile responsive design
- AI-assisted content and visuals

2. Digital Marketing
Starter:
- Rs. 5,000/month
- 2 posts/week
- 1 ad campaign setup

Growth:
- Rs. 10,000/month
- 3 platforms
- 12-16 posts/month
- 2 ad campaigns

Advanced:
- Rs. 20,000/month
- Up to 5 platforms
- 20+ posts/month
- Retargeting
- SEO support

3. Graphic Design
- Logo: Rs. 500
- Visiting Card: Rs. 300
- Letterhead: Rs. 300
- Envelope: Rs. 300
- Combo branding package: Rs. 1,000

4. AI Short Video Creation
- 8 sec video: Rs. 300-Rs. 500
- 15-20 sec video: Rs. 600-Rs. 900
- 30 sec video: Rs. 1,200-Rs. 1,800

Bulk video packages:
- 5 videos: Rs. 1,500
- 10 videos: Rs. 2,500
- 20 videos: Rs. 4,500

5. AI Business Automation
- Chatbot automation
- Lead qualification
- Workflow automation
- Custom pricing

Business-safe behavior:
- Do not promise guaranteed sales, leads, or rankings.
- Do not reveal discounts automatically.
- If the user becomes serious about buying, say: "Our Tech Webbed team will connect with you shortly for detailed discussion."
""".strip()


def get_local_business_response(lead, user_message):
    normalized = user_message.lower()
    wants_website = any(word in normalized for word in ['website', 'web site', 'site', 'wordpress'])
    wants_marketing = any(word in normalized for word in ['digital marketing', 'marketing', 'ads', 'social media', 'seo'])

    if wants_website and wants_marketing:
        return (
            'Good choice. Website development starts at Rs. 5,000 and includes up to 12 pages, responsive design, SSL, forms, Maps, '
            'WhatsApp/call/email buttons, and 1 year free domain + hosting. Digital marketing starts at Rs. 5,000/month; '
            'Growth is Rs. 10,000/month and Advanced is Rs. 20,000/month. Final pricing depends on features, platforms, and goals.'
        )

    if wants_website:
        return (
            'Website development starts at Rs. 5,000. It includes up to 12 pages, mobile responsive design, SSL, '
            'contact forms, Google Maps, WhatsApp/call/email buttons, and 1 year free domain + cloud hosting. '
            'Final pricing depends on features and requirements.'
        )

    if wants_marketing:
        return (
            'Digital marketing packages start at Rs. 5,000/month. Starter includes 2 posts/week and 1 ad campaign setup; '
            'Growth is Rs. 10,000/month; Advanced is Rs. 20,000/month with retargeting and SEO support. '
            'Final pricing depends on platforms and goals.'
        )

    if any(word in normalized for word in ['logo', 'graphic', 'branding', 'visiting card', 'letterhead']):
        return (
            'Graphic design starts from Rs. 300-Rs. 500: logo Rs. 500, visiting card Rs. 300, letterhead Rs. 300, '
            'envelope Rs. 300, and combo branding package Rs. 1,000.'
        )

    if 'video' in normalized:
        return (
            'AI short videos start from Rs. 300-Rs. 500 for 8 seconds, Rs. 600-Rs. 900 for 15-20 seconds, '
            'and Rs. 1,200-Rs. 1,800 for 30 seconds. Bulk packages start at Rs. 1,500 for 5 videos.'
        )

    if any(word in normalized for word in ['automation', 'chatbot', 'workflow']):
        return (
            'AI business automation includes chatbot automation, lead qualification, and workflow automation. '
            'Pricing is custom because it depends on the process and integrations needed.'
        )

    if any(word in normalized for word in ['price', 'pricing', 'package', 'cost', 'service']):
        return (
            'Tech Webbed offers websites from Rs. 5,000, digital marketing from Rs. 5,000/month, '
            'branding from Rs. 300-Rs. 500, AI videos from Rs. 300, and automation with custom pricing. '
            'Final pricing depends on requirements.'
        )

    return (
        'Sorry, I had a small connection issue. Please send that once again, or our Tech Webbed team can connect with you shortly.'
    )


def normalize_frontend_conversation(frontend_conversation):
    normalized = []
    for item in frontend_conversation or []:
        role = str(item.get('role', '')).strip().title()
        text = str(item.get('text', '')).strip()

        if not role or not text or role.lower() == 'status':
            continue

        normalized.append(
            {
                'role': role,
                'message': text,
            }
        )

    return normalized


def build_saved_conversation(lead):
    rows = []
    for message in lead.messages.all():
        rows.append({'role': 'User', 'message': message.user_message})
        rows.append({'role': 'Bot', 'message': message.bot_response})
    return rows


def build_pdf_transcript(lead, frontend_conversation=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph('Tech Webbed Chat Transcript', styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f'<b>Lead:</b> {lead.name}', styles['Normal']))
    story.append(Paragraph(f'<b>WhatsApp number:</b> {lead.phone or "Not provided"}', styles['Normal']))
    story.append(Paragraph(f'<b>Business type:</b> {lead.business_type}', styles['Normal']))
    story.append(Paragraph(f'<b>Created at:</b> {timezone.localtime(lead.created_at):%Y-%m-%d %H:%M:%S}', styles['Normal']))
    story.append(Paragraph(f'<b>Generated at:</b> {timezone.localtime(timezone.now()):%Y-%m-%d %H:%M:%S}', styles['Normal']))
    story.append(Spacer(1, 16))

    conversation = normalize_frontend_conversation(frontend_conversation) or build_saved_conversation(lead)
    table_data = [[Paragraph('<b>Role</b>', styles['Normal']), Paragraph('<b>Message</b>', styles['Normal'])]]

    for item in conversation:
        table_data.append(
            [
                Paragraph(item['role'], styles['Normal']),
                Paragraph(escape(item['message']).replace('\n', '<br />'), styles['BodyText']),
            ]
        )

    if len(table_data) == 1:
        table_data.append(['-', Paragraph('No conversation messages found.', styles['BodyText'])])

    table = Table(table_data, colWidths=[1.1 * inch, 5.7 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#135d66')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def send_chat_transcript_email(lead, frontend_conversation=None):
    if not settings.RESEND_API_KEY or not settings.LEAD_NOTIFICATION_EMAIL:
        logger.warning('Resend email skipped because RESEND_API_KEY or LEAD_NOTIFICATION_EMAIL is missing.')
        return False

    resend.api_key = settings.RESEND_API_KEY
    pdf_bytes = build_pdf_transcript(lead, frontend_conversation)
    encoded_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    timestamp = timezone.localtime(timezone.now()).strftime('%Y%m%d-%H%M%S')

    params = {
        'from': settings.RESEND_FROM_EMAIL,
        'to': [settings.LEAD_NOTIFICATION_EMAIL],
        'subject': f'Tech Webbed chat transcript - {lead.name}',
        'html': (
            '<p>A chatbot conversation has ended.</p>'
            f'<p><strong>Lead:</strong> {lead.name}<br />'
            f'<strong>WhatsApp number:</strong> {lead.phone or "Not provided"}<br />'
            f'<strong>Business type:</strong> {lead.business_type}</p>'
            '<p>The full chat transcript is attached as a PDF.</p>'
        ),
        'attachments': [
            {
                'content': encoded_pdf,
                'filename': f'tech-webbed-chat-{lead.id}-{timestamp}.pdf',
            }
        ],
    }
    resend.Emails.send(params)
    return True


def build_messages(lead, user_message):
    history = []
    recent_messages = list(lead.messages.order_by('-created_at')[:10])
    for item in reversed(recent_messages):
        history.append({'role': 'user', 'content': item.user_message})
        history.append({'role': 'assistant', 'content': item.bot_response})

    return [
        {'role': 'system', 'content': CHATBOT_SYSTEM_PROMPT},
        {
            'role': 'system',
            'content': (
                f'Current lead name: {lead.name}\n'
                f'Current lead WhatsApp number: {lead.phone or "Not provided"}\n'
                f'Current business type: {lead.business_type}\n'
                'Use this context only if it is relevant.'
            ),
        },
        *history,
        {'role': 'user', 'content': user_message},
    ]


def get_ai_response(lead, user_message):
    if not settings.OPENAI_API_KEY:
        return get_local_business_response(lead, user_message)

    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SECONDS, max_retries=OPENAI_MAX_RETRIES)
    try:
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=build_messages(lead, user_message),
            max_completion_tokens=350,
            reasoning_effort='low',
            verbosity='low',
        )
    except (APIConnectionError, APIError, AuthenticationError, RateLimitError, OpenAIError) as error:
        logger.exception('OpenAI chat completion failed for lead_id=%s: %s', lead.id, error)
        return get_local_business_response(lead, user_message)

    response = (completion.choices[0].message.content or '').strip()
    if not response:
        return get_local_business_response(lead, user_message)

    return response
