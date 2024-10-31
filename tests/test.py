import datetime
import pathlib
import re
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


_COMPARE_FILE_CONTENT = """
struct TestConfig:
    boolean myBoolean = true
    int myInteger = 142
    float myFloat = 322.0
    float myCombinedFloat = 45724.0
    double myDouble = 233.9
    regex myRegex = /Test Reg(E|e)x/ -- Just another RegEx.
    string mySubstitutedString = 'Sometimes I just want to scream Hello World!'
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
        self._config_name = 'test-config'
        self._config_file = f'{self._config_name}.yaml'
        self._test_path = pathlib.Path(__file__).parent.resolve()
        self._test_config_path = join(self._test_path, '..', f'example/{self._config_file}')
        self._plugins = [
            Plugin('examplescript', ExampleScriptConfig),
            Plugin('ninja-bear-distributor-git', Distributor),
        ]

    def test_distribution(self):
        def distribute(include_time: bool):
            # Load test-config.yaml directly in test file to allow implementer to modify properties if required.
            with open(self._test_config_path, 'r') as f:
                config = yaml.safe_load(f)
                remote = environ.get('URL')
                token = environ.get('TOKEN')
                start_datetime = datetime.datetime.now()

                if not remote:
                    raise Exception('No remote URL provided')
                if not token:
                    raise Exception('No authentication token provided')
                
                # Update data in distributor.
                git_distributor = config['distributors'][0]
                git_distributor['url'] = remote
                git_distributor['password'] = token
                del git_distributor['user']

                # Add meta data.
                KEY_META = 'meta'

                config[KEY_META] = {}
                config[KEY_META]['date'] = include_time
                config[KEY_META]['time'] = include_time

                # Run parsing and distribution.
                orchestrator = Orchestrator.parse_config(config, self._config_name, plugins=self._plugins)
                orchestrator.distribute()

                with tempfile.TemporaryDirectory() as temp_dir:
                    target_file_path = join(temp_dir, git_distributor['path'], f'{self._config_name}.es')
                    code, _, _ = execute_command(f' git clone {remote.replace("://", f"://{token}@")} {temp_dir}')
                    
                    if code != 0:
                        raise Exception('Cloning failed')

                    with open(target_file_path, 'r') as f:
                        loaded_content = f.read()
                        date_comment_matches = list(re.finditer(r'.+ date: ((\d+(:|\.))+\d+).+', loaded_content))
                        date_greater = False

                        if len(date_comment_matches) > 0:
                            date_comment_match = date_comment_matches[0]
                            date_comment = date_comment_match.group(0)
                            print('------ date commnet', date_comment)
                            # Remove date from content for easier comparison.
                            loaded_content = loaded_content.replace(date_comment, '')

                            # Compare date.
                            if include_time:
                                compare_date = datetime.datetime.strptime(date_comment_match.group(1), '%Y-%m-%d').date()
                                start_date = start_datetime.date()
                                date_greater = compare_date > start_date

                                self.assertGreaterEqual(compare_date, start_date)

                        time_comment_matches = list(re.finditer(r'.+ time: ((\d+(:|\.))+\d+).+', loaded_content))

                        if len(time_comment_matches) > 0:
                            time_comment_match = time_comment_matches[0]

                            # Remove time from content for easier comparison.
                            loaded_content = loaded_content.replace(time_comment_match.group(0), '')

                            # Compare time (only if date is not already greater).
                            if include_time and not date_greater:
                                compare_time = datetime.datetime.strptime(time_comment_match.group(1), '%H:%M:%S.%f').time()
                                self.assertGreaterEqual(compare_time, start_datetime.time())

                        # Compare content.
                        self.assertEqual(_COMPARE_FILE_CONTENT.strip(), loaded_content.strip())

        # Distibute first time with timestamp.
        distribute(True)

        # Distribute second and third time without timestamp to cover "nothing to commit"-branch.
        distribute(False)
        distribute(False)

        # Distibute fourth time with timestamp just to make sure something with a timestamp is in the repo.
        distribute(True)
