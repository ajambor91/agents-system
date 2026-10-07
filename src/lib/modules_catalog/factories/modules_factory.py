
from manifests import ManifestsApp
from typing import Any


from ..models import Module, Command, Flag, ExclusiveGroup, CommandInput, ModulesCatalog

class ModulesCatalogFactory:

    @classmethod
    def from_json(cls, raw: str | bytes) -> ModulesCatalog:
        return cls.from_dict(ManifestsApp().parse_manifest(raw))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModulesCatalog:
        modules: dict[str, Module] = {}
        modules_by_section: dict[str, Module] = {}
        command_index: dict[str, Command] = {}
        # exit
        for child_module in data["children"]:
            module = cls._create_module(
                child_module,
                fallback_section_name=child_module['module_name'],
            )

            modules[module.module_name] = module
            if child_module["is_menu_option"] is True:
                modules_by_section[module.section_name] = module
            for command in module.commands.values():
                command.module = module

                key = f"{module.section_name}.{command.name}"

                if key in command_index:
                    raise ValueError(f"Duplicate command: {key}")

                command_index[key] = command

        return ModulesCatalog(
            schema_version=data["schema_version"],
            version=data["version"],
            kind=data["kind"],
            app_name=data["app_module_name"],
            absolute_path=data["absolute_path"],
            modules=modules,
            modules_by_section=modules_by_section,
            commands=command_index,
        )

    @classmethod
    def _create_module(
        cls,
        data: dict[str, Any],
        fallback_section_name: str,
    ) -> Module:
        return Module(
            module_name=data["module_name"],
            absolute_module_path=data["absolute_module_path"],
            section_name=data.get(
                "section_name",
                fallback_section_name,
            ),
            menu_name=data["menu_name"],
            description=data["description"],
            usage=data.get("usage", ""),
            commands={
                command["name"]: cls._create_command(command)
                for command in data.get("commands", [])
            },
        )

    @classmethod
    def _create_command(
        cls,
        data: dict[str, Any],
    ) -> Command:
        command_input = None

        if input_data := data.get("input"):
            command_input = CommandInput(
                source=input_data["source"],
                type=input_data["type"],
                maximum_bytes=input_data["maximum_bytes"],
            )

        exclusive_groups = [
            ExclusiveGroup(
                members=group["members"],
                minimum=group["minimum"],
                maximum=group["maximum"],
            )
            for group in data.get("exclusive_groups", [])
        ]

        return Command(
            name=data["name"],
            method=data.get("method"),
            description=data["description"],
            usage=data["usage"],
            implementation_status=data["implementation_status"],
            flags=[
                cls._create_flag(flag)
                for flag in data.get("flags", [])
            ],
            input=command_input,
            exclusive_groups=exclusive_groups,
        )

    @staticmethod
    def _create_flag(data: dict[str, Any]) -> Flag:
        return Flag(
            name=data["name"],
            short=data.get("short"),
            long=data.get("long"),
            aliases=data.get("aliases", []),
            description=data["description"],
            usage=data["usage"],
            takes_value=data["takes_value"],
            type=data["type"],
            required=data["required"],
            default=data.get("default"),
        )
