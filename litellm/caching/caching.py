# +-----------------------------------------------+
# |                                               |
# |           Give Feedback / Get Help            |
# | https://github.com/BerriAI/litellm/issues/new |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import ast
import asyncio
import hashlib
import inspect
import io
import json
import logging
import time
import traceback
from enum import Enum
from typing import Any, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel

import litellm
from litellm._logging import verbose_logger
from litellm.types.caching import *
from litellm.types.utils import all_litellm_params

from .base_cache import BaseCache
from .disk_cache import DiskCache
from .dual_cache import DualCache
from .in_memory_cache import InMemoryCache
from .qdrant_semantic_cache import QdrantSemanticCache
from .redis_cache import RedisCache
from .redis_semantic_cache import RedisSemanticCache
from .s3_cache import S3Cache


def print_verbose(print_statement):
    try:
        verbose_logger.debug(print_statement)
        if litellm.set_verbose:
            print(print_statement)  # noqa
    except Exception:
        pass


class CacheMode(str, Enum):
    default_on = "default_on"
    default_off = "default_off"


#### LiteLLM.Completion / Embedding Cache ####
class Cache:
    def __init__(
        self,
        type: Optional[LiteLLMCacheType] = LiteLLMCacheType.LOCAL,
        mode: Optional[
            CacheMode
        ] = CacheMode.default_on,  # when default_on cache is always on, when default_off cache is opt in
        host: Optional[str] = None,
        port: Optional[str] = None,
        password: Optional[str] = None,
        namespace: Optional[str] = None,
        ttl: Optional[float] = None,
        default_in_memory_ttl: Optional[float] = None,
        default_in_redis_ttl: Optional[float] = None,
        similarity_threshold: Optional[float] = None,
        supported_call_types: Optional[List[CachingSupportedCallTypes]] = [
            "completion",
            "acompletion",
            "embedding",
            "aembedding",
            "atranscription",
            "transcription",
            "atext_completion",
            "text_completion",
            "arerank",
            "rerank",
        ],
        # s3 Bucket, boto3 configuration
        s3_bucket_name: Optional[str] = None,
        s3_region_name: Optional[str] = None,
        s3_api_version: Optional[str] = None,
        s3_use_ssl: Optional[bool] = True,
        s3_verify: Optional[Union[bool, str]] = None,
        s3_endpoint_url: Optional[str] = None,
        s3_aws_access_key_id: Optional[str] = None,
        s3_aws_secret_access_key: Optional[str] = None,
        s3_aws_session_token: Optional[str] = None,
        s3_config: Optional[Any] = None,
        s3_path: Optional[str] = None,
        redis_semantic_cache_use_async=False,
        redis_semantic_cache_embedding_model="text-embedding-ada-002",
        redis_flush_size: Optional[int] = None,
        redis_startup_nodes: Optional[List] = None,
        disk_cache_dir=None,
        qdrant_api_base: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        qdrant_collection_name: Optional[str] = None,
        qdrant_quantization_config: Optional[str] = None,
        qdrant_semantic_cache_embedding_model="text-embedding-ada-002",
        **kwargs,
    ):
        """
        Initializes the cache based on the given type.

        Args:
            type (str, optional): The type of cache to initialize. Can be "local", "redis", "redis-semantic", "qdrant-semantic", "s3" or "disk". Defaults to "local".

            # Redis Cache Args
            host (str, optional): The host address for the Redis cache. Required if type is "redis".
            port (int, optional): The port number for the Redis cache. Required if type is "redis".
            password (str, optional): The password for the Redis cache. Required if type is "redis".
            namespace (str, optional): The namespace for the Redis cache. Required if type is "redis".
            ttl (float, optional): The ttl for the Redis cache
            redis_flush_size (int, optional): The number of keys to flush at a time. Defaults to 1000. Only used if batch redis set caching is used.
            redis_startup_nodes (list, optional): The list of startup nodes for the Redis cache. Defaults to None.

            # Qdrant Cache Args
            qdrant_api_base (str, optional): The url for your qdrant cluster. Required if type is "qdrant-semantic".
            qdrant_api_key (str, optional): The api_key for the local or cloud qdrant cluster.
            qdrant_collection_name (str, optional): The name for your qdrant collection. Required if type is "qdrant-semantic".
            similarity_threshold (float, optional): The similarity threshold for semantic-caching, Required if type is "redis-semantic" or "qdrant-semantic".

            # Disk Cache Args
            disk_cache_dir (str, optional): The directory for the disk cache. Defaults to None.

            # S3 Cache Args
            s3_bucket_name (str, optional): The bucket name for the s3 cache. Defaults to None.
            s3_region_name (str, optional): The region name for the s3 cache. Defaults to None.
            s3_api_version (str, optional): The api version for the s3 cache. Defaults to None.
            s3_use_ssl (bool, optional): The use ssl for the s3 cache. Defaults to True.
            s3_verify (bool, optional): The verify for the s3 cache. Defaults to None.
            s3_endpoint_url (str, optional): The endpoint url for the s3 cache. Defaults to None.
            s3_aws_access_key_id (str, optional): The aws access key id for the s3 cache. Defaults to None.
            s3_aws_secret_access_key (str, optional): The aws secret access key for the s3 cache. Defaults to None.
            s3_aws_session_token (str, optional): The aws session token for the s3 cache. Defaults to None.
            s3_config (dict, optional): The config for the s3 cache. Defaults to None.

            # Common Cache Args
            supported_call_types (list, optional): List of call types to cache for. Defaults to cache == on for all call types.
            **kwargs: Additional keyword arguments for redis.Redis() cache

        Raises:
            ValueError: If an invalid cache type is provided.

        Returns:
            None. Cache is set as a litellm param
        """
        if type == LiteLLMCacheType.REDIS:
            self.cache: BaseCache = RedisCache(
                host=host,
                port=port,
                password=password,
                redis_flush_size=redis_flush_size,
                startup_nodes=redis_startup_nodes,
                **kwargs,
            )
        elif type == LiteLLMCacheType.REDIS_SEMANTIC:
            self.cache = RedisSemanticCache(
                host=host,
                port=port,
                password=password,
                similarity_threshold=similarity_threshold,
                use_async=redis_semantic_cache_use_async,
                embedding_model=redis_semantic_cache_embedding_model,
                **kwargs,
            )
        elif type == LiteLLMCacheType.QDRANT_SEMANTIC:
            self.cache = QdrantSemanticCache(
                qdrant_api_base=qdrant_api_base,
                qdrant_api_key=qdrant_api_key,
                collection_name=qdrant_collection_name,
                similarity_threshold=similarity_threshold,
                quantization_config=qdrant_quantization_config,
                embedding_model=qdrant_semantic_cache_embedding_model,
            )
        elif type == LiteLLMCacheType.LOCAL:
            self.cache = InMemoryCache()
        elif type == LiteLLMCacheType.S3:
            self.cache = S3Cache(
                s3_bucket_name=s3_bucket_name,
                s3_region_name=s3_region_name,
                s3_api_version=s3_api_version,
                s3_use_ssl=s3_use_ssl,
                s3_verify=s3_verify,
                s3_endpoint_url=s3_endpoint_url,
                s3_aws_access_key_id=s3_aws_access_key_id,
                s3_aws_secret_access_key=s3_aws_secret_access_key,
                s3_aws_session_token=s3_aws_session_token,
                s3_config=s3_config,
                s3_path=s3_path,
                **kwargs,
            )
        elif type == LiteLLMCacheType.DISK:
            self.cache = DiskCache(disk_cache_dir=disk_cache_dir)
        if "cache" not in litellm.input_callback:
            litellm.input_callback.append("cache")
        if "cache" not in litellm.success_callback:
            litellm.success_callback.append("cache")
        if "cache" not in litellm._async_success_callback:
            litellm._async_success_callback.append("cache")
        self.supported_call_types = supported_call_types  # default to ["completion", "acompletion", "embedding", "aembedding"]
        self.type = type
        self.namespace = namespace
        self.redis_flush_size = redis_flush_size
        self.ttl = ttl
        self.mode: CacheMode = mode or CacheMode.default_on

        if self.type == LiteLLMCacheType.LOCAL and default_in_memory_ttl is not None:
            self.ttl = default_in_memory_ttl

        if (
            self.type == LiteLLMCacheType.REDIS
            or self.type == LiteLLMCacheType.REDIS_SEMANTIC
        ) and default_in_redis_ttl is not None:
            self.ttl = default_in_redis_ttl

        if self.namespace is not None and isinstance(self.cache, RedisCache):
            self.cache.namespace = self.namespace

    def get_cache_key(self, *args, **kwargs) -> str:  # noqa: PLR0915
        """
        Get the cache key for the given arguments.

        Args:
            *args: args to litellm.completion() or embedding()
            **kwargs: kwargs to litellm.completion() or embedding()

        Returns:
            str: The cache key generated from the arguments, or None if no cache key could be generated.
        """
        cache_key = ""
        print_verbose(f"\nGetting Cache key. Kwargs: {kwargs}")

        # for streaming, we use preset_cache_key. It's created in wrapper(), we do this because optional params like max_tokens, get transformed for bedrock -> max_new_tokens
        if kwargs.get("litellm_params", {}).get("preset_cache_key", None) is not None:
            _preset_cache_key = kwargs.get("litellm_params", {}).get(
                "preset_cache_key", None
            )
            print_verbose(f"\nReturning preset cache key: {_preset_cache_key}")
            return _preset_cache_key

        # sort kwargs by keys, since model: [gpt-4, temperature: 0.2, max_tokens: 200] == [temperature: 0.2, max_tokens: 200, model: gpt-4]
        completion_kwargs = [
            "model",
            "messages",
            "prompt",
            "temperature",
            "top_p",
            "n",
            "stop",
            "max_tokens",
            "presence_penalty",
            "frequency_penalty",
            "logit_bias",
            "user",
            "response_format",
            "seed",
            "tools",
            "tool_choice",
            "stream",
        ]
        embedding_only_kwargs = [
            "input",
            "encoding_format",
        ]  # embedding kwargs = model, input, user, encoding_format. Model, user are checked in completion_kwargs
        transcription_only_kwargs = [
            "file",
            "language",
        ]
        rerank_only_kwargs = [
            "top_n",
            "rank_fields",
            "return_documents",
            "max_chunks_per_doc",
            "documents",
            "query",
        ]
        # combined_kwargs - NEEDS to be ordered across get_cache_key(). Do not use a set()
        combined_kwargs = (
            completion_kwargs
            + embedding_only_kwargs
            + transcription_only_kwargs
            + rerank_only_kwargs
        )
        litellm_param_kwargs = all_litellm_params
        for param in kwargs:
            if param in combined_kwargs:
                # check if param == model and model_group is passed in, then override model with model_group
                if param == "model":
                    model_group = None
                    caching_group = None
                    metadata = kwargs.get("metadata", None)
                    litellm_params = kwargs.get("litellm_params", {})
                    if metadata is not None:
                        model_group = metadata.get("model_group")
                        model_group = metadata.get("model_group", None)
                        caching_groups = metadata.get("caching_groups", None)
                        if caching_groups:
                            for group in caching_groups:
                                if model_group in group:
                                    caching_group = group
                                    break
                    if litellm_params is not None:
                        metadata = litellm_params.get("metadata", None)
                        if metadata is not None:
                            model_group = metadata.get("model_group", None)
                            caching_groups = metadata.get("caching_groups", None)
                            if caching_groups:
                                for group in caching_groups:
                                    if model_group in group:
                                        caching_group = group
                                        break
                    param_value = (
                        caching_group or model_group or kwargs[param]
                    )  # use caching_group, if set then model_group if it exists, else use kwargs["model"]
                elif param == "file":
                    file = kwargs.get("file")
                    metadata = kwargs.get("metadata", {})
                    litellm_params = kwargs.get("litellm_params", {})

                    # get checksum of file content
                    param_value = (
                        metadata.get("file_checksum")
                        or getattr(file, "name", None)
                        or metadata.get("file_name")
                        or litellm_params.get("file_name")
                    )
                else:
                    if kwargs[param] is None:
                        continue  # ignore None params
                    param_value = kwargs[param]
                cache_key += f"{str(param)}: {str(param_value)}"
            elif (
                param not in litellm_param_kwargs
            ):  # check if user passed in optional param - e.g. top_k
                if (
                    litellm.enable_caching_on_provider_specific_optional_params is True
                ):  # feature flagged for now
                    if kwargs[param] is None:
                        continue  # ignore None params
                    param_value = kwargs[param]
                    cache_key += f"{str(param)}: {str(param_value)}"

        print_verbose(f"\nCreated cache key: {cache_key}")
        # Use hashlib to create a sha256 hash of the cache key
        hash_object = hashlib.sha256(cache_key.encode())
        # Hexadecimal representation of the hash
        hash_hex = hash_object.hexdigest()
        print_verbose(f"Hashed cache key (SHA-256): {hash_hex}")
        if kwargs.get("metadata", {}).get("redis_namespace", None) is not None:
            _namespace = kwargs.get("metadata", {}).get("redis_namespace", None)
            hash_hex = f"{_namespace}:{hash_hex}"
            print_verbose(f"Hashed Key with Namespace: {hash_hex}")
        elif self.namespace is not None:
            hash_hex = f"{self.namespace}:{hash_hex}"
            print_verbose(f"Hashed Key with Namespace: {hash_hex}")
        return hash_hex

    def generate_streaming_content(self, content):
        chunk_size = 5  # Adjust the chunk size as needed
        for i in range(0, len(content), chunk_size):
            yield {
                "choices": [
                    {
                        "delta": {
                            "role": "assistant",
                            "content": content[i : i + chunk_size],
                        }
                    }
                ]
            }
            time.sleep(0.02)

    def _get_cache_logic(
        self,
        cached_result: Optional[Any],
        max_age: Optional[float],
    ):
        """
        Common get cache logic across sync + async implementations
        """
        # Check if a timestamp was stored with the cached response
        if (
            cached_result is not None
            and isinstance(cached_result, dict)
            and "timestamp" in cached_result
        ):
            timestamp = cached_result["timestamp"]
            current_time = time.time()

            # Calculate age of the cached response
            response_age = current_time - timestamp

            # Check if the cached response is older than the max-age
            if max_age is not None and response_age > max_age:
                return None  # Cached response is too old

            # If the response is fresh, or there's no max-age requirement, return the cached response
            # cached_response is in `b{} convert it to ModelResponse
            cached_response = cached_result.get("response")
            try:
                if isinstance(cached_response, dict):
                    pass
                else:
                    cached_response = json.loads(
                        cached_response  # type: ignore
                    )  # Convert string to dictionary
            except Exception:
                cached_response = ast.literal_eval(cached_response)  # type: ignore
            return cached_response
        return cached_result

    def get_cache(self, *args, **kwargs):
        """
        Retrieves the cached result for the given arguments.

        Args:
            *args: args to litellm.completion() or embedding()
            **kwargs: kwargs to litellm.completion() or embedding()

        Returns:
            The cached result if it exists, otherwise None.
        """
        try:  # never block execution
            if self.should_use_cache(*args, **kwargs) is not True:
                return
            messages = kwargs.get("messages", [])
            if "cache_key" in kwargs:
                cache_key = kwargs["cache_key"]
            else:
                cache_key = self.get_cache_key(*args, **kwargs)
            if cache_key is not None:
                cache_control_args = kwargs.get("cache", {})
                max_age = cache_control_args.get(
                    "s-max-age", cache_control_args.get("s-maxage", float("inf"))
                )
                cached_result = self.cache.get_cache(cache_key, messages=messages)
                return self._get_cache_logic(
                    cached_result=cached_result, max_age=max_age
                )
        except Exception:
            print_verbose(f"An exception occurred: {traceback.format_exc()}")
            return None

    async def async_get_cache(self, *args, **kwargs):
        """
        Async get cache implementation.

        Used for embedding calls in async wrapper
        """
        try:  # never block execution
            if self.should_use_cache(*args, **kwargs) is not True:
                return

            kwargs.get("messages", [])
            if "cache_key" in kwargs:
                cache_key = kwargs["cache_key"]
            else:
                cache_key = self.get_cache_key(*args, **kwargs)
            if cache_key is not None:
                cache_control_args = kwargs.get("cache", {})
                max_age = cache_control_args.get(
                    "s-max-age", cache_control_args.get("s-maxage", float("inf"))
                )
                cached_result = await self.cache.async_get_cache(
                    cache_key, *args, **kwargs
                )
                return self._get_cache_logic(
                    cached_result=cached_result, max_age=max_age
                )
        except Exception:
            print_verbose(f"An exception occurred: {traceback.format_exc()}")
            return None

    def _add_cache_logic(self, result, *args, **kwargs):
        """
        Common implementation across sync + async add_cache functions
        """
        try:
            if "cache_key" in kwargs:
                cache_key = kwargs["cache_key"]
            else:
                cache_key = self.get_cache_key(*args, **kwargs)
            if cache_key is not None:
                if isinstance(result, BaseModel):
                    result = result.model_dump_json()

                ## DEFAULT TTL ##
                if self.ttl is not None:
                    kwargs["ttl"] = self.ttl
                ## Get Cache-Controls ##
                _cache_kwargs = kwargs.get("cache", None)
                if isinstance(_cache_kwargs, dict):
                    for k, v in _cache_kwargs.items():
                        if k == "ttl":
                            kwargs["ttl"] = v

                cached_data = {"timestamp": time.time(), "response": result}
                return cache_key, cached_data, kwargs
            else:
                raise Exception("cache key is None")
        except Exception as e:
            raise e

    def add_cache(self, result, *args, **kwargs):
        """
        Adds a result to the cache.

        Args:
            *args: args to litellm.completion() or embedding()
            **kwargs: kwargs to litellm.completion() or embedding()

        Returns:
            None
        """
        try:
            if self.should_use_cache(*args, **kwargs) is not True:
                return
            cache_key, cached_data, kwargs = self._add_cache_logic(
                result=result, *args, **kwargs
            )
            self.cache.set_cache(cache_key, cached_data, **kwargs)
        except Exception as e:
            verbose_logger.exception(f"LiteLLM Cache: Excepton add_cache: {str(e)}")

    async def async_add_cache(self, result, *args, **kwargs):
        """
        Async implementation of add_cache
        """
        try:
            if self.should_use_cache(*args, **kwargs) is not True:
                return
            if self.type == "redis" and self.redis_flush_size is not None:
                # high traffic - fill in results in memory and then flush
                await self.batch_cache_write(result, *args, **kwargs)
            else:
                cache_key, cached_data, kwargs = self._add_cache_logic(
                    result=result, *args, **kwargs
                )
                await self.cache.async_set_cache(cache_key, cached_data, **kwargs)
        except Exception as e:
            verbose_logger.exception(f"LiteLLM Cache: Excepton add_cache: {str(e)}")

    async def async_add_cache_pipeline(self, result, *args, **kwargs):
        """
        Async implementation of add_cache for Embedding calls

        Does a bulk write, to prevent using too many clients
        """
        try:
            if self.should_use_cache(*args, **kwargs) is not True:
                return

            # set default ttl if not set
            if self.ttl is not None:
                kwargs["ttl"] = self.ttl

            cache_list = []
            for idx, i in enumerate(kwargs["input"]):
                preset_cache_key = self.get_cache_key(*args, **{**kwargs, "input": i})
                kwargs["cache_key"] = preset_cache_key
                embedding_response = result.data[idx]
                cache_key, cached_data, kwargs = self._add_cache_logic(
                    result=embedding_response,
                    *args,
                    **kwargs,
                )
                cache_list.append((cache_key, cached_data))
            async_set_cache_pipeline = getattr(
                self.cache, "async_set_cache_pipeline", None
            )
            if async_set_cache_pipeline:
                await async_set_cache_pipeline(cache_list=cache_list, **kwargs)
            else:
                tasks = []
                for val in cache_list:
                    tasks.append(self.cache.async_set_cache(val[0], val[1], **kwargs))
                await asyncio.gather(*tasks)
        except Exception as e:
            verbose_logger.exception(f"LiteLLM Cache: Excepton add_cache: {str(e)}")

    def should_use_cache(self, *args, **kwargs):
        """
        Returns true if we should use the cache for LLM API calls

        If cache is default_on then this is True
        If cache is default_off then this is only true when user has opted in to use cache
        """
        if self.mode == CacheMode.default_on:
            return True

        # when mode == default_off -> Cache is opt in only
        _cache = kwargs.get("cache", None)
        verbose_logger.debug("should_use_cache: kwargs: %s; _cache: %s", kwargs, _cache)
        if _cache and isinstance(_cache, dict):
            if _cache.get("use-cache", False) is True:
                return True
        return False

    async def batch_cache_write(self, result, *args, **kwargs):
        cache_key, cached_data, kwargs = self._add_cache_logic(
            result=result, *args, **kwargs
        )
        await self.cache.batch_cache_write(cache_key, cached_data, **kwargs)

    async def ping(self):
        cache_ping = getattr(self.cache, "ping")
        if cache_ping:
            return await cache_ping()
        return None

    async def delete_cache_keys(self, keys):
        cache_delete_cache_keys = getattr(self.cache, "delete_cache_keys")
        if cache_delete_cache_keys:
            return await cache_delete_cache_keys(keys)
        return None

    async def disconnect(self):
        if hasattr(self.cache, "disconnect"):
            await self.cache.disconnect()

    def _supports_async(self) -> bool:
        """
        Internal method to check if the cache type supports async get/set operations

        Only S3 Cache Does NOT support async operations

        """
        if self.type and self.type == LiteLLMCacheType.S3:
            return False
        return True


