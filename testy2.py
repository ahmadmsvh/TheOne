# from testy import logger

# logger.info("Hello, world!")

# def myfunc(*args, **kwargs):
#     print(type(args))
#     print(type(kwargs))
#     print(args)
#     print(kwargs)

# myfunc(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, name="John", age=30)


# def the_decorator(func):
#     def wrapper(*args, **kwargs):
#         print("Before the function is called")
#         print(type(args))
#         print(type(kwargs))
#         print(args)
#         print(kwargs)
#         kwargs["input"] = [1, 2, 3]
#         new_args = tuple()
#         new_kwargs = {
#             "input": [1, 2, 3]
#         }
#         func(*new_args, **new_kwargs)
#         # or func(**new_kwargs)
#         print("After the function is called")
#     return wrapper


# @the_decorator
# def the_func(input):
#     for i in input:
#         print(i)


# the_func(1,2,3,4,name="John",age=30)


# import threading

# # Create thread-local storage
# local_data = threading.local()

# def worker(name):
#     # Each thread sets its own value
#     local_data.value = name
#     print(f"Thread {name}: {local_data.value}")

# # Create multiple threads
# t1 = threading.Thread(target=worker, args=("A",))
# t2 = threading.Thread(target=worker, args=("B",))

# t1.start()
# t2.start()


# import threading
# import time

# # WITHOUT threading.local() - using a regular object
# class RegularStorage:
#     pass

# shared_data = RegularStorage()

# def worker(name):
#     # Set a value
#     shared_data.value = name
#     print(f"Thread {name}: Set value to {name}")
    
#     # Small delay to let other threads interfere
#     time.sleep(0.01)
    
#     # Read the value back - might not be what we set!
#     print(f"Thread {name}: Read value as {shared_data.value}")

# # Create multiple threads
# threads = []
# for name in ["A", "B", "C"]:
#     t = threading.Thread(target=worker, args=(name,))
#     threads.append(t)
#     t.start()

# dict = {}
# dict.setdefault("name", "John")
# dict.setdefault("age", 30)
# print(dict.get("age"))