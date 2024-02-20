# Resource: https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/scripts/prepdocs.py

import time
from typing import List
import openai
import tiktoken

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

# In-module caching
open_ai_token_cache = {}
CACHE_KEY_TOKEN_CRED = "openai_token_cred"
CACHE_KEY_CREATED_TIME = "created_time"
CACHE_KEY_TOKEN_TYPE = "token_type"

# Embedding batch support section
SUPPORTED_BATCH_AOAI_MODEL = {
    "text-embedding-ada-002": {"token_limit": 8100, "max_batch_size": 16}
}
EMBEDDING_MODEL_NAME = "text-embedding-ada-002"


# Re-try function and helper function
def calculate_tokens_emb_aoai(input: str, embedding_model: str = EMBEDDING_MODEL_NAME):
    encoding = tiktoken.encoding_for_model(embedding_model)
    return len(encoding.encode(input))


def before_retry_sleep(retry_state):
    print("Rate limited on the OpenAI embeddings API, sleeping before retrying...")


def refresh_openai_token():
    """
    Refresh OpenAI token every 5 minutes
    """
    if (
        CACHE_KEY_TOKEN_TYPE in open_ai_token_cache
        and open_ai_token_cache[CACHE_KEY_TOKEN_TYPE] == "azure_ad"
        and open_ai_token_cache[CACHE_KEY_CREATED_TIME] + 300 < time.time()
    ):
        token_cred = open_ai_token_cache[CACHE_KEY_TOKEN_CRED]
        openai.api_key = token_cred.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token
        open_ai_token_cache[CACHE_KEY_CREATED_TIME] = time.time()


# Main section


@retry(
    retry=retry_if_exception_type(openai.error.RateLimitError),
    wait=wait_random_exponential(min=15, max=60),
    stop=stop_after_attempt(15),
    before_sleep=before_retry_sleep,
)
def compute_embedding(
    text: str,
    openai_api_type: str = "azure",
    embedding_deployment: str = EMBEDDING_MODEL_NAME,
    embedding_model: str = EMBEDDING_MODEL_NAME,
):
    """Non-batch compute embedding

    Args:
        text (str): The text to be embedded
        openai_api_tye (str, optional): OpenAI API endpoint type. Defaults to "azure".
        embedding_deployment (str, optional): The deployment name. Defaults to EMBEDDING_MODEL_NAME.
        embedding_model (str, optional): The model name. Defaults to EMBEDDING_MODEL_NAME.

    Returns:
        List[float]: The embedding vector
    """
    refresh_openai_token()
    embedding_args = (
        {"deployment_id": embedding_deployment} if openai_api_type == "azure" else {}
    )
    return openai.Embedding.create(**embedding_args, model=embedding_model, input=text)[
        "data"
    ][0]["embedding"]


@retry(
    retry=retry_if_exception_type(openai.error.RateLimitError),
    wait=wait_random_exponential(min=15, max=60),
    stop=stop_after_attempt(15),
    before_sleep=before_retry_sleep,
)
def compute_embedding_in_batch(
    texts: List[str],
    openai_api_type: str = "azure",
    embedding_deployment: str = EMBEDDING_MODEL_NAME,
    embedding_model: str = EMBEDDING_MODEL_NAME,
):
    """Batch compute embedding

    Args:
        texts (List[str]): The list of text to be embedded. The list length should not
            exceed the max-batch-limit of specified deployment
        openai_api_tye (str, optional): OpenAI API endpoint type. Defaults to "azure".
        embedding_deployment (str, optional): The deployment name. Defaults to EMBEDDING_MODEL_NAME.
        embedding_model (str, optional): The model name. Defaults to EMBEDDING_MODEL_NAME.

    Returns:
        List[float]: The embedding vector
    """
    refresh_openai_token()
    embedding_args = (
        {"deployment_id": embedding_deployment} if openai_api_type == "azure" else {}
    )
    emb_response = openai.Embedding.create(
        **embedding_args, model=embedding_model, input=texts
    )
    return [data.embedding for data in emb_response.data]


def update_embeddings_in_batch(
    sections: List[dict],
    token_limit: int = SUPPORTED_BATCH_AOAI_MODEL[EMBEDDING_MODEL_NAME]["token_limit"],
    max_batch_size: int = SUPPORTED_BATCH_AOAI_MODEL[EMBEDDING_MODEL_NAME][
        "max_batch_size"
    ],
    is_verbose=True,
    embedding_deployment: str = EMBEDDING_MODEL_NAME,
    embedding_model: str = EMBEDDING_MODEL_NAME,
    openai_api_type="azure",
):
    """Wrap around the compute-embedding-in-batch, perform batching (with max-token and max-batch limit logic)
    and mapping to original `section` structure

    Args:
        sections (List[dict]): List of to-be-embedded sections
        token_limit (int, optional): Token limit of model. Defaults to SUPPORTED_BATCH_AOAI_MODEL[EMBEDDING_MODEL_NAME]["token_limit"].
        max_batch_size (int, optional): Batch limit of model. Defaults to SUPPORTED_BATCH_AOAI_MODEL[EMBEDDING_MODEL_NAME][ "max_batch_size" ].
        is_verbose (bool, optional): Verbose. Defaults to True.
        embedding_deployment (str, optional): Model deployment name. Defaults to EMBEDDING_MODEL_NAME.
        embedding_model (str, optional): Model name. Defaults to EMBEDDING_MODEL_NAME.
        openai_api_type (str, optional): Deployment type/host. Defaults to "azure".

    Yields:
        dict: The input sections with calculated embedding
    """
    batch_queue: List[dict] = []
    copy_s: List[dict] = []
    batch_response = {}
    token_count = 0
    for s in sections:
        token_count += calculate_tokens_emb_aoai(s["content"], embedding_model)
        if token_count < token_limit and len(batch_queue) < max_batch_size:
            batch_queue.append(s)
            copy_s.append(s)
        else:
            emb_responses = compute_embedding_in_batch(
                [item["content"] for item in batch_queue],
                openai_api_type=openai_api_type,
                embedding_deployment=embedding_deployment,
                embedding_model=embedding_model,
            )
            if is_verbose:
                print(
                    f"Batch Completed. Batch size  {len(batch_queue)} Token count {token_count}"
                )
            for emb, item in zip(emb_responses, batch_queue):
                batch_response[item["id"]] = emb
            batch_queue = []
            batch_queue.append(s)
            token_count = calculate_tokens_emb_aoai(s["content"], embedding_model)

    if batch_queue:
        emb_responses = compute_embedding_in_batch(
            [item["content"] for item in batch_queue],
            openai_api_type=openai_api_type,
            embedding_deployment=embedding_deployment,
            embedding_model=embedding_model,
        )
        if is_verbose:
            print(
                f"Batch Completed. Batch size  {len(batch_queue)} Token count {token_count}"
            )
        for emb, item in zip(emb_responses, batch_queue):
            batch_response[item["id"]] = emb

    for s in copy_s:
        s["content_vector"] = batch_response[s["id"]]
        yield s
