"""Exact free model allowlist, separate from TokenHarbor weekly allowances."""
from urllib.parse import urlsplit
FREE_MODELS={'deepseek-v4.1-flash-free','glm-5.3-flash-free'}

def is_beatapi(base):
    url=urlsplit(base)
    return url.scheme=='https' and url.hostname=='api.beatapi.io' and url.path.rstrip('/')=='/v1'

def allowed_beatapi(api):
    return is_beatapi(api.base) and api.beatapi_free_only and all(m in FREE_MODELS for m in (api.model,api.reviewer_model,api.fallback_model))

def available_for_input(api,system,user):
    return not is_beatapi(api.base) or len(system)+len(user)<=api.beatapi_max_input_chars
