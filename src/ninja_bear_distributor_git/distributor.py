from __future__ import annotations
import os
import re
import tempfile
from typing import Dict

from ninja_bear import DistributorBase, DistributorCredentials, DistributeInfo
from ninja_bear.helpers.shell import execute_commands
from ninja_bear.base.info import VERSION

class NoRepositoryUrlProvidedException(Exception):
    def __init__(self):
        super().__init__('No repository URL has been provided')


class GitProblemException(Exception):
    def __init__(self, problem: str, additional_info: str=''):
        super().__init__(problem, additional_info)


class GitVersionException(Exception):
    def __init__(self, check_version: GitVersion, git_version: GitVersion):
        super().__init__(f'Invalid git version. Required: {check_version}, actual: {git_version}')


class GitVersion:
    major: str
    minor: str
    patch: str

    def __init__(self, major: int, minor: int, patch: int):
        """
        Constructor

        :param major: Major version.
        :type major:  int
        :param minor: Minor version.
        :type minor:  int
        :param patch: Patch version.
        :type patch:  int
        """
        self.major = major
        self.minor = minor
        self.patch = patch

    @staticmethod
    def from_git() -> GitVersion:
        """
        Retrieves the git version by calling git --version.

        :raises GitProblemException: Raised if the Git version could not be evaluated.

        :return: GitVersion instance with the actual Git version.
        :rtype:  GitVersion
        """
        code, text, _ = execute_commands('git --version')
        version_text = text if code == 0 else ''

        if code != 0:
            raise GitProblemException('Git version could not be evaluated')
        return GitVersion.from_string(version_text)

    @staticmethod
    def from_string(version_string: str) -> GitVersion:
        """
        Turns a version string.

        :param version_string: Version string which contains the version in the form of <major>.<minor>.<patch>.
        :type version_string:  str

        :return: GitVersion instance with the data from the version string.
        :rtype:  GitVersion
        """
        version = GitVersion(0, 0, 0)
        match = re.search('\d+\.\d+\.\d+', version_string)

        if match:
            parts = match.group(0).split('.')

            version.major = int(parts[0])
            version.minor = int(parts[1])
            version.patch = int(parts[2])
        return version
    
    def __str__(self) -> str:
        return f'{self.major}.{self.minor}.{self.patch}'


class Distributor(DistributorBase):
    _MIN_GIT_VERSION = GitVersion(2, 29, 0)  # Needs at least git version 2.29.0 as it introduced partial-clone (https://www.git-scm.com/docs/partial-clone).

    def __init__(self, config: Dict, credentials: DistributorCredentials=None):
        """
        Constructor

        :param url:         Git repository URL.
        :type url:          str
        :param target_path: Relative target path within the repo.
        :type target_path:  str
        :param user:        Git user.
        :type user:         str
        :param password:    Git user password or token.
        :type password:     str

        :raises NoRepositoryUrlProvidedException: Raised if no Git server URL has been provided.
        """
        super().__init__(config, credentials)

        target_path = self.from_config('path')  # Use root directory as default path.

        self._url = self.from_config('url')
        self._target_path = target_path if target_path else ''  # Use root directory as default path.
        self._user = self.from_config('user')
        self._password = self.from_config('password')

    def get_responsiblity_type(self) -> str:
        return 'git'

    def _distribute(self, info: DistributeInfo) -> DistributorBase:
        """
        Method to distribute a generated config to a Git server.

        :param info: Contains the required information to distribute the generated config.
        :type info:  DistributeInfo

        :raises GitVersionException: Raised if Git does not fulfill the minimum required version.
        :raises GitProblemException: Raised on different Git problems.

        :return: The current GitDistributor instance.
        :rtype:  GitDistributor
        """
        file_name = info.file_name
        data = info.data

        # Make sure an URL has been provided.
        if not self._url:
            raise NoRepositoryUrlProvidedException()
        
        # If credentials were provided, overwrite YAML defined user and password value.
        credentials = self.credentials()

        if credentials:
            user = credentials.user
            password = credentials.password
        else:
            user = self._user
            password = self._password

        # Retrieve Git version.
        git_version = GitVersion.from_git()
        
        if git_version.major < self._MIN_GIT_VERSION.major or \
           git_version.minor < self._MIN_GIT_VERSION.minor or \
           git_version.patch < self._MIN_GIT_VERSION.patch:
            raise GitVersionException(self._MIN_GIT_VERSION, git_version)
        else:
            # Create temporary folder to clone the git repo into and work with it.
            with tempfile.TemporaryDirectory() as temp_dir:
                SEPARATOR = '://'
                url_parts = self._url.split(SEPARATOR)
                protocol = url_parts[0] if len(url_parts) > 1 else ''
                url = url_parts[1] if len(url_parts) > 1 else url_parts[0]
                separator = SEPARATOR if protocol else ''
                user = self._user if self._user else ''
                password = self._password if self._password else ''
                colon = ':' if user and password else ''
                at = '@' if user or password else ''
                url_with_credentials = f'{protocol}{separator}{user}{colon}{password}{at}{url}'
                password = None

                code, _, stderr = execute_commands(*[
                    f'git clone --filter=blob:none --no-checkout {url_with_credentials} {temp_dir}',
                ])

                # If clone was successful, go on.
                if code == 0:
                    # Only clone desired target folder.
                    code, _, stderr = execute_commands(*[
                        f'cd {temp_dir}',
                        f'git sparse-checkout set {self._target_path}' if self._target_path else '',
                        'git checkout',
                    ])

                # If checkout was successful, go on.
                if code == 0:
                    # Make sure target directory exists.
                    if self._target_path:
                        os.makedirs(os.path.join(temp_dir, self._target_path), exist_ok=True)

                    target_file_path = os.path.join(self._target_path, file_name)
                    target_file_path_full = os.path.join(temp_dir, target_file_path)

                    # Write data to target file.
                    with open(target_file_path_full, 'w') as f:
                        f.write(data)

                    # Add changes.
                    code, _, stderr = execute_commands(*[
                        f'cd {temp_dir}',
                        f'git add "{target_file_path}"',
                    ])

                    def commit():
                        return execute_commands(*[
                            f'cd {temp_dir}',
                            f'git commit "{target_file_path}" -m "Update {target_file_path} via ninja-bear v{VERSION}"',
                        ])

                    if code == 0:
                        # Commit changes.
                        code, _, stderr = commit()

                    if code != 0:
                        user = self._user if self._user else 'ninja-bear'

                        # If commit didn't work, it's probably because user.name and user.email are not set. Therefore,
                        # if a user was provided, use it, otherwise commit as ninja-bear.
                        code, stdio, stderr = execute_commands(*[
                            f'cd {temp_dir}',
                            f'git config --local user.name {user}',
                            f'git config --local user.email {user}',
                        ])
                        # Try to commit changes again.
                        code, stdio, stderr = commit()
                        
                        # if nothing to commit was the problem, correct the error code.
                        if code != 0 and re.search('nothing to commit', stdio):
                            code = 0

                    if code == 0:
                        # Commit and push changes to repo.
                        code, _, stderr = execute_commands(*[
                            f'cd {temp_dir}',
                            f'git push -u {url_with_credentials}',
                        ])

                    if code != 0:
                        raise GitProblemException(f'{file_name} could not be pushed to {self._url}', stderr)
                else:
                    raise GitProblemException(f'Git repo {self._url} could not be cloned', stderr)
        return self
