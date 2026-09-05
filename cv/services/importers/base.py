from abc import ABC, abstractmethod


class CVImportAdapter(ABC):
    source_type = None

    @classmethod
    @abstractmethod
    def extract_text(cls, uploaded_file):
        raise NotImplementedError
