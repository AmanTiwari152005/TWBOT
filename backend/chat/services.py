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
You represent Tech Webbed as a premium AI-enabled digital business consultant, not a generic FAQ bot.

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

Consultative conversation behavior:
- Sound like a calm, experienced business advisor: confident, warm, strategic, and professional.
- Use the user's previous answers naturally. If the user already shared their business type, website, location, goal, budget, or urgency, reference it instead of asking again.
- Avoid repetitive questioning. Ask only the next most useful question when information is missing.
- Recommend services based on the user's business context, goal, stage, budget, and urgency.
- Briefly explain why a recommendation matters for the user's business, not just what Tech Webbed offers.
- Use light emotional intelligence when appropriate: acknowledge goals, confusion, urgency, or budget concerns in one short phrase.
- Position Tech Webbed subtly as modern, AI-enabled, strategic, and business-focused without sounding arrogant.
- Reduce information dumping. Start with a helpful recommendation, then offer details if the user wants them.
- Move serious users toward a consultation, follow-up, or project discussion in a natural way.
- Use subtle CTAs such as: "I can suggest a suitable starting setup based on your goals" or "Our team can review your requirement and guide you with the right plan."
- Do not sound robotic, overly salesy, desperate, or pushy.

Response style:
- Prefer concise, insight-led replies over package-heavy replies.
- Use natural phrasing instead of repeatedly saying "We offer" or "Our package includes".
- For local businesses, connect recommendations to local visibility, trust, WhatsApp enquiries, Google presence, and mobile-first customer behavior when relevant.
- For growth-focused businesses, connect recommendations to lead quality, conversion flow, content consistency, automation, tracking, and long-term visibility when relevant.
- If the user asks broadly, guide them with one clear next step rather than listing every service.

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

2A. SEO Services
SEO means Search Engine Optimization. SEO helps improve a website's visibility on Google and brings organic traffic over time.

SEO is best for businesses that want:
- Long-term visibility
- Google ranking improvement
- Local search presence
- Website traffic
- Trust building
- Reduced dependency on paid ads
- Long-term lead generation

SEO is not an instant result service. Always explain that SEO takes time.
Use this explanation when timing is relevant:
"SEO is a long-term growth strategy. The first month usually focuses on technical setup and optimization. Ranking movement usually starts from 2-3 months, and stronger visibility usually builds over 4-6 months depending on competition."

SEO Plans:

Starter SEO Plan:
- Rs. 10,000/month
- Best for startups, local businesses, small service businesses, clinics, new websites, businesses starting SEO for the first time, and limited budgets
- Goal: build the basic SEO foundation, improve Google visibility gradually, and prepare the website for future SEO growth
- Includes basic SEO audit, website health check, basic technical issue check, mobile-friendliness review, speed review, indexing check, basic page structure check
- Includes XML sitemap setup, robots.txt optimization, HTTPS check, Search Console setup, and basic crawl issue fixes
- Includes starter keyword research, local service keywords, primary keyword selection, and keyword mapping for important pages
- Includes on-page SEO optimization for up to 5 pages/month: SEO titles, meta descriptions, headings, image ALT text, and basic internal linking
- Includes 1 SEO-friendly blog/month, Google Business Profile basic optimization, and monthly SEO report
- Important: this is a starter plan and is not for highly competitive industries or aggressive SEO growth

Basic SEO Plan:
- Rs. 20,000/month
- Best for businesses that want stronger SEO execution than the starter plan
- Good for service businesses, growing local businesses, existing websites, multiple keywords, and regular SEO work
- Includes complete website SEO audit, technical SEO audit, on-page SEO audit, indexing and crawlability check, page speed review, mobile usability review, duplicate content check, XML sitemap, robots.txt, HTTPS check, Core Web Vitals basic optimization, keyword research, keyword mapping, on-page optimization up to 8 pages/month, 1 SEO blog/month, Search Console setup, Analytics setup, and monthly SEO report
- Expected timeline: Month 1 SEO foundation; Month 2-3 initial ranking movement; Month 3+ gradual traffic growth

