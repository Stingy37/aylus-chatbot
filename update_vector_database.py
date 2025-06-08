import os
import requests
import shutil
import streamlit as st
import openai

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from rag import load_documents, create_database

START_URL       = "https://www.aylus-pearland.org/"
DOWNLOAD_FOLDER = "llm_website_context"
PDF_PREFIX      = "page_"
openai.api_key  = st.secrets["OPENAI_API_KEY"]

FONT_PATH = os.path.join(os.path.dirname(__file__),
                         "scrapper_fonts", "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))


def crawl_site(start_url):
    opts = Options(); opts.headless = True
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    to_visit, visited, all_urls = {start_url}, set(), set()
    while to_visit:
        url = to_visit.pop()
        if url in visited: continue
        visited.add(url)
        driver.get(url)
        for a in driver.find_elements(By.TAG_NAME, "a"):
            try:
                href = a.get_attribute("href") or ""
            except StaleElementReferenceException:
                continue
            if href.startswith(start_url) and href not in all_urls:
                all_urls.add(href)
                to_visit.add(href)
    driver.quit()
    return sorted(all_urls)


def text_to_pdf_reportlab(text: str, dest_path: str):
    """
    Creates a PDF at dest_path from `text`, word‐wrapping to page margins
    and creating new pages as needed. Uses DejaVu Unicode font.
    """
    # Page and font settings
    page_width, page_height = letter
    margin = 40
    usable_width = page_width - 2 * margin
    usable_height = page_height - 2 * margin
    font_name = "DejaVu"
    font_size = 11
    leading = font_size * 1.2

    # Prepare the canvas
    c = canvas.Canvas(dest_path, pagesize=letter)
    c.setFont(font_name, font_size)

    # Pre‐split into paragraphs
    y = page_height - margin
    for para in text.split("\n"):
        # Normalize whitespace
        para = para.strip()
        if not para:
            # blank line: advance by one leading
            y -= leading
            if y < margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = page_height - margin
            continue

        # Split paragraph into words
        words = para.split(" ")
        line = ""
        for word in words:
            # Try appending this word to the current line
            if line:
                test_line = f"{line} {word}"
            else:
                test_line = word
            test_width = pdfmetrics.stringWidth(test_line, font_name, font_size)

            if test_width <= usable_width:
                line = test_line
            else:
                # Flush current line
                c.drawString(margin, y, line)
                y -= leading
                if y < margin:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    y = page_height - margin
                line = word

        # Flush last line of paragraph
        if line:
            c.drawString(margin, y, line)
            y -= leading
            if y < margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = page_height - margin

    c.save()




def scrape_and_render_pdfs(urls, download_folder):
    os.makedirs(download_folder, exist_ok=True)
    print("Generating PDFs with ReportLab:")
    for idx, url in enumerate(urls, 1):
        out_path = os.path.join(download_folder, f"{PDF_PREFIX}{idx}.pdf")
        if os.path.exists(out_path):
            print(f"  • [{idx}/{len(urls)}] Skipped")
            continue
        try:
            print(f"  • [{idx}/{len(urls)}] Fetching…", end="")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            text = BeautifulSoup(resp.text, "html.parser") \
                   .get_text(separator="\n")
            text_to_pdf_reportlab(text, out_path)
            print(" saved")
        except Exception as e:
            print(f"\n    ⚠️ Error on {url}: {e}")

    print("\nAll PDFs generated.\n")


def build_db():
    files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".pdf")]
    pages = load_documents(DOWNLOAD_FOLDER, files)
    db = create_database(pages, openai.api_key)
    db.save_local("vector_database")
    print("Vector DB saved.")


if os.path.exists(DOWNLOAD_FOLDER):
    shutil.rmtree(DOWNLOAD_FOLDER)
urls = crawl_site(START_URL)
scrape_and_render_pdfs(urls, DOWNLOAD_FOLDER)
build_db()
