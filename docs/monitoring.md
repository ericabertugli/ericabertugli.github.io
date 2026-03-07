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

## SEO & Analytics

- [Google Search Console](https://search.google.com/u/1/search-console?resource_id=https%3A%2F%2Fericabertugli.github.io%2F) - Search performance, indexing status, crawl errors
- [Google Analytics](https://analytics.google.com/analytics/web/provision/?authuser=1#/provision/create) - Traffic, user behavior, engagement metrics

## Map Data Updates

**Service:** GitHub Actions (`.github/workflows/update-map-data.yml`)

- Runs monthly on the 1st at 6:00 UTC
- Fetches latest data from OpenStreetMap via Overpass API
- Creates PR and auto-merges if checks pass