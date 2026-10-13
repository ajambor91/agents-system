"""Internal conversion of YAML values into Compose models."""
from dataclasses import fields
from typing import Any, TypeVar

from .models import (
    Build, ComposeData, Dependency, DependsOn, Environment, EnvironmentVariable,
    Healthcheck, Network, Networks, Port, Ports, Resource, Resources,
    ResourceReference, ResourceReferences, Service, Services, ServiceNetwork,
    ServiceNetworks, Volume, Volumes, VolumeDefinition, VolumeDefinitions,
)

_T = TypeVar("_T")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be a mapping with string keys")
    return value


def _sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _short_names(value: list[Any], label: str) -> dict[str, Any]:
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"{label} entries must be strings")
    return {item: {} for item in value}


def _model(model: type[_T], value: Any, label: str) -> _T:
    data = _mapping(value, label)
    names = {item.name for item in fields(model)} - {"extra"}
    return model(**{key: val for key, val in data.items() if key in names},
                 extra={key: val for key, val in data.items() if key not in names})


def _named(model: type[_T], collection: type, value: Any, label: str):
    return collection((name, _model(model, {} if item is None else item, f"{label}.{name}"))
                      for name, item in _mapping(value, label).items())


def _variables(value: Any, label: str) -> Environment:
    if isinstance(value, list):
        data = {}
        for entry in value:
            if not isinstance(entry, str):
                raise ValueError(f"{label} entries must be strings")
            name, separator, content = entry.partition("=")
            data[name] = content if separator else None
    else:
        data = _mapping(value, label)
    result = Environment()
    for name, content in data.items():
        if content is not None and not isinstance(content, (str, int, float, bool)):
            raise ValueError(f"{label}.{name} must be a scalar or null")
        result[name] = EnvironmentVariable(name=name, value=content)
    return result


def _build(value: Any) -> Build:
    if isinstance(value, str):
        return Build(context=value)
    result = _model(Build, value, "build")
    if "args" in value:
        result.args = {name: item.value for name, item in _variables(value["args"], "build.args").items()}
    return result


def _number(value: str) -> int | str:
    return int(value) if value.isascii() and value.isdigit() else value


def _port(value: Any) -> Port:
    if isinstance(value, dict):
        if "target" not in value:
            raise ValueError("ports entry requires target")
        return _model(Port, value, "ports entry")
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("ports entries must be strings, integers or mappings")
    text, separator, protocol = str(value).partition("/")
    parts = text.rsplit(":", 2)
    host_ip = None
    if text.startswith("["):
        host, closing, rest = text.partition("]:")
        if not closing:
            raise ValueError("IPv6 ports require [address]:published:target")
        host_ip = host[1:]
        parts = rest.split(":")
        if len(parts) != 2:
            raise ValueError("IPv6 ports require [address]:published:target")
    elif len(parts) == 3:
        host_ip, *parts = parts
    if any(not part for part in parts):
        raise ValueError("ports entry contains an empty port")
    return Port(target=_number(parts[-1]),
                published=_number(parts[0]) if len(parts) == 2 else None,
                host_ip=host_ip, protocol=protocol if separator else "tcp")


def _volume(value: Any) -> Volume:
    if isinstance(value, dict):
        if "target" not in value:
            raise ValueError("volumes entry requires target")
        return _model(Volume, value, "volumes entry")
    if not isinstance(value, str):
        raise ValueError("volumes entries must be strings or mappings")
    parts = value.split(":")
    if len(parts) == 1:
        return Volume(target=value)
    if len(parts) not in (2, 3):
        raise ValueError("volumes entry must use source:target[:mode]")
    source, target = parts[:2]
    mode = parts[2] if len(parts) == 3 else None
    return Volume(target=target, source=source,
                  type="bind" if source.startswith((".", "/", "~")) else "volume",
                  read_only=mode is not None and "ro" in mode.split(","), mode=mode)


def _references(value: Any, label: str) -> ResourceReferences:
    result = ResourceReferences()
    for entry in _sequence(value, label):
        if isinstance(entry, str):
            result.append(ResourceReference(source=entry))
        else:
            data = _mapping(entry, label)
            if "source" not in data:
                raise ValueError(f"{label} entry requires source")
            result.append(_model(ResourceReference, data, label))
    return result


def _service(name: str, value: Any) -> Service:
    data = dict(_mapping(value, f"services.{name}"))
    data["name"] = name
    service = _model(Service, data, f"services.{name}")
    if service.build is not None:
        service.build = _build(service.build)
    if "ports" in data:
        service.ports = Ports(_port(item) for item in _sequence(data["ports"], "ports"))
    if "volumes" in data:
        service.volumes = Volumes(_volume(item) for item in _sequence(data["volumes"], "volumes"))
    if "environment" in data:
        service.environment = _variables(data["environment"], "environment")
    if "depends_on" in data:
        dependencies = data["depends_on"]
        if isinstance(dependencies, list):
            dependencies = _short_names(dependencies, "depends_on")
        service.depends_on = _named(Dependency, DependsOn, dependencies, "depends_on")
    if "networks" in data:
        networks = data["networks"]
        if isinstance(networks, list):
            networks = _short_names(networks, "networks")
        service.networks = _named(ServiceNetwork, ServiceNetworks, networks, "networks")
    for label in ("secrets", "configs"):
        if label in data:
            setattr(service, label, _references(data[label], label))
    if service.healthcheck is not None:
        service.healthcheck = _model(Healthcheck, service.healthcheck, "healthcheck")
    return service


def _compose(value: Any) -> ComposeData:
    data = _mapping(value, "Compose document")
    result = _model(ComposeData, data, "Compose document")
    result.services = Services((name, _service(name, entry))
                               for name, entry in _mapping(data.get("services", {}), "services").items())
    for label, model, collection in (
        ("volumes", VolumeDefinition, VolumeDefinitions),
        ("networks", Network, Networks),
        ("secrets", Resource, Resources),
        ("configs", Resource, Resources),
    ):
        setattr(result, label, _named(model, collection, data.get(label, {}), label))
    return result
