from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Union

T = TypeVar('T')

class BaseParser(ABC, Generic[T]):
    @abstractmethod
    def parse(self, input: Union[str, any]) -> T:
        return None
    
    @property
    def inputType(self) -> Any:
        return Union[str, bytes]
    
    @property
    def outputType(self) -> Any:
        return T
