"""
Control Flow API module.

Conditional execution and loop APIs.
Module name 'control_flow' becomes the category name.
"""

# pylint: disable=unused-argument

from lib.services import env

from ..if_stack import if_stack


def if_not_goto(executor, parameters):
    """
    Conditional jump if expression is false.

    Parameters:
        0..n-1: expression tokens
        n: line_number (int) - Line to jump to if false
    """
    line_number = parameters[-1]
    expression = parameters[:-1]
    if executor.eval_expression(expression):
        if_stack.push(True)
        executor.program_counter += 1
    else:
        if_stack.push(False)
        executor.jump_forward(line_number)


# Note: Named 'else_' because 'else' is a Python keyword
# The trailing underscore will be stripped by the auto-discovery mechanism
# to register this as 'else' API
def else_(executor, parameters):
    """
    Else clause for if statement.

    Note: Named 'else_' to avoid Python keyword conflict, but registered as 'else'.

    Parameters:
        0: line_number (int) - Line to jump to
    """
    line_number = parameters[-1]
    if if_stack.top():
        executor.jump_forward(line_number)
    else:
        executor.program_counter += 1


def elseif(executor, parameters):
    """
    Else-if clause for if statement.

    Parameters:
        0..n-1: expression tokens
        n: line_number (int) - Line to jump to
    """
    line_number = parameters[-1]
    expression = parameters[:-1]
    if if_stack.top():
        executor.jump_forward(line_number)
    else:
        if executor.eval_expression(expression):
            if_stack.pop()
            if_stack.push(True)
            executor.program_counter += 1
        else:
            executor.jump_forward(line_number)


def endif(executor, parameters):
    """
    End if block.

    Parameters:
        None
    """
    if_stack.pop()


def loop(executor, parameters):
    """
    Loop marker (no operation).

    Parameters:
        None
    """


def until(executor, parameters):
    """
    Loop until condition is true.

    Parameters:
        0: line_number (int) - Line to jump back to
        1..n: expression tokens
    """
    line_number = parameters[0]
    expression = parameters[1:]
    new_expression = []
    for token in expression:
        if token.startswith("$"):
            new_token = env.get_var(token[1:])
            if new_token is None:
                new_expression.append(token)
            else:
                new_expression.append(new_token)
        else:
            new_expression.append(token)
    if executor.eval_expression(new_expression):
        executor.program_counter += 1
    else:
        executor.jump_backward(line_number)
