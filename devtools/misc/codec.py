import base64
import urllib
import urllib.parse


class ACSIndexerEncodingConversion:
    """
    ACS's Indexer will generate an (azure) BASE64 encode of the "quoted" blob URL.
    - We will transfer all this encoding into "quoted" as the middle ground.
    From blob storage, filename is in raw version,
    - we will convert it to "quoted" version as the middle ground.

    Finally, this middle ground will be convert to BASE64.
    - The reason we don't directly the used the BASE64 from ACS is because that encoded
    is not universal (the trailing number), which make a one-way decoding.

    The diagram of codec may look like this

      ACS's Indexer  ───────► Quote URL ◄───────── Blob URL
          BASE64                   │              (Unicode)
                                   │
                                   ▼
                             Python BASE64
                                Encoded

    """

    def __init__(self) -> None:
        pass

    def azure_decode(self, base64_url: str) -> str:
        """Decode Azure BASE64 encoded string

        Args:
            base64_url (str): Azure BASE64 encoded string

        Returns:
            str: decoded string and encoded back into UTF8
        """
        padding_len = 4 - (len(base64_url[:-1]) % 4)
        padded_path = base64_url[:-1] + ("=" * padding_len)
        try:
            return base64.b64decode(padded_path).decode("utf-8")
        except Exception:
            return base64.b64decode(base64[:-1]).decode("utf-8")

    def indexer_to_search(
        self,
        base64_url: str,
    ):
        """ACS's Indexer BASE64 convert to Universal BASE64

        Args:
            base64_url (str): ACS's Indexer URL in BASE64 format

        Returns:
            str: the BASE64 string
        """
        # Azure base64 -> quoted (middle ground)
        quoted_url = self.azure_decode(base64_url=base64_url)
        return base64.urlsafe_b64encode(quoted_url.encode("utf-8")).decode("utf-8")

    def blob_to_search(self, blob_url: str) -> str:
        """Azure Blob URL convert to Universal BASE64

        Args:
            blob_url (str): Blob URL

        Returns:
            str: the BASE64 string
        """
        # Blob name -> quoted
        blob_url = blob_url.removeprefix("https://")
        quoted_url = urllib.parse.quote(blob_url)
        quoted_url = "https://" + quoted_url
        return base64.urlsafe_b64encode(quoted_url.encode("utf-8")).decode("utf-8")