def enable_cache(
    type: Optional[LiteLLMCacheType] = LiteLLMCacheType.LOCAL,
    host: Optional[str] = None,
    port: Optional[str] = None,
    password: Optional[str] = None,
    supported_call_types: Optional[List[CachingSupportedCallTypes]] = [
        "completion",
        "acompletion",
        "embedding",
        "aembedding",
        "atranscription",
        "transcription",
        "atext_completion",
        "text_completion",
        "arerank",
        "rerank",
    ],
    **kwargs,
):
    """
    Enable cache with the specified configuration.

    Args:
        type (Optional[Literal["local", "redis", "s3", "disk"]]): The type of cache to enable. Defaults to "local".
        host (Optional[str]): The host address of the cache server. Defaults to None.
        port (Optional[str]): The port number of the cache server. Defaults to None.
        password (Optional[str]): The password for the cache server. Defaults to None.
        supported_call_types (Optional[List[Literal["completion", "acompletion", "embedding", "aembedding"]]]):
            The supported call types for the cache. Defaults to ["completion", "acompletion", "embedding", "aembedding"].
        **kwargs: Additional keyword arguments.

    Returns:
        None

    Raises:
        None
    """
    print_verbose("LiteLLM: Enabling Cache")
    if "cache" not in litellm.input_callback:
        litellm.input_callback.append("cache")
    if "cache" not in litellm.success_callback:
        litellm.success_callback.append("cache")
    if "cache" not in litellm._async_success_callback:
        litellm._async_success_callback.append("cache")

    if litellm.cache is None:
        litellm.cache = Cache(
            type=type,
            host=host,
            port=port,
            password=password,
            supported_call_types=supported_call_types,
            **kwargs,
        )
    print_verbose(f"LiteLLM: Cache enabled, litellm.cache={litellm.cache}")
    print_verbose(f"LiteLLM Cache: {vars(litellm.cache)}")


