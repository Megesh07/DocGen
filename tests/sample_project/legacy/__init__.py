"""Legacy package."""
from .compat import (
    AuditedConfig,
    DynamicRecord,
    FlexRecord,
    OldStyleMapper,
    accumulate_gen,
    add_audit_trail,
    build_class_from_spec,
    load_config,
)

__all__ = [
    "AuditedConfig", "DynamicRecord", "FlexRecord", "OldStyleMapper",
    "accumulate_gen", "add_audit_trail", "build_class_from_spec", "load_config",
]
