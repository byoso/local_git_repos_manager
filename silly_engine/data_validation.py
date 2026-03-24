#! /usr/bin/env python3
"""
Data validation module
"""
from abc import ABC
from dataclasses import dataclass, fields, InitVar, field
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
    _data: InitVar[Dict[str, Any]]

    def __post_init__(self, _data: Dict[str, Any]) -> None:
        # filter data to only include allowed fields
        allowed = {f.name: f.type for f in fields(self)}

        for key, value in _data.items():
            if key in allowed:
                setattr(self, key, _check_generic(value, allowed[key], key))
        self._validate()

    def _validate(self) -> None:
        # Additional validation logic can be added here
        pass
