import operator

try:
    user_input = raw_input
except NameError:
    user_input = input

operators = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "<<": operator.lshift,
    ">>": operator.rshift,
    "%": operator.mod,
    "**": operator.pow
}

def get_user_input():
    try:
        a = user_input("Enter first number: ")
        op = user_input("Enter operator: ")
        b = user_input("Enter second number: ")

        func = operators.get(op)
        if func is None:
            return None, None, None

        # Operators requiring integers
        if op in ["<<", ">>", "%"]:
            n1 = int(a)
            n2 = int(b)
        else:
            n1 = float(a)
            n2 = float(b)

        return n1, n2, func
    except:
        return None, None, None

if __name__ == "__main__":
    while True:
        num1, num2, func = get_user_input()

        if num1 is None or num2 is None or func is None:
            print("Invalid input.")
            break

        print("Result:", func(num1, num2))