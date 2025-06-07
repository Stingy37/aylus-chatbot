import os
import requests
import shutil
import streamlit as st
import openai

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup
from fpdf import FPDF

from rag import load_documents, create_database


START_URL        = "https://www.aylus-pearland.org/"
DOWNLOAD_FOLDER  = "LLM_website_context"
PDF_PAGE_PREFIX  = "page_"         # e.g. page_1.pdf, page_2.pdf, …

# ensure context folder exists — but first, clear any old PDFs
if os.path.exists(DOWNLOAD_FOLDER):
    shutil.rmtree(DOWNLOAD_FOLDER)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def crawl_site(start_url):
    opts   = Options(); opts.headless = True
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
    driver.get(start_url)

    to_visit = {start_url}
    visited  = set()
    all_urls = set()

    while to_visit:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)
        driver.get(url)

        # grab all same-domain links
        for a in driver.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            if href.startswith(start_url):
                all_urls.add(href)
                if href not in visited:
                    to_visit.add(href)

    driver.quit()
    return sorted(all_urls)


def text_to_pdf(text, dest_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for line in text.split("\n"):
        pdf.multi_cell(0, 5, line)
    pdf.output(dest_path)


def scrape_and_render_pdfs(urls, download_folder):
    for idx, url in enumerate(urls, start=1):
        fname = f"{PDF_PAGE_PREFIX}{idx}.pdf"
        out_path = os.path.join(download_folder, fname)

        # skip if already done
        if os.path.exists(out_path):
            continue

        # fetch HTML & extract text
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # you can refine this to drop nav/footers, ads, etc.
        page_text = soup.get_text(separator="\n")

        # dump into a PDF
        text_to_pdf(page_text, out_path)
        print(f"⤷ Saved {url} → {fname}")


def build_db():
    # find all generated PDFs
    files = [
        f for f in os.listdir(DOWNLOAD_FOLDER)
        if f.lower().endswith(".pdf") and not f.startswith(".")
    ]

    pages = load_documents(DOWNLOAD_FOLDER, files)
    db    = create_database(pages, openai.api_key)
    db.save_local("vector_database")


urls = crawl_site(START_URL)
scrape_and_render_pdfs(urls, DOWNLOAD_FOLDER)
build_db()
print("Vector database refreshed from live site!")
