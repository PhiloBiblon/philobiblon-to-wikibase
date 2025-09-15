#!/usr/bin/env python3
import argparse
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, NavigableString
from common.settings import TEMP_DICT
import pandas as pd
import logging
from datetime import datetime
import time
import re

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    filename=f"html_extract_{timestamp}.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.info("Logging started at %s", timestamp)

TEMP_DICT['TEMP_WB'] = 'FACTGRID'

def slice_from_h3_to_first_comment(full_html: str) -> str:
    """
    Return substring from the first <h3 ...> up to (but not including) the first <!-- ... -->
    after that point. If no comment is found, return from <h3> to the end.
    """
    if not full_html:
        logging.info("Empty HTML from API")
        return ""

    lower = full_html.lower()
    start_idx = lower.find("<h3")
    if start_idx == -1:
        logging.info("No <h3> found in talk page HTML, skipping extraction.")
        return ""

    end_idx = full_html.find("<!--", start_idx)
    if end_idx == -1:
        end_idx = len(full_html)

    return full_html[start_idx:end_idx]

def replace_headers(html: str) -> str:
    header_replace_mapping = {
        'BETA / Bibliografía de Textos Antiguos': 'BETA / Bibliografía Española de Textos Antiguos',
        'BITECA / Bibliografía de Textos Catalanes Antiguos': 'BITECA / Bibliografia de Textos Antics Catalans, Valencians i Balears',
    }
    #print(html)
    # Normalize keys once (strip extra spaces)
    norm_map = { " ".join(k.split()): v for k, v in header_replace_mapping.items() }

    def norm(s: str) -> str:
        # collapse multiple spaces and trim
        return " ".join((s or "").split())

    soup = BeautifulSoup(html, "html.parser")
    candidates = list(soup.select("span.mw-headline")) + \
                 list(soup.find_all(["h1","h2","h3","h4"]))
    for el in candidates:
        current_text = norm(el.get_text(" ", strip=True))
        if not current_text:
            continue

        if current_text in norm_map:
            new_text = norm_map[current_text]
            logging.info(f"Replacing header '{current_text}' with '{new_text}'")
            el.clear()
            el.append(NavigableString(new_text))

    return str(soup)

def rewrite_links_as_bracket_text(html: str, base_url: str | None = None) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a.get("href")
        url = urljoin(base_url, href) if base_url else href
        item_id = url.split("/")[-1]

        # Get the text and remove leading/trailing parentheses only if they enclose the text
        text = a.get_text(" ", strip=True)
        if text.startswith("(") and text.endswith(")") and len(text) > 2:
            text = text[1:-1].strip()

        replacement = f'[[{url}]]' if not text or text == href else f'[[{item_id}|{text}]]'
        a.replace_with(NavigableString(replacement))
    #print("Final HTML:", str(soup))
    return str(soup)

def get_notes_html(qid: str) -> str:
    from notes import notes
    html = notes.get_notes_html(qid)
    if not html:
        logging.info(f"No HTML content found for QID {qid}.")
        return ""
    return html

def replace_notes_html(qid: str, new_html: str):
    from notes import notes
    if not new_html:
        logging.info(f"No new HTML content provided for QID {qid}. No changes made.")
        return

    notes.replace_notes_html(qid, new_html)
    logging.info(f"Talk page HTML for {qid} successfully replaced.")

def main():
    ap = argparse.ArgumentParser(description="Extract talk-page HTML (from <h3> to first <!--) and rewrite links.")
    ap.add_argument("--qid", required=False, help="FactGrid QID (e.g., Q1083011)")
    ap.add_argument("--base_url", default="https://database.factgrid.de", help="Base URL for resolving relative links")
    ap.add_argument("--csv", help='Path to CSV file with QIDs to process. If provided, --qid is ignored.')
    ap.add_argument("--dry_run", action="store_true", help="If set, no changes will be made to the talk page.")
    ap.add_argument('--limit', default=None ,type=int, required=False, help='Limit the number of notes to process.  This is useful for testing purposes.')
    ap.add_argument("--start_item", type=str, default=None, help="If set, start processing from this QID (inclusive).")
    args = ap.parse_args()
    count = 0

    if args.csv:
        df = pd.read_csv(args.csv, low_memory=False)
        # Extract Qnumber from item, example: https://database.factgrid.de/entity/Q10441 to Q10441
        qids = df['item'].str.extract(r'/entity/(Q\d+)')[0].unique().tolist()
        qids = sorted(set(qids), key=lambda x: int(re.search(r'\d+', x).group()))
        #logging.info(f"Loaded QIDs from {args.csv}: {qids}")
        if args.start_item:
            logging.info(f"Starting from item {args.start_item}")
            start_index = qids.index(args.start_item) if args.start_item in qids else None
            qids = qids[start_index:] if start_index is not None else []
    else:
        qids = [args.qid]

    for qid in qids:
        if count >= (args.limit or float('inf')):
            logging.info(f"Reached limit of {args.limit} items, stopping.")
            break
        if not args.dry_run:
            logging.info(f"Processing QID: {qid}")
        else:
            logging.info(f"Dry run for QID: {qid} (no changes will be made)")
            continue
        html = get_notes_html(qid)
        fragment = slice_from_h3_to_first_comment(html)
        bracket_update = rewrite_links_as_bracket_text(fragment, base_url=args.base_url)
        updated = replace_headers(bracket_update)
        if updated:
            #print(updated)
            logging.info(f'Talk page HTML for {qid} successfully extracted.  Preparing to delete old notes and replace with new HTML.')
            replace_notes_html(qid, updated)
            count += 1
        else:
            logging.warning(f'No valid HTML content extracted for {qid}. No changes made to notes.')
    logging.info(f"Processed {count} QIDs.")

if __name__ == "__main__":
    main()
