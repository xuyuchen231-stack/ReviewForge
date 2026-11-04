"""Explicitly authorized self-hosted Free.ai route; no premium substitution."""
from urllib.parse import urlsplit

def is_freeai(base):
    url=urlsplit(base)
    return url.scheme=='https' and url.hostname=='api.free.ai' and url.path.rstrip('/')=='/v1'

def allowed_freeai(api):
    return is_freeai(api.base) and api.freeai_self_hosted_only and all(m=='qwen7b' for m in (api.model,api.reviewer_model,api.fallback_model))

def available_for_input(api,system,user):
    return not is_freeai(api.base) or len(system)+len(user)<=api.freeai_max_input_chars
