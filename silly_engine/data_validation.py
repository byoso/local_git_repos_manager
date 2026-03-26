#! /usr/bin/env python3
"""
Version:
- 1.1.0: constructor doesn't accept raw dict, do DataValidatedClass(**dict) instead
Data validation module
"""
from abc import ABC
from dataclasses import dataclass, fields, field, MISSING
from typing import Any, get_origin, get_args, List, Dict

class DataValidationError(Exception):
    pass


def _check_generic(value: Any, field_type: Any, field_name: str = "<unknown>") -> Any:
    """Cast simple types + list[T] + dict[K, V]"""
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Any : no check
    if field_type is Any:
        return value

    # Simple cases : str, int, bool, float
    if isinstance(field_type, type):
        if not isinstance(value, field_type):
            if field_type is bool:
                if isinstance(value, int):
                    return bool(value)
            raise DataValidationError(
                f"Field '{field_name}' expects {field_type.__name__}, got {value!r} ({type(value).__name__})"
            )
        return value

    # List[T]
    if origin in (list, List):
        inner_type = args[0] if args else Any
        if not isinstance(value, list):
            raise DataValidationError(f"Field '{field_name}' expects a list, got {value!r}")
        return [_check_generic(v, inner_type, field_name) for v in value]

    # Dict[K, V]
    if origin in (dict, Dict):
        key_type, val_type = args if args else (Any, Any)
        if not isinstance(value, dict):
            raise DataValidationError(f"Field '{field_name}' expects a dict, got {value!r}")
        return {_check_generic(k, key_type, field_name): _check_generic(v, val_type, field_name) for k, v in value.items()}

    # If type is unknown
    return value

@dataclass
class ValidatedDataClass(ABC):
    """Data class with automatic validation.
    This class is expected to be inherited and needs to be used with
    @dataclass decorator and default values for all fields."""
    _id: str = field(init=True, default="")

    def __init__(self, *args, **kwargs) -> None:
        # set declared fields only, using defaults when absent
        for f in fields(self.__class__):
            if f.name in kwargs:
                val = kwargs.pop(f.name)
            elif f.default is not MISSING:
                val = f.default
            else:
                val = None
            setattr(self, f.name, val)
        # ignore any remaining kwargs (extras)
        self.__post_init__()

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            try:
                validated_value = _check_generic(value, field.type, field.name)
                setattr(self, field.name, validated_value)
            except DataValidationError as e:
                raise DataValidationError(f"Error in field '{field.name}': {e}") from e
        self._validate()

    def _validate(self) -> None:
        # Additional validation logic can be added here
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.__dict__})>"