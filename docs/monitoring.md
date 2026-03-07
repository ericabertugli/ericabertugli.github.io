# Website Monitoring

## Uptime Monitoring

**Service:** [UptimeRobot](https://uptimerobot.com) (free tier)

- Checks site availability every 5 minutes
- Sends email alerts on downtime
- Dashboard: https://uptimerobot.com/dashboard

## Broken Link Detection

**Service:** GitHub Actions (`.github/workflows/link-check.yml`)

- Runs weekly on Fridays at 14:00 UTC
- Checks all internal and external links
- Failed runs trigger GitHub email notifications

**Manual trigger:** Actions tab → Link Check → Run workflow
