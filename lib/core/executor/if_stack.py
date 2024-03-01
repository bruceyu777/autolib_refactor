class IfStack:
    def __init__(self):
        self.stack = []

    def push(self, if_matched):
        self.stack.append(if_matched)

    def pop(self):
        return self.stack.pop()

    def top(self):
        return self.stack[-1]

    def __str__(self):
        return " ".join(str(v) for v in self.stack)


if_stack = IfStack()
