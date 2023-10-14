from copy import deepcopy
from typing import Tuple, Union
from typing_extensions import Self
from azure.core.credentials import AzureKeyCredential
from typing import List
from azure.ai.formrecognizer import (
    AnalyzeResult,
    DocumentPage,
    DocumentParagraph,
    DocumentTable,
    DocumentAnalysisClient,
)

from aztextproc import table_to_html
from tqdm import tqdm

from misc.io import load_json, write_json
from misc.decorator import time_benchmark_decorator


class EnhancePage:
    def __init__(
        self,
        page: DocumentPage,
        tables: List[DocumentTable],
        paragraphs: List[DocumentParagraph],
        parent_analyze_result: AnalyzeResult,
    ) -> None:
        self.page = page
        self.tables = tables
        self.paragraphs = paragraphs
        self.parent_analyze_result = parent_analyze_result
        self.span_offset = self.page.spans[0].offset
        self.span_length = self.page.spans[0].length

        # Run filter
        self.run_filter_paragraphs()

        pass

    def run_filter_paragraphs(self):
        # NOTE: filter logic is here
        pass

    @classmethod
    def parse_enhance_pages(cls, analyzed_doc: AnalyzeResult) -> List[Self]:
        pages = analyzed_doc.pages
        ps = sorted(analyzed_doc.paragraphs, key=lambda x: x.spans[0].offset)
        ps_idx = 0
        packed_pages = []
        for page_num, page in tqdm(
            enumerate(pages),
            desc="Parsing page, paragraph and table into data structure",
            total=len(pages),
        ):
            page_offset = page.spans[0].offset
            page_length = page.spans[0].length
            current_page_ps = []

            # Track down the paragraph, assume that it sorted by offset
            while ps_idx < len(ps):
                p_offset = ps[ps_idx].spans[0].offset
                if p_offset < page_offset + page_length and p_offset >= page_offset:
                    current_page_ps.append(ps[ps_idx])
                    ps_idx += 1
                else:
                    break
                pass

            # Track down the table of the page
            tables_on_page = [
                table
                for table in analyzed_doc.tables
                if (
                    table.bounding_regions[0].page_number == page_num + 1
                    and len(table.spans) > 0
                )
            ]

            packed_pages.append(
                cls(page, tables_on_page, current_page_ps, analyzed_doc)
            )
            pass

        return packed_pages

    def get_non_overlap_paragraph(self) -> List[DocumentParagraph]:
        paragraph_buffer = deepcopy(self.paragraphs)
        for _, table in enumerate(self.tables):
            for span in table.spans:
                for p_idx, p in enumerate(paragraph_buffer):
                    if p.spans[0].offset in range(
                        span.offset, span.offset + span.length + 1
                    ):
                        paragraph_buffer[p_idx] = None
                        pass
                    pass

                # Filter out the None element
                paragraph_buffer = [p for p in paragraph_buffer if p is not None]
                pass

        return paragraph_buffer

    def to_plain_text(self):
        # Remove all the paragraphs that overlap with the table
        paragraph_buffer = deepcopy(self.paragraphs)
        for _, table in enumerate(self.tables):
            for span in table.spans:
                for p_idx, p in enumerate(paragraph_buffer):
                    if p.spans[0].offset in range(
                        span.offset, span.offset + span.length + 1
                    ):
                        paragraph_buffer[p_idx] = None
                        pass
                    pass

                # Filter out the None element
                paragraph_buffer = [p for p in paragraph_buffer if p is not None]
                pass

        content_seq = self._build_joint_content_sequence(paragraph_buffer)

        # Page building
        page_text = ""
        for element in content_seq:
            if isinstance(element, DocumentParagraph):
                # "pageHeader", "pageFooter", "pageNumber", "title", "sectionHeading", "footnote", "formulaBlock".
                p_text = f"{element.role if element.role is not None else 'paragraph'}: {element.content}\n"
                page_text += p_text
                pass
            elif isinstance(element, DocumentTable):
                page_text += table_to_html(element) + "\n"
            pass

        return page_text

    def _build_joint_content_sequence(
        self, paragraph_buffer
    ) -> List[Union[DocumentParagraph, DocumentTable]]:
        """Helper function -> Join a sequence of paragraph and table, base on offset"""
        # 2-pointer iterate section
        page_build_stack: List[Union[DocumentParagraph, DocumentTable]] = []
        paragraph_idx = 0
        table_idx = 0
        while paragraph_idx < len(paragraph_buffer) and table_idx < len(self.tables):
            p_offset = paragraph_buffer[paragraph_idx].spans[0].offset
            table_offset = self.tables[table_idx].spans[0].offset
            if p_offset < table_offset:
                page_build_stack.append(paragraph_buffer[paragraph_idx])
                paragraph_idx += 1
                pass
            else:
                page_build_stack.append(self.tables[table_idx])
                table_idx += 1
            pass

        # 2-pointer leftover handle
        if paragraph_idx < len(paragraph_buffer):
            page_build_stack.extend(paragraph_buffer[paragraph_idx:])
            pass

        if table_idx < len(self.tables):
            page_build_stack.extend(self.tables[table_idx:])
            pass
        return page_build_stack


