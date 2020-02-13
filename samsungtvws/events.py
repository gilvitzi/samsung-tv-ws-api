
class ListenerEntry(object):
    def __init__(self, callable, description):
        super().__init__()
        self.callable = callable
        self.description = description

class SimplePubSub(object):
    def __init__(self):
        super().__init__()
        self.topics = {
            '*': []
        }
    
    def subscribe(self, topic, callable, description=None):
        if topic not in self.topics:
            self.topics[topic] = []
        
        self.topics[topic].append(ListenerEntry(callable, description))
    
    def unsubscribe(self, topic, callable):
        # Not Implemented
        pass

    def publish(self, topic, data):
        self._publish(topic, {'topic': topic, 'data': data })
        if topic != '*':
            self._publish('*', {'topic': topic, 'data': data })
    
    def _publish(self, topic, data):
        if topic in self.topics:
            for l in self.topics[topic]:
                l.callable(data)