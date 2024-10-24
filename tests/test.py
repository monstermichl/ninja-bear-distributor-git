from os import path
import pathlib
from typing import Type
import unittest

from ninja_bear import Orchestrator, DistributorCredentials, GeneratorBase, NamingConventionType, DumpInfo, PropertyType, LanguageConfigBase, Plugin
from src.ninja_bear_distributor_git.distributor import Distributor


_COMPARE_FILE_CONTENT = """
struct TestConfig:
    boolean myBoolean = true
    int myInteger = 142
    float myFloat = 322.0
    float myCombinedFloat = 45724.0
    double myDouble = 233.9
    regex myRegex = /Test Reg(E|e)x/ -- Just another RegEx.
    string mySubstitutedString = 'Sometimes I just want to scream Hello Mars!'
    string myCombinedString = 'I am telling you that this string got included from test-include.yaml.'
-- Generated with ninja-bear v1.0.0 (https://pypi.org/project/ninja-bear/).
"""


class ExampleScriptGenerator(GeneratorBase):
    """
    ExampleScript specific generator. For more information about the generator methods, refer to GeneratorBase.
    """

    def _default_type_naming_convention(self) -> NamingConventionType:
        return NamingConventionType.PASCAL_CASE
    
    def _line_comment(self, string: str) -> str:
        return f'-- {string}'
    
    def _dump(self, info: DumpInfo) -> str:
        code = f'struct {info.type_name}:\n'

        for property in info.properties:
            type = property.type
            value = property.value

            if type == PropertyType.BOOL:
                type_string = 'boolean'
                value = 'true' if value else 'false'
            elif type == PropertyType.INT:
                type_string = 'int'
            elif type == PropertyType.FLOAT:
                type_string = 'float'
            elif type == PropertyType.DOUBLE:
                type_string = 'double'
            elif type == PropertyType.STRING:
                type_string = 'string'
                value = f'\'{value}\''
            elif type == PropertyType.REGEX:
                type_string = 'regex'
                value = f'/{value}/'

            comment = f' {self._line_comment(property.comment)}' if property.comment else ''
            code += f'{" " * info.indent}{type_string} {property.name} = {value}{comment}\n'

        return code


class ExampleScriptConfig(LanguageConfigBase):
    """
    ExampleScript specific config. For more information about the config methods, refer to LanguageConfigBase.
    """

    def _file_extension(self) -> str:
        return 'es'

    def _generator_type(self) -> Type[ExampleScriptGenerator]:
        return ExampleScriptGenerator
    
    def _default_file_naming_convention(self) -> NamingConventionType:
        return NamingConventionType.KEBAP_CASE

    def _allowed_file_name_pattern(self) -> str:
        return r'.+'


class Test(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self._test_path = pathlib.Path(__file__).parent.resolve()
        self._test_config_path = path.join(self._test_path, '..', 'example/test-config.yaml')
        self._plugins = [
            Plugin('examplescript', ExampleScriptConfig),
        ]

    def test_distribution(self):
        # Get secret from environment variables.
        credential = DistributorCredentials('example-alias', None, 'password')
        orchestrator = Orchestrator.read_config(self._test_config_path, [credential], plugins=self._plugins)

        orchestrator.distribute()

        # TODO: Implement
        # TODO: Add distributor result check here (e.g. if file has been distributed to Git or whatever
        # your distributor does).
        raise Exception('Distributor result checking has not been implemented')