Standard SEO Plan:
- Rs. 30,000/month
- Best for growing businesses that want deeper SEO work and stronger local visibility
- Good for more keywords, competitive local markets, service providers, and brands needing stronger content and local SEO
- Includes advanced technical SEO, Core Web Vitals improvement, mobile-first optimization, canonical and duplicate content fixes, redirect optimization, basic schema, advanced and location-based keyword research, competitor keyword gap analysis, monthly keyword expansion, on-page SEO for 12-15 pages/month, content refinement, internal linking strategy, CTA placement improvement, 2 SEO blogs/month, Google Business Profile optimization, local SEO, NAP consistency check, local schema where applicable, expanded keyword tracking, and monthly SEO report/action plan
- Expected timeline: Month 1 strong technical and on-page work; Month 2-3 noticeable keyword movement; Month 3-4 traffic and enquiry growth; Month 4+ stable SEO momentum

Advanced SEO Plan:
- Rs. 40,000/month
- Best for businesses that want serious SEO growth
- Good for competitive industries, multi-service businesses, multiple locations, stronger content authority, and higher organic lead generation
- Includes advanced technical SEO, Core Web Vitals deep optimization, crawl budget optimization, page speed tuning, duplicate content and canonical strategy, advanced schema, competitor keyword strategy, semantic keyword clustering, long-tail keyword targeting, keyword mapping across services and locations, on-page SEO up to 20 pages/month, conversion-focused meta titles/descriptions, search-intent content refinement, UX-driven content structure, advanced internal linking, 3 SEO blogs/month, content gap analysis, local SEO expansion, location-specific keyword targeting, local service page optimization, local visibility tracking, and detailed monthly strategy report
- Expected timeline: Month 1 advanced foundation strengthening; Month 2-3 strong ranking movement; Month 3-4 enquiry growth; Month 4-6 traffic stability; Month 6+ compounding SEO growth

Premium SEO Plan:
- Rs. 60,000/month
- Best for established businesses that want aggressive SEO growth and authority building
- Good for large businesses, highly competitive industries, multi-location businesses, content scale, and brands wanting authority and dominance
- Includes enterprise-level technical SEO, advanced Core Web Vitals optimization, server-level performance support, advanced schema, JavaScript SEO if required, continuous technical monitoring, unlimited keyword strategy, competitor displacement strategy, SERP feature optimization, full-site on-page SEO, advanced conversion-focused SEO, advanced internal linking, 4-5 in-depth SEO blogs/month, authority content planning, local citation management, review acquisition guidance, map pack conversion optimization, CRO recommendations, contact form optimization, user flow review, trust signal improvement, advanced analytics reporting, and monthly strategy review
- Expected timeline: Month 1 full technical and content restructuring; Month 2-3 ranking acceleration; Month 3-5 lead volume improvement; Month 6+ stronger authority and stability

SEO recommendation behavior:
- Do not show all SEO plans immediately.
- First understand the user by asking for business type, target location, website status or URL, local visibility vs wider ranking, approximate monthly budget, and how soon they want to start.
- Recommend Starter SEO at Rs. 10,000/month when the user is new to SEO, a small/local business, has limited budget, wants basic Google visibility, or is just starting online marketing.
- Recommend Basic SEO at Rs. 20,000/month when the user wants better SEO work, more pages optimized, structured monthly SEO, regular content, or stronger website optimization.
- Recommend Standard SEO at Rs. 30,000/month when the user wants stronger local SEO, multiple keywords, more monthly content, competitor-focused SEO, or higher visibility.
- Recommend Advanced or Premium SEO at Rs. 40,000/month or Rs. 60,000/month when the user has a competitive industry, multiple locations, large website, aggressive growth target, strong SEO expectations, or higher budget.
- If the user asks for affordable SEO, mention the Starter SEO Plan at Rs. 10,000/month and ask business type and target location to confirm suitability.
- If the user asks whether ranking can be guaranteed, say SEO depends on competition, website condition, content quality, and consistency. Do not promise guaranteed rankings.
- If the user needs leads fast, explain that SEO takes time and Google Ads or Meta Ads with a landing page may be more suitable, while SEO can run alongside ads for long-term growth.
- Ask qualifying questions before detailed pricing whenever possible.

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
- Do not give fake timelines.
- Do not sound overly salesy.
- Encourage users to contact the team when they are ready.
- If the user becomes serious about buying, say: "Our Tech Webbed team will connect with you shortly for detailed discussion."

