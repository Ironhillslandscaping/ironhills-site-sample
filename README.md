# Ironhills Landscaping: static website sample

This is a **static sample copy** of the live Wix site **https://www.ironhillslandscaping.com**, rebuilt as plain HTML/CSS so it can be hosted on **GitHub Pages**.

> **This is not the live site.** Every page has `<meta name="robots" content="noindex,nofollow">`, and `robots.txt` disallows all crawling, so this copy won't compete with the real site in Google. No domain or CNAME is set up, and nothing on the Wix site was changed.

## What's here

| Path | Contents |
|---|---|
| `index.html`, `*/index.html` | 65 pages: home, services, 13 service pages, design, gallery, careers, contact, book-online, blog index, the blog category page, 31 blog posts, the locations hub, and 11 city pages. These mirror the live URLs (`/services/`, `/locations/orem/`, `/post/<slug>/`, and so on). |
| `assets/img/` | Images downloaded from the Wix media CDN, sized for display. Large PNG photos were recompressed to JPG. |
| `assets/video/` | Wix-hosted videos (section backgrounds and inline clips) downloaded at 720p. |
| `assets/embeds/` | The two JobTread request-form embeds, copied verbatim from the Wix "HTML embed" boxes (contact page and design page). |
| `assets/css/site.css`, `assets/js/site.js` | Shared stylesheet, plus a small script for the mobile menu and dropdowns. |
| `robots.txt`, `404.html`, `.nojekyll` | Crawl block, not-found page, and a flag telling GitHub Pages to skip Jekyll processing. |
| `tools/linkcheck.py` | Local link and asset checker. |
| `tools/build/` | The capture and build scripts used to generate the site (see below). |

All internal links are **relative**, so the site works from a GitHub Pages project URL such as `https://<user>.github.io/<repo>/`, from a custom domain, or from a local folder server. External links are unchanged: Calendly booking, Google reviews and maps, YouTube, social profiles, `tel:` and `mailto:`.

## How it was built (2026-11-24)

1. **Page list:** taken from the live Wix sitemaps (`pages-sitemap.xml`, `blog-posts-sitemap.xml`, `blog-categories-sitemap.xml`) and checked against the header menu.
2. **Capture:** `tools/build/capture.py` opened each live page in headless Chrome (Playwright) at 1280px wide, scrolled it so lazy content loaded, and ran `tools/build/extract.js`. That script records each section's background (color, image, video, opacity) and every visible element: rich text with its fonts, sizes, and colors; images; buttons; containers or cards; forms; embeds; and videos. It also records each element's on-page position.
3. **Build:** `tools/build/build.py` turns that geometry into responsive rows and columns using percentage widths, so each section keeps the live order and layout and collapses to a single column on phones. It downloads the media, maps Wix fonts to close web-font equivalents, and rewrites links.
   - Fonts: Corben, Cormorant Garamond, Barlow, Poppins, and Playfair come from Google Fonts. Helvetica uses the system font. Avenir maps to Nunito Sans.
   - Text, headings, phone numbers, prices, and reviews are copied verbatim from the rendered pages. Nothing was added or reworded.

To rebuild after the Wix site changes:

```bash
pip install playwright pillow      # uses the system Chrome at /usr/bin/google-chrome
cd tools/build
python3 capture.py urls.txt --force    # writes pages/*.json, raw/*.html, shots/*.png
python3 build.py ../..                 # regenerates the site into the repo root
```

## Check links locally

```bash
python3 -m http.server 8000          # from the repo root
python3 tools/linkcheck.py http://localhost:8000/
```

## Static-hosting limits (Wix features that can't run on GitHub Pages)

- **Wix Forms:** the contact form on the 11 city pages and the newsletter signups on the home, landscaping-design, and outdoor-lighting pages post to Wix servers. They are rebuilt with the same fields for layout only. Their button sends visitors to the Contact page, where the JobTread request form works. Each one has an HTML comment saying so.
- **JobTread forms** on the contact and design pages use the same embed code as the live site and submit straight to JobTread.
- **Booking and consultation buttons** link to Calendly, the same as on the live site, so they keep working. The Wix Bookings page (`/book-online`) showed "Nothing to book right now," and that text is copied as-is.
- **Blog:** Wix blog comments, likes, view counts, share buttons, and the member login aren't included. The post content and recent-post cards are.
- **Slideshows:** Wix sliders (design-page videos, wood-features photos) are rebuilt as horizontal scroll strips.
- **Wix Chat, the site-members area, and Wix's Google-reviews badge widget** aren't copied. The "Read our Google reviews" button still links to the Google listing.
