class VMCode:
    def __init__(self, line_number, operation, parameters):
        self.line_number = line_number
        self.operation = operation
        self.parameters = parameters

    def __str__(self):
        parameters = " ".join(str(p) for p in self.parameters)
        operation = f"{self.line_number} {self.operation}"

        return operation + (f" {parameters}" if parameters else "")

    def add_parameter(self, parameter):
        self.parameters = (*self.parameters, parameter)

    def __repr__(self):
        parameters = " ".join(str(p) for p in self.parameters)
        operation = f"{self.line_number} {self.operation}"

        return operation + (f" {parameters}" if parameters else "")
