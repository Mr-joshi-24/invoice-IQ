# Invoice IQ — Deployment Guide

This guide covers deploying **Invoice IQ** to production using the enterprise-standard decoupled architecture:
- **Backend & Database**: [Render](https://render.com) (Docker container + Managed PostgreSQL)
- **Frontend**: [Vercel](https://vercel.com) (Global Edge CDN for React/Vite)

---

## 1. Prerequisites: Push Latest Config to GitHub

Run this command in your terminal to ensure Render and Vercel have the latest `render.yaml` and `Dockerfile` configurations:

```bash
git push origin main
```

---

## 2. Deploy Backend on Render

Render builds directly from your GitHub repository.

### Step 2.1: Create Render Account
1. Go to [dashboard.render.com](https://dashboard.render.com) and sign in using **GitHub**.

### Step 2.2: Create Web Service
1. In your Render Dashboard, click **New +** $\rightarrow$ **Web Service**.
2. Select your repository: `Mr-joshi-24/invoice-IQ` (click **Connect**).
3. Configure the service:
   - **Name**: `invoice-iq-backend`
   - **Region**: Oregon (US West) or closest region
   - **Branch**: `main`
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Docker Build Context**: `.`
   - **Instance Type**: `Free`

### Step 2.3: Environment Variables
Under the **Environment Variables** section, add:

| Key | Value | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Production environment flag |
| `DEBUG` | `False` | Disables debug logs |
| `SECRET_KEY` | *(Click "Generate" or enter a secure 32+ char string)* | JWT HMAC secret key |
| `ALLOWED_ORIGINS` | `["http://localhost:5173", "http://localhost:3000"]` | CORS origin whitelist |

*(Note: If using SQLite, the app will auto-create `data/documind.db`. If you create a Render PostgreSQL database under "New + -> PostgreSQL", copy its "Internal Database URL" and paste it as `DATABASE_URL`)*.

### Step 2.4: Deploy
Click **Create Web Service**. 
Render will build the Docker container and deploy it with free automatic SSL:
- **API URL**: `https://invoice-iq-backend.onrender.com`
- **Swagger Docs**: `https://invoice-iq-backend.onrender.com/docs`
- **Health Check**: `https://invoice-iq-backend.onrender.com/`

---

## 3. Deploy Frontend on Vercel

### Step 3.1: Connect Vercel
1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New...** $\rightarrow$ **Project**.
3. Select `Mr-joshi-24/invoice-IQ` and click **Import**.

### Step 3.2: Configure Build Settings
- **Framework Preset**: `Vite`
- **Root Directory**: Click "Edit" and choose `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

### Step 3.3: Environment Variable
Under **Environment Variables**, add:
- **Key**: `VITE_API_URL`
- **Value**: `https://invoice-iq-backend.onrender.com/api/v1` *(replace with your actual Render URL)*

### Step 3.4: Deploy
Click **Deploy**. Within 60 seconds, your frontend will be live at:
`https://invoice-iq.vercel.app`

---

## 4. Final Wiring

Once both are deployed:
1. Copy your Vercel URL (e.g. `https://invoice-iq-xyz.vercel.app`).
2. Go back to **Render Dashboard** $\rightarrow$ `invoice-iq-backend` $\rightarrow$ **Environment**.
3. Add your Vercel URL to `ALLOWED_ORIGINS` (our backend also automatically accepts all `https://*.vercel.app` origins via regex!).

