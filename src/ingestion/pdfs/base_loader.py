from abc import ABC, abstractmethod
from typing import List, Dict


class BaseLoader(ABC):

    @abstractmethod
    def load(self, file_path: str) -> List[Dict]:
        pass
