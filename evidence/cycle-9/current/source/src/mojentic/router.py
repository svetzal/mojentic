class Router:
    def __init__(self, routes=None):
        if routes is None:
            routes = {}
        self.routes = routes

    def add_route(self, event_type, agent):
        agents = self.routes.get(event_type, [])
        agents.append(agent)
        self.routes[event_type] = agents

    def get_agents(self, event):
        return self.routes.get(type(event), [])
