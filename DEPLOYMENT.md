# Deployment Guide for Smart Gmail Assistant

This guide provides step-by-step instructions for deploying the Smart Gmail Assistant multi-agent system to various cloud platforms.

## Prerequisites

Before deployment, ensure you have:

1. **Google Gmail API Credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download `credentials.json`

2. **Google Gemini API Key**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Save the key securely

3. **GitHub Repository** (already created)
   - https://github.com/nikhilkommala01/gmail-automation-agent

## Deployment Options

### Option 1: Google Cloud Run (Recommended)

**Pros:** Native Google Cloud integration, auto-scaling, free tier available

**Steps:**

1. **Enable Billing**
   ```bash
   # Visit: https://console.cloud.google.com/billing
   # Add payment method (free tier includes $300 credit)
   ```

2. **Install Google Cloud SDK**
   ```bash
   # Download from: https://cloud.google.com/sdk/docs/install
   ```

3. **Create Dockerfile** (if not exists)
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   EXPOSE 8080
   CMD ["python", "main.py"]
   ```

4. **Deploy to Cloud Run**
   ```bash
   # Authenticate
   gcloud auth login
   
   # Set project
   gcloud config set project YOUR_PROJECT_ID
   
   # Deploy
   gcloud run deploy gmail-assistant \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

5. **Set Environment Variables**
   ```bash
   gcloud run services update gmail-assistant \
     --set-env-vars GEMINI_API_KEY="your-key-here"
   ```

### Option 2: Render.com (Easiest)

**Pros:** Simple setup, free tier, GitHub integration

**Steps:**

1. **Sign Up**
   - Visit [render.com](https://render.com)
   - Sign up with GitHub

2. **Create New Web Service**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select `gmail-automation-agent`

3. **Configure Service**
   - **Name:** gmail-assistant
   - **Region:** Choose nearest
   - **Branch:** main
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Instance Type:** Free

4. **Add Environment Variables**
   - Go to "Environment" tab
   - Add:
     - `GEMINI_API_KEY`: Your Gemini API key
     - `GMAIL_CREDENTIALS`: Paste contents of credentials.json

5. **Deploy**
   - Click "Create Web Service"
   - Wait 3-5 minutes for deployment

### Option 3: Railway.app

**Pros:** $5 free credit monthly, simple deployment

**Steps:**

1. **Sign Up**
   - Visit [railway.app](https://railway.app)
   - Login with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `gmail-automation-agent`

3. **Add Environment Variables**
   - Click project → Variables
   - Add `GEMINI_API_KEY` and other credentials

4. **Deploy**
   - Railway auto-deploys on push to main
   - Get public URL from settings

### Option 4: Heroku

**Pros:** Mature platform, extensive documentation

**Steps:**

1. **Install Heroku CLI**
   ```bash
   # Download from: https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Login and Create App**
   ```bash
   heroku login
   heroku create gmail-assistant-app
   ```

3. **Set Environment Variables**
   ```bash
   heroku config:set GEMINI_API_KEY="your-key"
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

## Post-Deployment

### 1. Test the Deployment
```bash
curl https://your-app-url.com/health
```

### 2. Monitor Logs
```bash
# Google Cloud
gcloud run logs read --service gmail-assistant

# Render
# View in dashboard

# Railway
railway logs

# Heroku
heroku logs --tail
```

### 3. Update Kaggle Submission

- Add deployment URL to your Kaggle writeup
- Claim +5 bonus points for deployment!

## Security Best Practices

1. **Never commit API keys** to Git
2. **Use environment variables** for all secrets
3. **Enable authentication** if handling user data
4. **Regular updates** - keep dependencies current
5. **Monitor usage** - set up billing alerts

## Troubleshooting

### Issue: Gmail API Authentication Fails
**Solution:** Ensure `credentials.json` is properly configured and OAuth consent screen is set up

### Issue: Gemini API Rate Limits
**Solution:** Implement retry logic and request throttling

### Issue: Out of Memory
**Solution:** Increase instance size or optimize memory usage

## Cost Estimate

- **Google Cloud Run:** Free tier (1M requests/month)
- **Render.com:** Free tier (750 hours/month)
- **Railway.app:** $5 credit/month
- **Heroku:** Free tier discontinued (minimum $5/month)

## Support

For issues or questions:
- GitHub Issues: [Create an issue](https://github.com/nikhilkommala01/gmail-automation-agent/issues)
- Email: [Your email if you want]

## Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Render Deployment Guide](https://render.com/docs)
- [Railway Documentation](https://docs.railway.app/)
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
- [Gemini API Documentation](https://ai.google.dev/docs)

---

**Deployed successfully?** Don't forget to:
1. Update your Kaggle writeup with the deployment URL
2. Test all agent functionalities
3. Monitor performance and costs
4. Share your project with the community!
