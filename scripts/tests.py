import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Hello, world!")


class SomeClass:
    @property
    def some_prop(self):
        return 10

obj = SomeClass()
print(obj.some_prop)

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