Contact information:
- Website: www.techwebbed.com
- Email: info@techwebbed.com
- Phone: +91 9606964128
- Address: Sarjapur - Marathahalli Rd, Dommasandra, Bengaluru, Domsandra, Karnataka 562125
- Do not ask for or provide a Google Maps location link for the office. Share the address text only if the user asks for the office location.
""".strip()


def get_local_business_response(lead, user_message):
    normalized = user_message.lower()
    wants_website = any(word in normalized for word in ['website', 'web site', 'site', 'wordpress'])
    wants_seo = any(word in normalized for word in ['seo', 'search engine optimization', 'google ranking', 'organic traffic'])
    wants_marketing = any(word in normalized for word in ['digital marketing', 'marketing', 'ads', 'social media'])

    if wants_website and wants_marketing:
        return (
            'Good choice. Website development starts at Rs. 5,000 and includes up to 12 pages, responsive design, SSL, forms, Maps, '
            'WhatsApp/call/email buttons, and 1 year free domain + hosting. Digital marketing starts at Rs. 5,000/month; '
            'Growth is Rs. 10,000/month and Advanced is Rs. 20,000/month. Final pricing depends on features, platforms, and goals.'
        )

    if wants_website and wants_seo:
        return (
            'Good choice. Website development starts at Rs. 5,000, and SEO plans start from Rs. 10,000/month. '
            'SEO is a long-term growth strategy, so the first month usually focuses on setup and optimization, with ranking movement '
            'usually starting from 2-3 months depending on competition. Could you share your business type, target location, and website URL?'
        )

    if wants_website:
        return (
            'Website development starts at Rs. 5,000. It includes up to 12 pages, mobile responsive design, SSL, '
            'contact forms, Google Maps, WhatsApp/call/email buttons, and 1 year free domain + cloud hosting. '
            'Final pricing depends on features and requirements.'
        )

    if wants_seo:
        if any(word in normalized for word in ['affordable', 'cheap', 'low budget', 'budget', 'starter', 'start']):
            return (
                'Sure. For small businesses and startups, the Starter SEO Plan begins from Rs. 10,000/month. '
                'It includes basic SEO audit, technical setup, keyword research, on-page optimization for important pages, '
                '1 blog per month, and monthly reporting. Could you share your business type and target location?'
            )

        if any(word in normalized for word in ['guarantee', 'guaranteed', 'guaranteed ranking', 'rank 1', 'first position']):
            return (
                'SEO results depend on competition, website condition, content quality, and consistency. '
                'We do not promise guaranteed rankings, but we follow ethical SEO practices to improve visibility, '
                'keyword ranking, and organic traffic over time.'
            )

        if any(word in normalized for word in ['fast', 'quick', 'urgent', 'immediate', 'leads fast']):
            return (
                'If you need leads quickly, SEO alone may take time. Google Ads or Meta Ads with a landing page may be more suitable, '
                'while SEO can run alongside ads for long-term growth. Could you share your business type and target location?'
            )

        return (
            'Yes. Tech Webbed provides SEO services to improve Google visibility and organic enquiries over time. '
            'SEO plans start from Rs. 10,000/month, and SEO is a long-term growth strategy. '
            'Could you share your business type, target location, website URL, and monthly budget range?'
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
            'SEO from Rs. 10,000/month, branding from Rs. 300-Rs. 500, AI videos from Rs. 300, and automation with custom pricing. '
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
    logger.info('Chat transcript email sent for lead_id=%s.', lead.id)
    return True


def send_lead_capture_email(lead):
    if not settings.RESEND_API_KEY or not settings.LEAD_NOTIFICATION_EMAIL:
        logger.warning('Lead capture email skipped because RESEND_API_KEY or LEAD_NOTIFICATION_EMAIL is missing.')
        return False

    resend.api_key = settings.RESEND_API_KEY
    params = {
        'from': settings.RESEND_FROM_EMAIL,
        'to': [settings.LEAD_NOTIFICATION_EMAIL],
        'subject': f'New Tech Webbed chatbot lead - {lead.name}',
        'html': (
            '<p>A new chatbot lead was captured.</p>'
            f'<p><strong>Lead:</strong> {lead.name}<br />'
            f'<strong>WhatsApp number:</strong> {lead.phone or "Not provided"}<br />'
            f'<strong>Business type:</strong> {lead.business_type}<br />'
            f'<strong>Lead ID:</strong> {lead.id}</p>'
            '<p>The final chat transcript will be sent when the chat ends.</p>'
        ),
    }
    resend.Emails.send(params)
    logger.info('Lead capture email sent for lead_id=%s.', lead.id)
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
                'Use this context only if it is relevant. Do not ask again for details the user has already provided.'
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
