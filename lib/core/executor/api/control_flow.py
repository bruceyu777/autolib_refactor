"""
Control Flow API module.

Conditional execution and loop APIs.
Module name 'control_flow' becomes the category name.
"""

# pylint: disable=unused-argument

from lib.services import env

from ..if_stack import if_stack


def if_not_goto(executor, params):
    """
    Conditional jump if expression is false.

    Parameters (accessed via params object):
        Variable-length expression tokens followed by line number
    """
    # This API receives variable-length parameters
    # Get raw parameter data
    parameters = (
        params._raw if hasattr(params, "_raw") else list(params.to_dict().values())
    )

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
def else_(executor, params):
    """
    Else clause for if statement.

    Note: Named 'else_' to avoid Python keyword conflict, but registered as 'else'.

    Parameters (accessed via params object):
        Variable-length parameters with line number at end
    """
    # Get raw parameter data
    parameters = (
        params._raw if hasattr(params, "_raw") else list(params.to_dict().values())
    )
    line_number = parameters[-1]

    if if_stack.top():
        executor.jump_forward(line_number)
    else:
        executor.program_counter += 1


def elseif(executor, params):
    """
    Else-if clause for if statement.

    Parameters (accessed via params object):
        Variable-length expression tokens followed by line number
    """
    # Get raw parameter data
    parameters = (
        params._raw if hasattr(params, "_raw") else list(params.to_dict().values())
    )

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


def endif(executor, params):
    """
    End if block.

    No parameters required.
    """
    if_stack.pop()


def loop(executor, params):
    """
    Loop marker (no operation).

    No parameters required.
    """


def until(executor, params):
    """
    Loop until condition is true.

    Parameters (accessed via params object):
        Variable-length parameters: line_number followed by expression tokens
    """
    # Get raw parameter data
    parameters = (
        params._raw if hasattr(params, "_raw") else list(params.to_dict().values())
    )

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
