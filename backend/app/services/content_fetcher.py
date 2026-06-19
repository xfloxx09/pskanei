import httpx


async def extract_article_text(url: str) -> str:
    if not url or not url.startswith("http"):
        return ""

    try:
        import trafilatura

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ViralClipStudio/1.0)"},
            )
            resp.raise_for_status()
            html = resp.text

        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        if text:
            return text[:3000]
    except Exception:
        pass

    return ""
