from .docker_facade import DockerFacade
from class_builder import ClassBuilder
from module_creater import ModuleCreator
class DockerManager(DockerFacade):

    def __new___(cls):
        creator = ModuleCreator()
        return DockerFacade(
            candidates=creator.candidates,
            compose=creator.compose,
            stack_manager=creator.stack_manager,
            docker_units_service=creator.docker_units_service
        )
