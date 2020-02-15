
class ListenerEntry(object):
    def __init__(self, callable):
        super().__init__()
        self.callable = callable

class SimplePubSub(object):
    def __init__(self):
        super().__init__()
        self.topics = {
            '*': set()
        }
    
    def subscribe(self, topic, callable):
        if topic not in self.topics:
            self.topics[topic] = set()
        
        self.topics[topic].add(ListenerEntry(callable))
    
    def unsubscribe(self, topic, callable):
        if topic in self.topics:
            listeners = self.topics[topic]
            listeners.remove(callable)
            if not len(listeners):
                del self.topics[topic]
        else:
            raise ValueError("unsubscribe: topic does not exists")

    def publish(self, topic, data):
        self._publish(topic, {'topic': topic, 'data': data })
        if topic != '*':
            self._publish('*', {'topic': topic, 'data': data })
    
    def _publish(self, topic, data):
        if topic in self.topics:
            for l in self.topics[topic]:
                l.callable(data)