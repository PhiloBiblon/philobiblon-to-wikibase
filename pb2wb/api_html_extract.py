#!/usr/bin/env python3
import argparse
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, NavigableString
from common.settings import TEMP_DICT
import pandas as pd

TEMP_DICT['TEMP_WB'] = 'FACTGRID'

def slice_from_h3_to_first_comment(full_html: str) -> str:
    """
    Return substring from the first <h3 ...> up to (but not including) the first <!-- ... -->
    after that point. If no comment is found, return from <h3> to the end.
    """
    if not full_html:
        print("Empty HTML from API")
        return ""

    lower = full_html.lower()
    start_idx = lower.find("<h3")
    if start_idx == -1:
        print("No <h3> found in talk page HTML, skipping extraction.")
        return ""

    end_idx = full_html.find("<!--", start_idx)
    if end_idx == -1:
        end_idx = len(full_html)

    return full_html[start_idx:end_idx]

def rewrite_links_as_bracket_text(html: str, base_url: str | None = None) -> str:

    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a"):
        #print(f"Processing anchor: {a}")
        href = (a.get("href") or "").strip()
        text = a.get_text(" ", strip=True)  # tolerate nested tags

        # unwrap anchors without href
        if not href:
            a.unwrap()
            continue

        # resolve relative links if base_url given
        if base_url:
            href = urljoin(base_url, href)

        # normalize anchor text like "(Carlos V)" → "Carlos V"
        if text.startswith("(") and text.endswith(")") and len(text) >= 2:
            text = text[1:-1].strip()

        # build replacement string
        replacement = f'[{href}]' if not text or text == href else f'[{href} ({text})]'
        #print(f"Replacing anchor with: {replacement}")
        a.replace_with(NavigableString(replacement))

    return str(soup)

def get_notes_html(qid: str) -> str:
    from notes import notes
    html = notes.get_notes_html(qid)
    if not html:
        print(f"No HTML content found for QID {qid}.")
        return ""
    return html

def replace_notes_html(qid: str, new_html: str):
    from notes import notes
    if not new_html:
        print(f"No new HTML content provided for QID {qid}. No changes made.")
        return

    notes.replace_notes_html(qid, new_html)
    print(f"Talk page HTML for {qid} successfully replaced.")

def main():
    ap = argparse.ArgumentParser(description="Extract talk-page HTML (from <h3> to first <!--) and rewrite links.")
    ap.add_argument("--qid", required=False, help="FactGrid QID (e.g., Q1083011)")
    ap.add_argument("--base_url", default="https://database.factgrid.de", help="Base URL for resolving relative links")
    ap.add_argument("--csv", help='Path to CSV file with QIDs to process. If provided, --qid is ignored.')
    ap.add_argument("--dry_run", action="store_true", help="If set, no changes will be made to the talk page.")
    ap.add_argument('--limit', default=None ,type=int, required=False, help='Limit the number of notes to process.  This is useful for testing purposes.')
    args = ap.parse_args()
    count = 0

    if args.csv:
        df = pd.read_csv(args.csv, low_memory=False)
        # Extract Qnumber from item, example: https://database.factgrid.de/entity/Q10441 to Q10441
        qids = df['item'].str.extract(r'/entity/(Q\d+)')[0].tolist()
        print(f"Loaded QIDs from {args.csv}: {qids}")
    else:
        qids = [args.qid]

    for qid in qids:
        if count >= (args.limit or float('inf')):
            print(f"Reached limit of {args.limit} items, stopping.")
            break
        if not args.dry_run:
            print(f"Processing QID: {qid}")
        else:
            print(f"Dry run for QID: {qid} (no changes will be made)")
            continue

        html = get_notes_html(qid)
        fragment = slice_from_h3_to_first_comment(html)
        updated = rewrite_links_as_bracket_text(fragment, base_url=args.base_url)
        if updated:
            print(f'Talk page HTML for {qid} successfully extracted.  Preparing to delete old notes and replace with new HTML.')
            replace_notes_html(qid, updated)
            count += 1
        else:
            print(f'No valid HTML content extracted for {qid}. No changes made to notes.')
    print(f"Processed {count} QIDs.")

if __name__ == "__main__":
    main()