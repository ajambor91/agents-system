import json
import argparse

from pathlib import Path


TYPE_MAP = {
    str: "str",
    int: "int",
    float: "float",
    bool: "bool"
}


def generate(source: Path) -> None:
    SCRIPT_DIR = Path(__file__).resolve().parent
    target = (SCRIPT_DIR / "../lib/configuration/configuration.py").resolve()
    config = json.loads(source.read_text(encoding="utf-8"))

    lines = [
        "# AUTO-GENERATED. DO NOT EDIT.",
        "",
        "from typing import ClassVar, Mapping",
        "from .configuration_abstract import ConfigurationAbstract",
        "",
        "",
        "class Configuration(ConfigurationAbstract):",
        "    __slots__ = ()",
        ""
    ]

    variables = config['variables']
    # Generate typed class fields
    for field in variables:
        print("field")
        print(field)
        name = field["name"]
        value = field["value"]

        if not isinstance(name, str) or not name.isidentifier() or (
            name.startswith("_")
        ):
            raise ValueError(f"Invalid field name: {name}")

        value_type = TYPE_MAP.get(type(value))

        if value_type is None:
            raise TypeError(f"Unsupported type for {name}")

        lines.append(f"    {name}: ClassVar[{value_type}]")

    lines.extend([
        "",
        "    @classmethod",
        "    def schema(cls) -> Mapping[str, type]:",
        "        return {"
    ])

    # Generate field schema
    for field in variables:
        name = field["name"]
        value_type = TYPE_MAP[type(field["value"])]

        lines.append(f"            {name!r}: {value_type},")

    lines.extend([
        "        }",
        ""
    ])

    # Save generated class
    target.parent.mkdir(parents=True, exist_ok=True)

    target.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print(f"Generated: {target}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        type=Path,
        required=True
    )

    args = parser.parse_args()

    generate(args.source)