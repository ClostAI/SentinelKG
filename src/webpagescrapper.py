
# import os
# import time
# import tiktoken
# import backoff
# import asyncio
# from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
# from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
# from crawl4ai.deep_crawling.filters import (
#     FilterChain,
#     URLPatternFilter,
#     DomainFilter,
#     ContentTypeFilter
# )
# from openai import OpenAI
# from openai import OpenAI
# from openai import OpenAI, RateLimitError
# from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
# # filter_chain = FilterChain([
# #     URLPatternFilter(patterns=["http://*", "https://*"]),
# #     DomainFilter(allowed_domains=[
# #         "sarposhfoods.com",
# #         "orders.sarposhfoods.com"
# #     ]),
# #     ContentTypeFilter(allowed_types=["text/html"])
# # ])
# strategy = BestFirstCrawlingStrategy(
#     max_depth=3,
#     include_external=False,
#     #filter_chain=filter_chain,
#     max_pages=50
# )
# config = CrawlerRunConfig(
#     deep_crawl_strategy=strategy,
#     markdown_generator=DefaultMarkdownGenerator(),
#     stream=False,
#     verbose=True
# )

# async def scrape_webpage(webpage_url):
#     async with AsyncWebCrawler() as crawler:
#         results = await crawler.arun(webpage_url, config=config)
#         print(f"Total pages crawled: {len(results)}")

#         with open("crawl_output.txt", "w", encoding="utf-8") as f:
#             for res in results:
#                 if res.markdown:
#                     # If markdown is a string
#                     if isinstance(res.markdown, str):
#                         f.write(res.markdown + "\n\n")
#                     # If markdown is a MarkdownGenerationResult object
#                     elif hasattr(res.markdown, 'raw_markdown'):
#                         f.write(res.markdown.raw_markdown + "\n\n")
#                     else:
#                         f.write(f"No markdown content extracted for {res.url}\n\n")
#                 else:
#                     f.write(f"No markdown content extracted for {res.url}\n\n")

# asyncio.run(scrape_webpage("https://www.paperandpie.in"))
##############################################################################################################
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


# OPENAI_API_KEY="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"
# client = OpenAI(api_key=OPENAI_API_KEY)

# # Tokenizer for gpt-4o-mini
# ENCODER = tiktoken.encoding_for_model("gpt-4o-mini")

# # TPM & derived TPS (tokens per second) limit
# TPM = 200_000  # your org’s tokens-per-minute limit
# TPS = TPM / 60

# def chunk_text_by_tokens(text: str, max_chunk_tokens: int = 3000) -> list[str]:
#     """Split text into chunks, each ≤ max_chunk_tokens (approx)."""
#     tokens = ENCODER.encode(text)
#     chunks = []
#     for i in range(0, len(tokens), max_chunk_tokens):
#         chunk = tokens[i : i + max_chunk_tokens]
#         chunks.append(ENCODER.decode(chunk))
#     return chunks

# def throttle_sleep(tokens_used: int, last_time: float) -> float:
#     """
#     Sleep if needed to respect TPS, then return new timestamp.
#     """
#     elapsed = time.time() - last_time
#     allowed = TPS * elapsed
#     if tokens_used > allowed:
#         deficit = tokens_used - allowed
#         time.sleep(deficit / TPS)
#     return time.time()

# @backoff.on_exception(
#     backoff.expo,              # exponential backoff
#     RateLimitError,            # on 429
#     max_time=300               # up to 5 minutes total
# )
# def safe_create_completion(**kwargs):
#     return client.chat.completions.create(**kwargs)

# def process_file(file_path: str):
#     with open(file_path, "r", encoding="utf-8") as f:
#         content = f.read()

#     # 1) Split into sensible token-sized chunks
#     chunks = chunk_text_by_tokens(content, max_chunk_tokens=3000)

#     last_request_time = time.time()
#     for idx, chunk in enumerate(chunks, start=1):
#         print(f"\nProcessing chunk {idx}/{len(chunks)}...")

#         # Count tokens in prompt + a cushion for output
#         prompt_tokens = len(ENCODER.encode(chunk)) + 500

#         # 2) Throttle to avoid exceeding TPM
#         last_request_time = throttle_sleep(prompt_tokens, last_request_time)

#         # 3) Call with retry on 429
#         response = safe_create_completion(
#             model="gpt-4o-mini",
#             messages=[
#                {
#                    "role": "system",
#                    "content": """
# You are an assistant that processes and refines content. Your tasks include:
# - Retaining all provided information without summarizing.
# - Removing duplicates or redundant entries and ensure unique content.
# - Maintaining all images and links in their original form.
# - Formatting the output as structured markdown.
# """
#                },
#                {"role": "user", "content": chunk}
#             ]
#         )

#         print("Assistant:", response.choices[0].message.content)

# if __name__ == "__main__":
#     process_file("crawl_output.txt")
