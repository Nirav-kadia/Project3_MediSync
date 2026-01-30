# GitHub Secrets Setup Guide

To enable automatic deployment via GitHub Actions, you need to set up the following secrets in your GitHub repository.

## How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

## Required Secrets

### AWS Credentials

#### `AWS_ACCESS_KEY_ID`
Your AWS access key ID for programmatic access.

**How to get it:**
1. Go to AWS Console → IAM → Users
2. Select your user or create a new one
3. Go to **Security credentials** tab
4. Click **Create access key**
5. Copy the Access Key ID

**Value:** `AKIAIOSFODNN7EXAMPLE`

---

#### `AWS_SECRET_ACCESS_KEY`
Your AWS secret access key (shown only once when creating access key).

**Value:** `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

---

### Pulumi Token

#### `PULUMI_ACCESS_TOKEN`
Your Pulumi access token for managing infrastructure state.

**How to get it:**
1. Go to https://app.pulumi.com/account/tokens
2. Click **Create token**
3. Give it a name (e.g., "GitHub Actions")
4. Copy the token

**Value:** `pul-abc123def456...`

---

### Application Secrets (from your .env file)

#### `GOOGLE_API_KEY`
Your Google Gemini API key.

**Current value from .env:**
```
AIzaSyBovrkeTtXOyMYlTOQoCn6RmjDH9DTiZQ8
```

---

#### `NEO4J_URI`
Your Neo4j AuraDB connection URI.

**Current value from .env:**
```
neo4j+ssc://e549a456.databases.neo4j.io
```

---

#### `NEO4J_USER`
Your Neo4j username.

**Current value from .env:**
```
neo4j
```

---

#### `NEO4J_PASSWORD`
Your Neo4j password.

**Current value from .env:**
```
n66M978Cm1zU-vdSdXCC7AGtwOw2gS1wn2UZAvHYNcI
```

---

## Summary Checklist

Once you've added all secrets, you should have:

- [ ] `AWS_ACCESS_KEY_ID`
- [ ] `AWS_SECRET_ACCESS_KEY`
- [ ] `PULUMI_ACCESS_TOKEN`
- [ ] `GOOGLE_API_KEY`
- [ ] `NEO4J_URI`
- [ ] `NEO4J_USER`
- [ ] `NEO4J_PASSWORD`

## Testing the Setup

After adding all secrets:

1. Make a small change to your code
2. Commit and push to the `main` branch:
   ```bash
   git add .
   git commit -m "Test deployment"
   git push origin main
   ```
3. Go to **Actions** tab in GitHub
4. Watch the deployment workflow run
5. Once complete, visit the ALB URL shown in the workflow output

## Security Notes

⚠️ **Important:**
- Never commit the `.env` file to Git (it's in `.gitignore`)
- GitHub secrets are encrypted and only exposed during workflow runs
- Rotate your credentials regularly
- Use least-privilege IAM policies for AWS access

## Troubleshooting

### "Secret not found" error
- Double-check the secret name matches exactly (case-sensitive)
- Ensure you're adding secrets to the correct repository

### AWS permission errors
- Verify your IAM user has permissions for:
  - ECR (push images)
  - ECS (update services)
  - CloudWatch (logs)
  - IAM (create roles)
  - EC2 (security groups, load balancers)

### Pulumi errors
- Verify your Pulumi token is valid
- Check you have access to the organization/stack
- Ensure the stack name matches (`dev`)

## Need Help?

- Check the workflow logs in GitHub Actions
- Review CloudWatch logs for application errors
- Verify all secrets are set correctly