def create_page_map(analyzed_doc: AnalyzeResult) -> List[Tuple[int, int, str]]:
    """Create the page mapping

    Args:
        analyzed_doc (AnalyzeResult): The analyzed form

    Returns:
        List[Tuple[int, int, str]]: [page-number, string-length-offset, content]
    """
    enhanced_pages: List[EnhancePage] = EnhancePage.parse_enhance_pages(analyzed_doc)
    page_map = []
    offset = 0
    for page_num, page in tqdm(
        enumerate(enhanced_pages),
        desc="Convert page to plain text...",
        total=len(enhanced_pages),
    ):
        page_text = page.to_plain_text()
        page_map.append((page_num, offset, page_text))
        offset += len(page_text)

    return page_map


class AzureDocumentTool:
    def __init__(self) -> None:
        pass

    def run(self, filename: str):
        pass

    @staticmethod
    @time_benchmark_decorator("azformrec.AzureDocumentTool.run_form_recognizer", True)
    def run_form_recognizer(
        filename: str,
        endpoint: str,
        key: str,
        cache_path: str = None,
        is_cache=False,
        verbose=True,
    ) -> AnalyzeResult:
        """Run Form Recognizer - Layout API

        Args:
            filename (str): Path to the PDF file
            cache_path (str, optional): Cache path. Defaults to None.
            is_cache (bool, optional): Is writing to the cache. Defaults to False.
            verbose (bool, optional): Is printing out text. Defaults to True.
            endpoint (str, optional): Endpoint for the FC API. Defaults to FORM_RECOGNIZE_ENDPOINT.
            key (str, optional): Key for the FC API. Defaults to FORM_RECOGNIZE_KEY.

        Returns:
            AnalyzeResult: The analyzed result
        """
        if is_cache:
            assert isinstance(cache_path, str), "Cache path must be defined as str"
            pass

        if verbose:
            print(f"Start analyzed pdf {filename}")

        with open(filename, "rb") as f:
            form_recognizer_client = DocumentAnalysisClient(
                endpoint=endpoint, credential=AzureKeyCredential(key)
            )
            poller = form_recognizer_client.begin_analyze_document(
                "prebuilt-layout", document=f
            )
            analyze_result = poller.result()
            pass

        if is_cache:
            AzureDocumentTool.write_cache_form_recognizer(cache_path, analyze_result)
        return analyze_result

    @staticmethod
    def write_cache_form_recognizer(path, analyze_result: AnalyzeResult):
        write_json(analyze_result.to_dict(), path=path, encoding="utf-16")
        pass

    @staticmethod
    def load_cache_form_recognizer(path):
        return AnalyzeResult().from_dict(load_json(path, encoding="utf-16"))


if __name__ == "__main__":
    filename = "dataset/openai_policy_search/01. S07_SM773_MY.V2.0.pdf"

    # analyzed = run_form_recognizer(filename, is_cache=True)
    # page_map = create_page_map(analyzed_doc=analyzed)
    # sections = []
    # for i, (content, pagenum) in enumerate(split_text(page_map)):
    #     section = {
    #         "id": f"{filename}-page-{i}",
    #         "page_num": pagenum,
    #         "content": content,
    #         "sourcefile": filename,
    #     }
    #     sections.append(section)

    # with open("dataset/sections.json", "w") as out:
    #     json.dump(sections, out)
    pass
