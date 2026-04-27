import functools , time 

def retry(max_retries = 3 , backoff = 2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args , **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args , **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(backoff * (2 ** attempt))
        return wrapper
    return decorator


def printHi():
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args , **kwargs):
            print("Hi")
            return func(*args , **kwargs)
        return wrapper
    return decorator




@retry(max_retries=5 , backoff=3)
@printHi()
def unstable_api_call():
    print("API call ...")
    time.sleep(1)
    if time.time() % 3 < 1:
        raise ConnectionError("API is unstable!")
    return "Success"


print(unstable_api_call())