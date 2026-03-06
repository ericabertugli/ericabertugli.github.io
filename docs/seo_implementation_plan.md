# SEO Implementation Plan

## 1. Technical SEO Foundations

- [x] Add proper `<title>` tags to each page
- [x] Add `<meta name="description">` tags to each page
- [x] Ensure mobile responsiveness
- [x] Compress images (profile.jpeg is 140KB - acceptable)
- [x] Minify CSS/JS (inline CSS, external JS from CDNs)
- [x] Use semantic HTML (`<header>`, `<main>`, `<article>`, `<nav>`)
- [x] Add `robots.txt`
- [x] Add `sitemap.xml`
- [x] Verify HTTPS is enabled (GitHub Pages)

## 2. Content & Structure

- [x] Use clear heading hierarchy (`<h1>` → `<h2>` → `<h3>`)
- [x] Add descriptive `alt` attributes to all images
- [x] Use descriptive, readable URLs
- [x] Add structured data (JSON-LD) for rich snippets
- [x] Review content for quality and originality

## 3. Social & Branding

- [x] Add Open Graph meta tags for social sharing
- [x] Add Twitter Card meta tags
- [x] Add favicon

## 4. Indexing & Discoverability

- [x] Submit sitemap to Google Search Console
- [x] Add canonical URLs to avoid duplicate content issues (added in Section 1)
- [x] Verify site is indexed in Google (search `site:yourdomain.com`)

## 5. Monitoring Setup

- [x] Set up Google Search Console
- [x] Set up Google Analytics or Plausible
- [x] Run Lighthouse audit (Chrome DevTools)
- [x] Review initial SEO score and identify issues

### Lighthouse Results (2026-03-06)

| Category       | Score |
|----------------|-------|
| Performance    | 87%   |
| Accessibility  | 100%  |
| Best Practices | 100%  |
| SEO            | 100%  |

**Performance improvements identified:**
- ~~Image delivery: Convert to WebP format (est. 137 KiB savings)~~ ✓ Done
- Cache lifetimes: Improve caching headers (requires CDN like Cloudflare)
- First Contentful Paint: 2.9s (could be improved)

## 6. Ongoing Monitoring

- [ ] Fix crawl errors reported in Search Console
- [ ] Monitor Core Web Vitals (LCP, FID, CLS)
- [ ] Track keyword rankings
- [ ] Review backlink profile
- [ ] Schedule monthly SEO review