class LoopEnv:
    def __init__(self):
        self.vars = dict()
        self.loop_start = None

    def add_var(self, name, value):
        self.vars[name] = value

    def get_var(self, name):
        return self.vars.get(name, None)

    def set_var(self, name, value):
        self.vars[name] = value


loop_env = LoopEnv()
