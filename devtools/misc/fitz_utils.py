import cv2
import io
from PIL import Image
from typing import Tuple
import fitz
from azure.ai import formrecognizer
import numpy as np


def acoord2fcoord(
    fitz_page: fitz.fitz.Page,
    az_page: formrecognizer.DocumentPage,
    az_coord: Tuple[float, float],
) -> Tuple[float]:
    """Convert Azure Form Recognizer's coordinate
    into Fitz-type's coordinate

    Args:
        fitz_page (Page): The fitz_page instance
        az_page (formrecognizer.DocumentPage): Azure page instance
        az_coord (Tuple[float, float]): Azure coordinate

    Returns:
        Tuple[float]: _description_
    """
    fitz_p = fitz_page.get_pixmap()
    return (
        float(fitz_p.width) / float(az_page.width) * az_coord[0],
        float(fitz_p.height) / float(az_page.height) * az_coord[1],
    )


def page2img(page: fitz.fitz.Page):
    pil_image = Image.open(io.BytesIO(page.get_pixmap().pil_tobytes(format="PNG")))
    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    return image
