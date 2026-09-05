from abc import ABC, abstractmethod


class DocumentGenerator(ABC):
    @abstractmethod
    def generate(self, version):
        raise NotImplementedError
