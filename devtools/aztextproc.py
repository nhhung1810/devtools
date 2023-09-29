import html
from azure.ai.formrecognizer import (
    DocumentTable,
)

# Azure text processing utils
MAX_SECTION_LENGTH = 1000
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100
SENTENCE_ENDINGS = [".", "!", "?"]
WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
# Resource: https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/scripts/prepdocs.py


def table_to_html(table: DocumentTable) -> str:
    """Parse the Document Table instance of Azure Document get from Form Recognizer API

    Args:
        table (DocumentTable): instance of Table

    Returns:
        str: an HTML string represent the table
    """
    table_html = "<table>"
    rows = [
        sorted(
            [cell for cell in table.cells if cell.row_index == i],
            key=lambda cell: cell.column_index,
        )
        for i in range(table.row_count)
    ]
    for row_cells in rows:
        table_html += "<tr>"
        for cell in row_cells:
            tag = (
                "th"
                if (cell.kind == "columnHeader" or cell.kind == "rowHeader")
                else "td"
            )
            cell_spans = ""
            if cell.column_span > 1:
                cell_spans += f" colSpan={cell.column_span}"
            if cell.row_span > 1:
                cell_spans += f" rowSpan={cell.row_span}"
            table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
        table_html += "</tr>"
    table_html += "</table>"
    return table_html


def split_text(
    page_map,
    section_overlap=SECTION_OVERLAP,
    max_section_length=MAX_SECTION_LENGTH,
    sentence_search_limit=SENTENCE_SEARCH_LIMIT,
):
    def find_page(offset):
        num_pages = len(page_map)
        for i in range(num_pages - 1):
            if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
                return i
        return num_pages - 1

    all_text = "".join(p[2] for p in page_map)
    length = len(all_text)
    start = 0
    end = length
    while start + section_overlap < length:
        last_word = -1
        end = start + max_section_length

        if end > length:
            end = length
        else:
            # Try to find the end of the sentence
            while (
                end < length
                and (end - start - max_section_length) < sentence_search_limit
                and all_text[end] not in SENTENCE_ENDINGS
            ):
                if all_text[end] in WORDS_BREAKS:
                    last_word = end
                end += 1
            if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                end = last_word  # Fall back to at least keeping a whole word
        if end < length:
            end += 1

        # Try to find the start of the sentence or at least a whole word boundary
        last_word = -1
        while (
            start > 0
            and start > end - max_section_length - 2 * sentence_search_limit
            and all_text[start] not in SENTENCE_ENDINGS
        ):
            if all_text[start] in WORDS_BREAKS:
                last_word = start
            start -= 1
        if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
            start = last_word
        if start > 0:
            start += 1

        # Yield the result -> force yield on keyword, not a work break
        if all_text[start] in WORDS_BREAKS:
            start += 1
        section_text = all_text[start:end]
        yield (section_text, find_page(start), find_page(end))

        last_table_start = section_text.rfind("<table")
        if (
            last_table_start > 2 * sentence_search_limit
            and last_table_start > section_text.rfind("</table")
        ):
            # If the section ends with an unclosed table, we need to start the next section with the table.
            # If table starts inside SENTENCE_SEARCH_LIMIT, we ignore it, as that will cause an infinite
            # loop for tables longer than MAX_SECTION_LENGTH
            # If last table starts inside SECTION_OVERLAP, keep overlapping
            start = min(end - section_overlap, start + last_table_start)
        else:
            start = end - section_overlap

    if start + section_overlap < end:
        yield (all_text[start:end], find_page(start), find_page(end))
