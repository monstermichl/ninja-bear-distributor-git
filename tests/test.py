import datetime
import os
import pathlib
import tempfile
import unittest

from typing import Type
from os.path import join
from os import environ

import yaml

from ninja_bear import (
    DumpInfo,
    GeneratorBase,
    LanguageConfigBase,
    NamingConventionType,
    Orchestrator,
    Plugin,
    PropertyType,
)
from src.ninja_bear_distributor_git.distributor import Distributor, execute_command


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
        self._config_name = 'test-config'
        self._config_file = f'{self._config_name}.yaml'
        self._test_path = pathlib.Path(__file__).parent.resolve()
        self._test_config_path = join(self._test_path, '..', f'example/{self._config_file}')
        self._plugins = [
            Plugin('examplescript', ExampleScriptConfig),
            Plugin('ninja-bear-distributor-git', Distributor),
        ]

    def test_distribution(self):
        def distribute(change: bool):
            # Load test-config.yaml directly in test file to allow implementer to modify properties if required.
            with open(self._test_config_path, 'r') as f:
                config = yaml.safe_load(f)
                remote = environ.get('URL')
                token = environ.get('TOKEN')
                start_datetime = datetime.datetime.now()
                commit_message = f'Updating config ({start_datetime.isoformat()})'

                if not remote:
                    raise Exception('No remote URL provided')
                if not token:
                    raise Exception('No authentication token provided')
                
                # Update data in distributor.
                git_distributor = config['distributors'][0]
                git_distributor['url'] = remote
                git_distributor['password'] = token
                git_distributor['message'] = commit_message
                del git_distributor['user']

                # If change shall be tested, change float property.
                if change:
                    config['properties'][2]['value'] = start_datetime.timestamp()

                # If context is a CI server, set the Git user.
                if os.getenv('GITHUB_ACTIONS') or os.getenv('TRAVIS') or \
                    os.getenv('CIRCLECI') or os.getenv('GITLAB_CI'):
                    execute_command('git config --global user.name github-actions')
                    execute_command('git config --global user.email github-actions@github.com')
                
                # Run parsing and distribution.
                orchestrator = Orchestrator.parse_config(config, self._config_name, plugins=self._plugins)
                orchestrator.distribute()

                with tempfile.TemporaryDirectory() as temp_dir:
                    code, _, _ = execute_command(f' git clone {remote.replace("://", f"://{token}@")} {temp_dir}')
                    
                    if code != 0:
                        raise Exception('Cloning failed')

                    _, compare_commit_message, _ = execute_command('git log -1 --pretty=%B', directory=temp_dir)  # https://stackoverflow.com/a/7293026

                    if change:
                        self.assertEqual(commit_message.strip(), compare_commit_message.strip())

        # First call to check if upload works.
        distribute(True)

        # Second call to undo value change.
        distribute(False)

        # Third call to check 'nothing to commit'-branch.
        distribute(False)
