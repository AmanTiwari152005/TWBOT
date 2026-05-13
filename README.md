# Tech Webbed AI Chatbot

Production-ready chatbot project with:

- Frontend: React + Vite
- Backend: Django + Django REST Framework
- AI: OpenAI API
- Email: Resend API with PDF chat transcript
- Local database: SQLite
- Production database: PostgreSQL on Render

## Project Structure

```text
frontend/
  index.html
  src/
  package.json
  .env.example

backend/
  chatbot_backend/
  chat/
  requirements.txt
  build.sh
  Procfile
  .env.example

render.yaml
README.md
```

## Local Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Local backend URL:

```text
http://127.0.0.1:8000
```

Backend `.env` variables:

```env
DJANGO_SECRET_KEY=your_local_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ALLOW_ALL_ORIGINS=False
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=

OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-5-mini

RESEND_API_KEY=your_resend_key
RESEND_FROM_EMAIL=Tech Webbed Chat <onboarding@resend.dev>
LEAD_NOTIFICATION_EMAIL=official.techwebbed@gmail.com
```

The backend API endpoint is:

```text
POST /chat/
```

When the frontend sends `action: "end_chat"`, the backend generates a PDF transcript and emails it to `LEAD_NOTIFICATION_EMAIL` using Resend.

## Local Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend `.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Local frontend URL:

```text
http://127.0.0.1:5173
```

## Render Backend Deployment

1. Push the repository to GitHub.
2. In Render, create a PostgreSQL database.
3. Copy the Render PostgreSQL **Internal Database URL**.
4. Create a Render Web Service from the same GitHub repository.
5. You can deploy using `render.yaml`, or manually set:

```text
Root Directory: backend
Build Command: ./build.sh
Start Command: gunicorn chatbot_backend.wsgi:application
```

The backend build script runs:

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

Render backend environment variables:

```env
DATABASE_URL=your_render_postgres_internal_database_url
DJANGO_SECRET_KEY=generate_a_strong_secret_key
DEBUG=False
ALLOWED_HOSTS=your-backend-name.onrender.com
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://yourwordpresssite.com
CORS_ALLOW_ALL_ORIGINS=False
CSRF_TRUSTED_ORIGINS=https://your-frontend.vercel.app,https://yourwordpresssite.com

OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-5-mini

RESEND_API_KEY=your_resend_key
RESEND_FROM_EMAIL=Tech Webbed Chat <onboarding@resend.dev>
LEAD_NOTIFICATION_EMAIL=official.techwebbed@gmail.com
```

Database behavior:

```text
Local without DATABASE_URL -> SQLite at backend/db.sqlite3
Render with DATABASE_URL -> PostgreSQL
```

You do not use both databases at the same time in one environment.

## Vercel Frontend Deployment

1. Import the same GitHub repository into Vercel.
2. Set root directory to:

```text
frontend
```

3. Set build command:

```bash
npm run build
```

4. Set output directory:

```text
dist
```

5. Add Vercel environment variable:

```env
VITE_API_URL=https://your-backend-name.onrender.com
```

6. Deploy frontend.
7. Copy the final Vercel domain.
8. Add that domain to Render backend:

```env
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-frontend.vercel.app
```

9. Redeploy or restart the Render backend after changing CORS/CSRF values.

## WordPress iframe Embed

After the Vercel frontend is live, embed it into WordPress:

```html
<iframe
  src="https://your-frontend.vercel.app"
  style="position:fixed;right:0;bottom:0;width:420px;height:660px;border:0;z-index:999999;"
  title="Tech Webbed Chatbot"
></iframe>
```

Optional mobile CSS:

```css
@media (max-width: 480px) {
  iframe[title="Tech Webbed Chatbot"] {
    width: 100vw !important;
    height: 100vh !important;
  }
}
```

## Deployment Files

Backend:

- `backend/build.sh`
- `backend/Procfile`
- `backend/requirements.txt`
- `backend/.env.example`

Render:

- `render.yaml`

Frontend:

- `frontend/.env.example`
- `frontend/package.json`
- `frontend/vite.config.js`

