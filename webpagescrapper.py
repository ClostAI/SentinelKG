import os
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# ————————————————————————————————————————————————
# 1) Configure your crawling strategy & run settings
# ————————————————————————————————————————————————
strategy = BestFirstCrawlingStrategy(
    max_depth=3,
    include_external=False,
    max_pages=50
)
config = CrawlerRunConfig(
    deep_crawl_strategy=strategy,
    markdown_generator=DefaultMarkdownGenerator(),
    stream=False,
    verbose=True
)

# ————————————————————————————————————————————————
# 2) Scrape and write URL + content references
# ————————————————————————————————————————————————
async def scrape_webpage(webpage_url: str, output_dir: str = "restaurant", output_filename: str = "crawl_output.txt"):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(webpage_url, config=config)
        print(f"Total pages crawled: {len(results)}")

        output_path = os.path.join(output_dir, output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for res in results:
                # 1) Write the URL as a markdown header
                f.write(f"## Source: {res.url}\n\n")

                # 2) Write the markdown content or fallback note
                if res.markdown:
                    if isinstance(res.markdown, str):
                        f.write(res.markdown)
                    elif hasattr(res.markdown, "raw_markdown"):
                        f.write(res.markdown.raw_markdown)
                    else:
                        f.write(f"*No markdown content extracted for {res.url}*")
                else:
                    f.write(f"*No markdown content extracted for {res.url}*")

                # 3) Separation between pages
                f.write("\n\n---\n\n")

    print(f"Saved crawled content to {output_path}")


def webpage_scraper(webpage_url: str, output_dir: str):
    asyncio.run(scrape_webpage(webpage_url, output_dir))
