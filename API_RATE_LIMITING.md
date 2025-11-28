# API Rate Limiting

## Overview

All API endpoints are protected with rate limiting to prevent abuse and ensure fair usage.

## Rate Limits

**Current Limit**: 100 requests per hour per IP address

All API endpoints share this limit:
- `/api/reports/<report_id>/timeline/`
- `/api/reports/<report_id>/top-contributors/`
- `/api/reports/<report_id>/top-expenditures/`
- `/api/global/timeline/`
- `/api/contributors/<contributor_name>/timeline/`
- `/api/pacs/<organization_name>/sankey/`
- `/api/out-of-state/map/`

## How It Works

- **Tracking**: Rate limits are tracked by IP address
- **Method**: Only GET requests are rate limited
- **Cache**: Uses in-memory cache (LocMemCache)
- **Reset**: Limits reset after 1 hour

## Response Codes

- `200 OK` - Request successful
- `429 Too Many Requests` - Rate limit exceeded

When rate limited, the response will be:
```json
{
  "error": "Rate limit exceeded"
}
```

## Adjusting Rate Limits

To change the rate limit, edit the decorators in [views.py](polstats_project/disclosures/views.py):

```python
# Change '100/h' to your desired rate
# Examples:
#   '50/h'   - 50 requests per hour
#   '200/h'  - 200 requests per hour
#   '10/m'   - 10 requests per minute
#   '1000/d' - 1000 requests per day

@ratelimit(key='ip', rate='100/h', method='GET')
def api_out_of_state_map(request):
    ...
```

## Monitoring

To monitor rate limit usage, you can:

1. **Check server logs** for 429 responses
2. **Add logging** to track rate limit hits:
   ```python
   from django_ratelimit.decorators import ratelimit

   @ratelimit(key='ip', rate='100/h', method='GET')
   def my_api(request):
       if getattr(request, 'limited', False):
           # Log the rate limit event
           logger.warning(f'Rate limit hit for IP: {request.META.get("REMOTE_ADDR")}')
   ```

## Production Considerations

For production deployments, consider:

1. **Redis Cache**: Use Redis instead of in-memory cache for multi-server setups
   ```python
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.redis.RedisCache',
           'LOCATION': 'redis://127.0.0.1:6379/1',
       }
   }
   ```

2. **Different Limits per Endpoint**: Apply stricter limits to expensive queries
   ```python
   # Expensive query - lower limit
   @ratelimit(key='ip', rate='10/h', method='GET')
   def api_expensive_operation(request):
       ...

   # Cheap query - higher limit
   @ratelimit(key='ip', rate='500/h', method='GET')
   def api_simple_operation(request):
       ...
   ```

3. **User-based Limits**: Rate limit by user instead of IP (requires authentication)
   ```python
   @ratelimit(key='user', rate='1000/h', method='GET')
   def api_for_authenticated_users(request):
       ...
   ```

## Testing

To test rate limiting locally:

```bash
# Make many requests quickly to test the limit
for i in {1..105}; do
    curl -s -o /dev/null -w "Request $i: %{http_code}\n" \
    http://127.0.0.1:8000/api/out-of-state/map/
done
```

After 100 requests, you should see `429` responses.

## Disabling Rate Limiting

To temporarily disable rate limiting (e.g., for testing):

Edit [settings.py](polstats_project/settings.py):
```python
RATELIMIT_ENABLE = False  # Set to True to re-enable
```