def update_cache(
    type: Optional[LiteLLMCacheType] = LiteLLMCacheType.LOCAL,
    host: Optional[str] = None,
    port: Optional[str] = None,
    password: Optional[str] = None,
    supported_call_types: Optional[List[CachingSupportedCallTypes]] = [
        "completion",
        "acompletion",
        "embedding",
        "aembedding",
        "atranscription",
        "transcription",
        "atext_completion",
        "text_completion",
        "arerank",
        "rerank",
    ],
    **kwargs,
):
    """
    Update the cache for LiteLLM.

    Args:
        type (Optional[Literal["local", "redis", "s3", "disk"]]): The type of cache. Defaults to "local".
        host (Optional[str]): The host of the cache. Defaults to None.
        port (Optional[str]): The port of the cache. Defaults to None.
        password (Optional[str]): The password for the cache. Defaults to None.
        supported_call_types (Optional[List[Literal["completion", "acompletion", "embedding", "aembedding"]]]):
            The supported call types for the cache. Defaults to ["completion", "acompletion", "embedding", "aembedding"].
        **kwargs: Additional keyword arguments for the cache.

    Returns:
        None

    """
    print_verbose("LiteLLM: Updating Cache")
    litellm.cache = Cache(
        type=type,
        host=host,
        port=port,
        password=password,
        supported_call_types=supported_call_types,
        **kwargs,
    )
    print_verbose(f"LiteLLM: Cache Updated, litellm.cache={litellm.cache}")
    print_verbose(f"LiteLLM Cache: {vars(litellm.cache)}")


def disable_cache():
    """
    Disable the cache used by LiteLLM.

    This function disables the cache used by the LiteLLM module. It removes the cache-related callbacks from the input_callback, success_callback, and _async_success_callback lists. It also sets the litellm.cache attribute to None.

    Parameters:
    None

    Returns:
    None
    """
    from contextlib import suppress

    print_verbose("LiteLLM: Disabling Cache")
    with suppress(ValueError):
        litellm.input_callback.remove("cache")
        litellm.success_callback.remove("cache")
        litellm._async_success_callback.remove("cache")

    litellm.cache = None
    print_verbose(f"LiteLLM: Cache disabled, litellm.cache={litellm.cache}")
